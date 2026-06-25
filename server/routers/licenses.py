from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.keystore import generate_aes_key, generate_license_key, wrap_key
from database import get_db
from deps import get_current_user
from models import Application, Device, License, User
from schemas import (
    LicenseDetail,
    LicenseGenerateRequest,
    LicenseKeyResponse,
    RevokeResponse,
)

router = APIRouter(prefix="/licenses", tags=["licenses"])


async def _get_owned_license(
    license_key: str, user: User, db: AsyncSession
) -> License:
    result = await db.execute(
        select(License)
        .join(Application, License.app_id == Application.id)
        .where(License.license_key == license_key, Application.owner_id == user.id)
    )
    license_row = result.scalar_one_or_none()
    if license_row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="License not found")
    return license_row


@router.post("/generate", response_model=list[LicenseKeyResponse], status_code=status.HTTP_201_CREATED)
async def generate_licenses(
    body: LicenseGenerateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[LicenseKeyResponse]:
    app_result = await db.execute(
        select(Application).where(Application.id == body.app_id, Application.owner_id == user.id)
    )
    app = app_result.scalar_one_or_none()
    if app is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    keys: list[LicenseKeyResponse] = []
    for _ in range(body.count):
        raw_aes = generate_aes_key()
        license_row = License(
            app_id=body.app_id,
            license_key=generate_license_key(),
            max_devices=body.max_devices,
            expires_at=body.expires_at,
            wrapped_aes_key=wrap_key(raw_aes),
            state="ISSUED",
        )
        db.add(license_row)
        await db.flush()
        keys.append(LicenseKeyResponse(license_key=license_row.license_key))

    return keys


@router.get("/{key}", response_model=LicenseDetail)
async def get_license(
    key: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LicenseDetail:
    license_row = await _get_owned_license(key, user, db)

    device_count = await db.execute(
        select(func.count()).select_from(Device).where(Device.license_id == license_row.id)
    )

    return LicenseDetail(
        license_key=license_row.license_key,
        state=license_row.state,
        registered_devices=device_count.scalar_one(),
        max_devices=license_row.max_devices,
        expires_at=license_row.expires_at,
    )


@router.post("/{key}/revoke", response_model=RevokeResponse)
async def revoke_license(
    key: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RevokeResponse:
    license_row = await _get_owned_license(key, user, db)
    license_row.state = "REVOKED"
    return RevokeResponse(status="revoked")
