from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Auth service settings, read from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    database_url: str = Field(..., description="postgresql+asyncpg://user:pass@host:5432/db")
    db_schema: str = "auth"

    jwt_secret: str = Field(..., min_length=32)
    jwt_issuer: str = "oncogon-auth"
    jwt_audience: str = "oncogon-api"
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 30
    reset_token_ttl_minutes: int = 10

    reset_code_ttl_minutes: int = 10
    reset_code_max_attempts: int = 5
    max_failed_logins: int = 5
    lockout_minutes: int = 15

    @property
    def is_development(self) -> bool:
        return self.environment.lower() in {"development", "dev", "local"}


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
