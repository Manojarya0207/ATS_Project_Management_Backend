"""Application configuration.

All configuration comes from environment variables (or a local ``.env`` file in
development). Nothing is hardcoded; environment-specific behaviour is driven by
the ``ENVIRONMENT`` variable (development / testing / staging / production).

The ``Settings`` object is constructed once during application startup
(``app.main.lifespan``) and injected everywhere via ``app.state`` — there is no
module-level singleton. Scripts and Alembic build their own instance directly.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Self

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_INSECURE_SECRETS = {"", "change-me-in-production", "secret", "changeme"}


class Environment(StrEnum):
    development = "development"
    testing = "testing"
    staging = "staging"
    production = "production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Application ---------------------------------------------------------
    app_name: str = "ATS Project Management API"
    api_v1_prefix: str = "/api/v1"
    environment: Environment = Environment.development
    debug: bool = False

    # --- Database ------------------------------------------------------------
    database_url: str = "sqlite+aiosqlite:///./ats_pm.db"
    database_echo: bool = False
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # --- Auth / security -----------------------------------------------------
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    password_min_length: int = 8
    password_max_length: int = 128

    # --- CORS ----------------------------------------------------------------
    cors_origins: str = "http://localhost:3000,http://localhost:8080,http://localhost:5000"
    cors_allow_local_dev: bool = True  # allow any localhost/127.0.0.1 port via regex

    # --- Rate limiting -------------------------------------------------------
    rate_limit_enabled: bool = True
    rate_limit_auth: str = "10/minute"

    # --- File storage --------------------------------------------------------
    storage_backend: str = "local"  # local | s3 | r2 | azure
    upload_dir: str = "uploads"
    max_upload_size_bytes: int = 25 * 1024 * 1024  # 25 MB
    # S3 / R2 / Azure settings (used only when the matching backend is active)
    s3_bucket: str = ""
    s3_region: str = ""
    s3_endpoint_url: str = ""  # set for Cloudflare R2 / MinIO
    azure_container: str = ""
    azure_connection_string: str = ""

    # --- Cache ---------------------------------------------------------------
    cache_backend: str = "memory"  # memory | redis | none
    redis_url: str = "redis://localhost:6379/0"

    # --- Queue ---------------------------------------------------------------
    queue_backend: str = "inline"  # inline | celery

    # --- Logging -------------------------------------------------------------
    log_level: str = "INFO"
    log_json: bool | None = None  # default: JSON in staging/production, console otherwise

    # --- Migrations ----------------------------------------------------------
    run_migrations_on_startup: bool = True

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production_like(self) -> bool:
        return self.environment in (Environment.staging, Environment.production)

    @property
    def log_json_enabled(self) -> bool:
        return self.log_json if self.log_json is not None else self.is_production_like

    @property
    def sync_database_url(self) -> str:
        """URL with a sync driver, for tools that need a sync engine (Alembic CLI)."""
        return self.database_url.replace("+aiosqlite", "").replace("+asyncpg", "+psycopg")

    @model_validator(mode="after")
    def _normalize_and_validate(self) -> Self:
        # Normalize database_url to use postgresql+asyncpg for PostgreSQL connections
        url = self.database_url
        if url.startswith("postgres://") or url.startswith("postgresql://"):
            if not url.startswith("postgresql+asyncpg://") and not url.startswith("postgres+asyncpg://"):
                if url.startswith("postgres://"):
                    url = url.replace("postgres://", "postgresql+asyncpg://", 1)
                else:
                    url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            
            # asyncpg does not accept libpq's ``sslmode`` parameter — translate
            # it to asyncpg's ``ssl``. Do NOT force ssl=require otherwise:
            # asyncpg defaults to ssl=prefer, which negotiates TLS on external
            # endpoints and falls back to plaintext on internal/private-network
            # endpoints (e.g. Render's internal connection string, which does
            # not speak TLS and closes the connection if SSL is forced).
            url = url.replace("?sslmode=", "?ssl=").replace("&sslmode=", "&ssl=")

            self.database_url = url

        if self.environment == Environment.production:
            if self.jwt_secret_key in _INSECURE_SECRETS or len(self.jwt_secret_key) < 32:
                raise ValueError(
                    "JWT_SECRET_KEY must be set to a strong value (>=32 chars) in production"
                )
            if self.database_url.startswith("sqlite"):
                raise ValueError("SQLite is not supported in production; set DATABASE_URL")
            if self.debug:
                raise ValueError("DEBUG must be disabled in production")
        return self
