from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+asyncpg://hardlock:hardlock@localhost:5432/hardlock"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_expire_minutes: int = 60 * 24  # dashboard JWT
    session_token_expire_seconds: int = 28800  # 8 hours for SDK verify

    hardlock_master_key: str = ""  # Fernet key; generate with Fernet.generate_key()

    verify_rate_limit: int = 20  # calls per hour per license key
    verify_rate_window_seconds: int = 3600

    cors_origins: str = "http://localhost:5173,http://localhost:3000"


@lru_cache
def get_settings() -> Settings:
    return Settings()
