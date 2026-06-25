from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.keystore import generate_api_key
from database import get_db
from deps import get_current_user
from models import Application, Device, LaunchLog, License, User
from schemas import AppCreate, AppCreated, AppDetail, AppStats, AppSummary, LicenseSummary

router = APIRouter(prefix="/apps", tags=["apps"])


@router.get("", response_model=list[AppSummary])
async def list_apps(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AppSummary]:
    result = await db.execute(
        select(Application).where(Application.owner_id == user.id).order_by(Application.created_at.desc())
    )
    apps = result.scalars().all()
    summaries: list[AppSummary] = []
    for app in apps:
        count_result = await db.execute(
            select(func.count()).select_from(License).where(License.app_id == app.id)
        )
        license_count = count_result.scalar_one()
        summaries.append(
            AppSummary(id=app.id, name=app.name, api_key=app.api_key, license_count=license_count)
        )
    return summaries


@router.post("", response_model=AppCreated, status_code=status.HTTP_201_CREATED)
async def create_app(
    body: AppCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AppCreated:
    app = Application(
        owner_id=user.id,
        name=body.name,
        description=body.description,
        api_key=generate_api_key(),
    )
    db.add(app)
    await db.flush()
    return AppCreated(id=app.id, name=app.name, api_key=app.api_key)


@router.get("/{app_id}", response_model=AppDetail)
async def get_app(
    app_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AppDetail:
    result = await db.execute(
        select(Application)
        .where(Application.id == app_id, Application.owner_id == user.id)
        .options(selectinload(Application.licenses).selectinload(License.devices))
    )
    app = result.scalar_one_or_none()
    if app is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    license_ids = [lic.id for lic in app.licenses]

    launches_today = 0
    if license_ids:
        launch_count = await db.execute(
            select(func.count())
            .select_from(LaunchLog)
            .where(LaunchLog.license_id.in_(license_ids), LaunchLog.launched_at >= today_start)
        )
        launches_today = launch_count.scalar_one()

    active_devices = sum(
        1 for lic in app.licenses for dev in lic.devices if dev.last_seen is not None
    )

    license_summaries = [
        LicenseSummary(
            id=lic.id,
            license_key=lic.license_key,
            state=lic.state,
            max_devices=lic.max_devices,
            expires_at=lic.expires_at,
            registered_devices=len(lic.devices),
            created_at=lic.created_at,
        )
        for lic in app.licenses
    ]

    return AppDetail(
        id=app.id,
        name=app.name,
        description=app.description,
        api_key=app.api_key,
        created_at=app.created_at,
        licenses=license_summaries,
        stats=AppStats(
            total_licenses=len(app.licenses),
            active_devices=active_devices,
            launches_today=launches_today,
        ),
    )
