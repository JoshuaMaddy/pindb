"""Typed application settings loaded from the environment and optional ``.env``.

The module exposes a single instance, ``CONFIGURATION``, constructed at import
time. Validation errors are printed as JSON to stderr and re-raised so
misconfiguration fails fast at startup.
"""

import sys
from pathlib import Path
from typing import Literal

from meilisearch_python_sdk import AsyncClient
from pydantic import Field, ValidationError, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Configuration(BaseSettings):
    """Pydantic settings model for PinDB (images, DB, search, auth, logging)."""

    model_config = SettingsConfigDict(
        extra="ignore",
        env_file=".env",
        env_nested_delimiter="__",
        case_sensitive=False,
    )

    # Images
    image_backend: Literal["filesystem", "r2"] = Field(default="filesystem")
    image_directory: Path | None = Field(default=None)
    r2_account_id: str | None = Field(default=None)
    r2_bucket: str | None = Field(default=None)
    r2_access_key_id: str | None = Field(default=None)
    r2_secret_access_key: str | None = Field(default=None)
    r2_public_url: str | None = Field(default=None)

    @model_validator(mode="after")
    def _database_sync_default(self) -> "Configuration":
        if not self.database_connection_sync.strip():
            u = self.database_connection
            sync = (
                u.replace("postgresql+asyncpg", "postgresql+psycopg", 1)
                if "asyncpg" in u
                else u
            )
            return self.model_copy(update={"database_connection_sync": sync})
        return self

    @model_validator(mode="after")
    def _check_backend_config(self) -> "Configuration":
        if self.image_backend == "filesystem" and self.image_directory is None:
            raise ValueError("image_directory required when image_backend=filesystem")
        if self.image_backend == "r2":
            missing = [
                f
                for f in (
                    "r2_account_id",
                    "r2_bucket",
                    "r2_access_key_id",
                    "r2_secret_access_key",
                )
                if getattr(self, f) is None
            ]
            if missing:
                raise ValueError(f"R2 backend missing config: {', '.join(missing)}")
        return self

    # Postgres: async app uses postgresql+asyncpg; sync URL for Alembic/CLI
    # (psycopg3). If ``database_connection_sync`` is empty, it defaults to
    # ``database_connection`` with the async driver swapped to psycopg.
    database_connection: str
    database_connection_sync: str = Field(
        default="",
        description="Sync SQLAlchemy URL (postgresql+psycopg). Empty = derive from database_connection.",
    )

    # Meilisearch
    meilisearch_key: str
    meilisearch_url: str = Field(default="http://127.0.0.1:7700")
    meilisearch_index: str = Field(default="pins")
    search_sync_interval_minutes: int = Field(default=5)

    _meili_client: AsyncClient | None = None

    @property
    def meili_client(self) -> AsyncClient:
        """Lazily construct a singleton Meilisearch ``AsyncClient`` (await I/O)."""
        if self._meili_client is None:
            self._meili_client = AsyncClient(
                url=self.meilisearch_url,
                api_key=self.meilisearch_key,
            )
        return self._meili_client

    async def aclose_meili(self) -> None:
        """Close the Meili HTTP client (call from app shutdown)."""
        if self._meili_client is not None:
            await self._meili_client.aclose()
            self._meili_client = None

    # Auth
    secret_key: str
    base_url: str = Field(default="http://localhost:8000")
    # Session cookie Secure flag. Default True (production). Flip to False
    # in .env for local dev over plain HTTP.
    session_cookie_secure: bool = Field(default=True)
    # CSRF: reject unsafe-method requests whose Origin/Referer does not
    # match base_url. Disable only for pytest's TestClient, which does
    # not attach Origin headers.
    csrf_enforce_origin: bool = Field(default=True)

    # Legal / contact — shown in footer, privacy policy, ToS, DMCA notice
    contact_email: str

    # Google OAuth (optional)
    google_client_id: str | None = Field(default=None)
    google_client_secret: str | None = Field(default=None)

    # Discord OAuth (optional)
    discord_client_id: str | None = Field(default=None)
    discord_client_secret: str | None = Field(default=None)

    # Meta (Facebook Login) OAuth (optional)
    meta_client_id: str | None = Field(default=None)
    meta_client_secret: str | None = Field(default=None)

    # Password policy
    password_min_length: int = Field(default=12)
    password_min_zxcvbn_score: int = Field(default=3)

    # Test-only OAuth provider — enables /auth/_test-oauth endpoints
    # used by the e2e suite. MUST stay False in production.
    allow_test_oauth_provider: bool = Field(default=False)

    # Toggle the per-IP rate limiter on sensitive auth endpoints. Disable only
    # for the e2e suite, where all traffic shares 127.0.0.1 and hits the
    # signup/login windows almost immediately. MUST stay True in production.
    rate_limit_enabled: bool = Field(default=True)

    # Comma-separated usernames to auto-promote to admin on startup.
    # Empty by default — promote your first admin via SQL or a seeded
    # migration. Kept as a string so ``.env`` stays ergonomic.
    bootstrap_admin_usernames: str = Field(default="")

    @property
    def bootstrap_admin_username_list(self) -> list[str]:
        """Split ``bootstrap_admin_usernames`` into non-empty trimmed names."""
        return [
            u.strip() for u in self.bootstrap_admin_usernames.split(",") if u.strip()
        ]

    # Logging
    logging_date_format: str = Field(default="%d %b %Y | %H:%M:%S")
    logging_format: str = Field(default="%(asctime)s | %(name)s | %(message)s")
    log_file: str = Field(default="pindb.log")
    log_file_max_bytes: int = Field(default=200 * 1024 * 1024)
    log_file_backup_count: int = Field(default=7)

    @property
    def templates_js_dir(self) -> Path:
        """First-party page scripts under ``templates/js/`` (subfolders by area)."""
        return Path(__file__).resolve().parent / "templates" / "js"


try:
    CONFIGURATION = Configuration()  # type: ignore
except ValidationError as exc:
    print(exc.json(indent=2), file=sys.stderr)
    raise
