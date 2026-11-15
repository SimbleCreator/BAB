"""Application settings, read only from environment variables (or a local .env)."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_JWT_SECRET = "dev-only-secret-never-use-in-production-0000"  # noqa: S105
DEV_DATABASE_URL = "postgresql+asyncpg://bab:bab_dev_password@localhost:5432/bab"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BAB_", env_file=".env", extra="ignore")

    env: str = "development"
    app_name: str = "B.A.B"
    version: str = "0.1.0"
    api_prefix: str = "/api/v1"

    database_url: str = DEV_DATABASE_URL
    test_database_url: str = "postgresql+asyncpg://bab:bab_dev_password@localhost:5432/bab_test"
    frontend_origin: str = "http://localhost:4200"
    contact_email: str = "owner@example.com"

    jwt_secret: str = Field(default=DEV_JWT_SECRET, repr=False)
    access_token_minutes: int = 15
    refresh_token_days: int = 30
    # "lax" when frontend and API share a site (local dev, or one domain behind a proxy).
    # "none" when they are on different sites; the cookie is always Secure.
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"

    # Bounce, the AI assistant: any OpenAI-compatible chat endpoint. Default: OpenRouter free
    # models. Without an API key Bounce is switched off.
    ai_base_url: str = "https://openrouter.ai/api/v1"
    ai_model: str = "google/gemma-4-31b-it:free"
    ai_api_key: str = Field(default="", repr=False)
    ai_timeout_s: float = 120.0
    # Comma-separated backup models. Used with OpenRouter, which tries them in order when
    # the main model is busy or unavailable.
    ai_fallback_models: str = ""
    # Ask the endpoint for strict JSON output. Turn off only if an endpoint rejects it.
    ai_json_mode: bool = True
    ai_daily_plan_limit: int = 5

    @property
    def ai_enabled(self) -> bool:
        return bool(self.ai_api_key)

    @property
    def ai_fallback_list(self) -> list[str]:
        return [m.strip() for m in self.ai_fallback_models.split(",") if m.strip()]

    @model_validator(mode="after")
    def _safe_production(self) -> "Settings":
        if not self.is_production:
            return self
        if self.jwt_secret == DEV_JWT_SECRET or len(self.jwt_secret) < 32:
            raise ValueError("BAB_JWT_SECRET must be set to 32+ random characters in production.")
        if self.database_url == DEV_DATABASE_URL:
            raise ValueError("BAB_DATABASE_URL must be set in production.")
        if not self.frontend_origin.startswith("https://"):
            raise ValueError("BAB_FRONTEND_ORIGIN must be an https:// origin in production.")
        return self

    @property
    def is_production(self) -> bool:
        return self.env == "production"

    @property
    def refresh_cookie_path(self) -> str:
        return f"{self.api_prefix}/auth"


@lru_cache
def get_settings() -> Settings:
    return Settings()
