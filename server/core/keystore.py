import secrets
import string

from cryptography.fernet import Fernet, InvalidToken

from config import get_settings

settings = get_settings()


def _fernet() -> Fernet:
    key = settings.hardlock_master_key
    if not key:
        raise RuntimeError("HARDLOCK_MASTER_KEY is not configured")
    return Fernet(key.encode() if isinstance(key, str) else key)


def generate_license_key() -> str:
    alphabet = string.ascii_uppercase + string.digits
    parts = ["".join(secrets.choice(alphabet) for _ in range(4)) for _ in range(3)]
    return f"HLCK-{'-'.join(parts)}"


def generate_api_key() -> str:
    suffix = secrets.token_hex(12)
    return f"hl_live_{suffix}"


def generate_aes_key() -> bytes:
    return secrets.token_bytes(32)


def wrap_key(raw_key: bytes) -> str:
    return _fernet().encrypt(raw_key).decode("utf-8")


def unwrap_key(wrapped: str) -> bytes:
    try:
        return _fernet().decrypt(wrapped.encode("utf-8"))
    except InvalidToken as exc:
        raise ValueError("Invalid wrapped key") from exc
