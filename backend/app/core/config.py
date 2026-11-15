"""Application settings, read only from environment variables (or a local .env)."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BAB_", env_file=".env", extra="ignore")

    env: str = "development"
    app_name: str = "B.A.B"
    version: str = "0.1.0"
    api_prefix: str = "/api/v1"

    database_url: str = "postgresql+asyncpg://bab:bab_dev_password@localhost:5432/bab"
    frontend_origin: str = "http://localhost:4200"
    contact_email: str = "owner@example.com"
    jwt_secret: str = Field(default="change-me-in-every-environment", repr=False)

    @property
    def is_production(self) -> bool:
        return self.env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
