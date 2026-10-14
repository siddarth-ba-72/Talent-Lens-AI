from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


_SERVICE_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    app_env: str = Field(default="dev", alias="APP_ENV")
    app_port: int = Field(default=9000, alias="APP_PORT")

    # Datastores: Postgres holds the structured data (users, searches, sourcing
    # tasks, share requests); MongoDB holds the sourced candidate profiles.
    database_url: str = Field(alias="DATABASE_URL")
    mongodb_uri: str = Field(alias="MONGODB_URI")
    mongodb_database: str = Field(default="talentlens", alias="MONGODB_DATABASE")

    jwt_secret: str = Field(alias="JWT_SECRET")
    jwt_access_expiry_ms: int = Field(default=900_000, alias="JWT_ACCESS_EXPIRY")
    jwt_refresh_expiry_ms: int = Field(default=604_800_000, alias="JWT_REFRESH_EXPIRY")
    jwt_signup_ticket_expiry_ms: int = Field(default=600_000, alias="JWT_SIGNUP_TICKET_EXPIRY")
    # Defaults to True outside dev; the session cookie is then only sent over HTTPS.
    cookie_secure: Optional[bool] = Field(default=None, alias="COOKIE_SECURE")
    rate_limit_max_attempts: int = Field(default=5, alias="RATE_LIMIT_MAX_ATTEMPTS")
    rate_limit_window_seconds: int = Field(default=60, alias="RATE_LIMIT_WINDOW_SECONDS")

    google_client_id: Optional[str] = Field(default=None, alias="GOOGLE_CLIENT_ID")
    google_client_secret: Optional[str] = Field(default=None, alias="GOOGLE_CLIENT_SECRET")
    google_redirect_uri: Optional[str] = Field(default=None, alias="GOOGLE_REDIRECT_URI")
    google_token_endpoint: str = Field(default="https://oauth2.googleapis.com/token", alias="GOOGLE_TOKEN_ENDPOINT")

    llm_provider: str = Field(default="gemini", alias="LLM_PROVIDER")
    gemini_api_key: Optional[str] = Field(default=None, alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-2.0-flash", alias="GEMINI_MODEL")
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")
    github_token: Optional[str] = Field(default=None, alias="GITHUB_TOKEN")
    llm_timeout_seconds: int = Field(default=30, alias="LLM_TIMEOUT_SECONDS")
    llm_max_retries: int = Field(default=2, alias="LLM_MAX_RETRIES")
    llm_log_prompts: bool = Field(default=False, alias="LLM_LOG_PROMPTS")
    jd_parse_timeout_seconds: int = Field(default=30, alias="JD_PARSE_TIMEOUT_SECONDS")
    sourcing_timeout_seconds: int = Field(default=120, alias="SOURCING_TIMEOUT_SECONDS")

    # Built UI (talentlens-client `npm run build` writes here).
    static_dir: Path = Field(default=_SERVICE_ROOT / "static", alias="STATIC_DIR")
    # Defaults to enabled in dev only.
    docs_enabled: Optional[bool] = Field(default=None, alias="DOCS_ENABLED")
    # Only needed when the UI is served from a different origin than the API.
    cors_allowed_origins: str = Field(default="", alias="CORS_ALLOWED_ORIGINS")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("jwt_secret")
    @classmethod
    def _require_strong_secret(cls, value: str) -> str:
        if len(value.encode("utf-8")) < 32:
            raise ValueError("JWT_SECRET must be at least 32 characters")
        return value

    @property
    def is_dev(self) -> bool:
        return self.app_env.strip().lower() in {"dev", "development", "local", "test"}

    @property
    def use_secure_cookies(self) -> bool:
        return self.cookie_secure if self.cookie_secure is not None else not self.is_dev

    @property
    def expose_docs(self) -> bool:
        return self.docs_enabled if self.docs_enabled is not None else self.is_dev

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


def clear_settings_cache() -> None:
    get_settings.cache_clear()
