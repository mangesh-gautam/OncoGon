from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    auth_service_url: str = "http://auth-service:8001"
    research_service_url: str = "http://research-service:8002"
    voice_service_url: str = "http://oncogon-voice-api:8000"
    cors_origins: str = "*"
    upstream_timeout_seconds: float = 15.0
    voice_timeout_seconds: float = 180.0
    research_timeout_seconds: float = 60.0  # evidence uploads
    # Per-client-IP limit for credential endpoints (login, register, password reset).
    auth_rate_limit_per_minute: int = 20

    @property
    def is_development(self) -> bool:
        return self.environment.lower() in {"development", "dev", "local"}

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
