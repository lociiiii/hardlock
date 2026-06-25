from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


# ── Auth ──────────────────────────────────────────────────────────────────────


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ── Applications ──────────────────────────────────────────────────────────────


class AppCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None


class AppSummary(BaseModel):
    id: UUID
    name: str
    api_key: str
    license_count: int

    model_config = {"from_attributes": True}


class AppDetail(BaseModel):
    id: UUID
    name: str
    description: str | None
    api_key: str
    created_at: datetime
    licenses: list["LicenseSummary"]
    stats: "AppStats"

    model_config = {"from_attributes": True}


class AppStats(BaseModel):
    total_licenses: int
    active_devices: int
    launches_today: int


class AppCreated(BaseModel):
    id: UUID
    name: str
    api_key: str


# ── Licenses ──────────────────────────────────────────────────────────────────


class LicenseGenerateRequest(BaseModel):
    app_id: UUID
    count: int = Field(default=1, ge=1, le=100)
    max_devices: int = Field(default=1, ge=1)
    expires_at: datetime | None = None


class LicenseKeyResponse(BaseModel):
    license_key: str


class LicenseSummary(BaseModel):
    id: UUID
    license_key: str
    state: str
    max_devices: int
    expires_at: datetime | None
    registered_devices: int
    created_at: datetime


class LicenseDetail(BaseModel):
    license_key: str
    state: str
    registered_devices: int
    max_devices: int
    expires_at: datetime | None


class RevokeResponse(BaseModel):
    status: str


# ── Devices (SDK) ─────────────────────────────────────────────────────────────


class DeviceRegisterRequest(BaseModel):
    license_key: str
    pc_uuid: str
    mb_serial: str
    esp_mac: str
    label: str | None = None


class DeviceRegisterResponse(BaseModel):
    status: str
    device_id: UUID


class DeviceVerifyRequest(BaseModel):
    license_key: str
    pc_uuid: str
    mb_serial: str
    esp_mac: str


class DeviceVerifySuccess(BaseModel):
    authorized: bool = True
    session_token: str
    expires_in: int


class DeviceVerifyFailure(BaseModel):
    authorized: bool = False
    reason: str


# ── Admin ─────────────────────────────────────────────────────────────────────


class AdminStats(BaseModel):
    total_licenses: int
    active_devices: int
    launches_today: int
    launches_this_week: int


class LaunchLogEntry(BaseModel):
    id: int
    device_id: UUID | None
    license_id: UUID | None
    success: bool
    reason: str | None
    launched_at: datetime
    ip: str | None

    model_config = {"from_attributes": True}


AppDetail.model_rebuild()
