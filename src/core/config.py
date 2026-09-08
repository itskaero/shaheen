"""Application configuration.

All configuration is loaded from environment variables (optionally via a
local .env file during development). Nothing here should ever be logged
verbatim — see core.logging for the redaction guard.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

SetupMode = Literal["development", "launch"]


class Settings(BaseSettings):
    """Runtime configuration for Shaheen Bot.

    See .env.example for the full list of variables and their meaning.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    discord_token: SecretStr
    guild_id: int
    database_url: str
    setup_mode: SetupMode = "development"
    log_level: str = Field(default="INFO")
    brawlhalla_api_key: SecretStr
    snapshot_interval_hours: float = Field(default=6.0, gt=0)

    @field_validator("database_url")
    @classmethod
    def _use_asyncpg_driver(cls, value: str) -> str:
        """Normalize a bare `postgres://`/`postgresql://` URL to asyncpg.

        Managed Postgres providers (Render, Heroku, ...) hand out connection
        strings without a driver suffix, but SQLAlchemy's async engine
        requires one. Doing this here means a provider's connection string
        can be used for DATABASE_URL as-is (docs/DEPLOYMENT.md).
        """
        for prefix in ("postgresql://", "postgres://"):
            if value.startswith(prefix):
                return "postgresql+asyncpg://" + value[len(prefix) :]
        return value


def load_settings() -> Settings:
    """Load and validate settings once at process startup."""
    return Settings()  # type: ignore[call-arg]  # values come from the environment
