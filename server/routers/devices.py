from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from core.fingerprint import compute_fingerprint
from core.rate_limit import check_verify_rate_limit
from core.security import create_session_token
from database import get_db
from deps import get_application_by_api_key
from models import Application, Device, LaunchLog, License
from schemas import (
    DeviceRegisterRequest,
    DeviceRegisterResponse,
    DeviceVerifyFailure,
    DeviceVerifyRequest,
    DeviceVerifySuccess,
)

router = APIRouter(prefix="/devices", tags=["devices"])
settings = get_settings()


async def _get_license_for_app(
    license_key: str, app: Application, db: AsyncSession
) -> License:
    result = await db.execute(
        select(License).where(License.license_key == license_key, License.app_id == app.id)
    )
    license_row = result.scalar_one_or_none()
    if license_row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="License not found")
    return license_row


def _license_blocked(license_row: License) -> str | None:
    if license_row.state == "REVOKED":
        return "REVOKED"
    if license_row.state == "SUSPENDED":
        return "SUSPENDED"
    if license_row.expires_at:
        expires = license_row.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires < datetime.now(timezone.utc):
            return "EXPIRED"
    return None


async def _append_launch_log(
    db: AsyncSession,
    *,
    device_id: str | None,
    license_id: str,
    ip: str | None,
    success: bool,
    reason: str,
) -> None:
    db.add(
        LaunchLog(
            device_id=device_id,
            license_id=license_id,
            ip_address=ip,
            success=success,
            reason=reason,
        )
    )


@router.post("/register", response_model=DeviceRegisterResponse, status_code=status.HTTP_201_CREATED)
async def register_device(
    body: DeviceRegisterRequest,
    app: Application = Depends(get_application_by_api_key),
    db: AsyncSession = Depends(get_db),
) -> DeviceRegisterResponse:
    license_row = await _get_license_for_app(body.license_key, app, db)

    blocked = _license_blocked(license_row)
    if blocked:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"License {blocked.lower()}")

    fingerprint = compute_fingerprint(body.pc_uuid, body.mb_serial, body.esp_mac)

    existing = await db.execute(
        select(Device).where(Device.license_id == license_row.id, Device.fingerprint == fingerprint)
    )
    device = existing.scalar_one_or_none()
    if device is not None:
        return DeviceRegisterResponse(status="registered", device_id=device.id)

    count_result = await db.execute(
        select(func.count()).select_from(Device).where(Device.license_id == license_row.id)
    )
    if count_result.scalar_one() >= license_row.max_devices:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Maximum devices reached for this license",
        )

    device = Device(
        license_id=license_row.id,
        fingerprint=fingerprint,
        label=body.label,
        last_seen=datetime.now(timezone.utc),
    )
    db.add(device)
    if license_row.state == "ISSUED":
        license_row.state = "ACTIVE"
    await db.flush()

    return DeviceRegisterResponse(status="registered", device_id=device.id)


@router.post(
    "/verify",
    response_model=DeviceVerifySuccess,
    responses={403: {"model": DeviceVerifyFailure}},
)
async def verify_device(
    body: DeviceVerifyRequest,
    request: Request,
    app: Application = Depends(get_application_by_api_key),
    db: AsyncSession = Depends(get_db),
):
    client_ip = request.client.host if request.client else None

    # Rate limiting — skipped if Redis is not available
    try:
        allowed, _ = await check_verify_rate_limit(body.license_key)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded for verify endpoint",
            )
    except HTTPException:
        raise
    except Exception:
        pass  # Redis not running — skip rate limiting for local dev

    try:
        license_row = await _get_license_for_app(body.license_key, app, db)
    except HTTPException:
        await _append_launch_log(
            db,
            device_id=None,
            license_id=None,
            ip=client_ip,
            success=False,
            reason="LICENSE_NOT_FOUND",
        )
        raise

    blocked = _license_blocked(license_row)
    if blocked:
        await _append_launch_log(
            db,
            device_id=None,
            license_id=str(license_row.id),
            ip=client_ip,
            success=False,
            reason=blocked,
        )
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content=DeviceVerifyFailure(authorized=False, reason=blocked).model_dump(),
        )

    fingerprint = compute_fingerprint(body.pc_uuid, body.mb_serial, body.esp_mac)

    result = await db.execute(
        select(Device).where(Device.license_id == license_row.id, Device.fingerprint == fingerprint)
    )
    device = result.scalar_one_or_none()

    if device is None:
        await _append_launch_log(
            db,
            device_id=None,
            license_id=str(license_row.id),
            ip=client_ip,
            success=False,
            reason="FINGERPRINT_MISMATCH",
        )
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content=DeviceVerifyFailure(
                authorized=False, reason="FINGERPRINT_MISMATCH"
            ).model_dump(),
        )

    device.last_seen = datetime.now(timezone.utc)
    await _append_launch_log(
        db,
        device_id=str(device.id),
        license_id=str(license_row.id),
        ip=client_ip,
        success=True,
        reason="OK",
    )

    session_token = create_session_token(
        license_key=license_row.license_key,
        device_id=device.id,
        app_id=app.id,
    )

    return DeviceVerifySuccess(
        session_token=session_token,
        expires_in=settings.session_token_expire_seconds,
    )