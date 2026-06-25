from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from deps import get_current_user
from models import Application, Device, LaunchLog, License, User
from schemas import AdminStats, LaunchLogEntry

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/stats", response_model=AdminStats)
async def admin_stats(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AdminStats:
    app_ids_subq = select(Application.id).where(Application.owner_id == user.id).scalar_subquery()

    total_licenses = await db.execute(
        select(func.count()).select_from(License).where(License.app_id.in_(app_ids_subq))
    )
    active_devices = await db.execute(
        select(func.count())
        .select_from(Device)
        .join(License, Device.license_id == License.id)
        .where(License.app_id.in_(app_ids_subq), Device.last_seen.isnot(None))
    )

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())

    launches_today = await db.execute(
        select(func.count())
        .select_from(LaunchLog)
        .join(License, LaunchLog.license_id == License.id)
        .where(License.app_id.in_(app_ids_subq), LaunchLog.launched_at >= today_start)
    )
    launches_week = await db.execute(
        select(func.count())
        .select_from(LaunchLog)
        .join(License, LaunchLog.license_id == License.id)
        .where(License.app_id.in_(app_ids_subq), LaunchLog.launched_at >= week_start)
    )

    return AdminStats(
        total_licenses=total_licenses.scalar_one(),
        active_devices=active_devices.scalar_one(),
        launches_today=launches_today.scalar_one(),
        launches_this_week=launches_week.scalar_one(),
    )


@router.get("/logs", response_model=list[LaunchLogEntry])
async def admin_logs(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[LaunchLogEntry]:
    app_ids_subq = select(Application.id).where(Application.owner_id == user.id).scalar_subquery()

    result = await db.execute(
        select(LaunchLog)
        .join(License, LaunchLog.license_id == License.id)
        .where(License.app_id.in_(app_ids_subq))
        .order_by(LaunchLog.launched_at.desc())
        .offset(offset)
        .limit(limit)
    )
    rows = result.scalars().all()

    return [
        LaunchLogEntry(
            id=row.id,
            device_id=row.device_id,
            license_id=row.license_id,
            success=row.success,
            reason=row.reason,
            launched_at=row.launched_at,
            ip=row.ip_address,
        )
        for row in rows
    ]
