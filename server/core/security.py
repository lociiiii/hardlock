from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext

from config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
settings = get_settings()


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(subject: str | UUID, expires_delta: timedelta | None = None) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.jwt_access_expire_minutes)
    )
    payload = {"sub": str(subject), "exp": expire, "type": "access"}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_session_token(
    license_key: str,
    device_id: str | UUID,
    app_id: str | UUID,
) -> str:
    expire = datetime.now(timezone.utc) + timedelta(seconds=settings.session_token_expire_seconds)
    payload = {
        "sub": license_key,
        "device_id": str(device_id),
        "app_id": str(app_id),
        "exp": expire,
        "type": "session",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


def get_token_subject(token: str) -> str:
    try:
        payload = decode_token(token)
        sub = payload.get("sub")
        if sub is None:
            raise JWTError("Missing subject")
        return str(sub)
    except JWTError as exc:
        raise ValueError("Invalid token") from exc
