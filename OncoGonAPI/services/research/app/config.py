from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Research service settings, read from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"

    # Must match the auth service, which issues the access tokens.
    jwt_secret: str = Field(..., min_length=32)
    jwt_issuer: str = "oncogon-auth"
    jwt_audience: str = "oncogon-api"

    @property
    def is_development(self) -> bool:
        return self.environment.lower() in {"development", "dev", "local"}


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
