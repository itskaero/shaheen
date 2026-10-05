"""Application configuration.

All configuration is loaded from environment variables (optionally via a
local .env file during development). Nothing here should ever be logged
verbatim — see core.logging for the redaction guard.
"""

from __future__ import annotations

from typing import Literal

from pydantic import AliasChoices, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

SetupMode = Literal["development", "launch"]


def normalize_database_url(value: str) -> str:
    """Normalize a bare `postgres://`/`postgresql://` URL to asyncpg.

    Managed Postgres providers (Render, Heroku, ...) hand out connection
    strings without a driver suffix, but SQLAlchemy's async engine requires
    one. Doing this means a provider's connection string can be used for
    DATABASE_URL as-is (docs/DEPLOYMENT.md).

    A standalone function, not a method, so `alembic/env.py` can reuse it
    without constructing a full `Settings` object — migrations run in
    contexts (CI, a bare migration-only container) that only have
    DATABASE_URL set, not Discord/Brawlhalla credentials.
    """
    for prefix in ("postgresql://", "postgres://"):
        if value.startswith(prefix):
            return "postgresql+asyncpg://" + value[len(prefix) :]
    return value


class Settings(BaseSettings):
    """Runtime configuration for Shaheen Bot.

    See .env.example for the full list of variables and their meaning.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        # .env.example lists optional ids as `NAME=`; an empty value means unset.
        env_ignore_empty=True,
    )

    discord_token: SecretStr
    # GUILD_ID or, per the BRAWLISTAN brief, DISCORD_GUILD_ID.
    guild_id: int = Field(validation_alias=AliasChoices("guild_id", "discord_guild_id"))
    # The Discord application id (for the invite link in the docs); optional.
    discord_client_id: int | None = None
    # Bot owner's Discord user id: always passes staff/setup checks, even
    # before any role exists (bot/checks/permissions.py). Optional.
    bot_owner_id: int | None = None
    database_url: str
    setup_mode: SetupMode = "development"
    log_level: str = Field(default="INFO")
    brawlhalla_api_key: SecretStr
    brawlhalla_api_base_url: str = "https://api.brawlhalla.com/"
    snapshot_interval_hours: float = Field(default=6.0, gt=0)
    # Brawlhalla wipes ranked ratings at the start of each season, and its
    # API does not say which season a response belongs to, so every snapshot
    # is stamped with a season (docs/DECISIONS.md ADR-088). The season is
    # derived from the date (services/seasons.py, ADR-102); set
    # BRAWLHALLA_SEASON only to override that when Brawlhalla's real reset
    # dates drift from the 13-week rhythm — and unset it again afterwards,
    # or the season stops advancing.
    brawlhalla_season: int | None = Field(default=None, ge=1)
    # The public website, for links the bot posts (ADR-107).
    site_url: str = "https://itskaero.github.io/shaheen"
    # Optional channel overrides (ADR-109). Unset, the bot posts to the
    # channels /setup provisioned: reports and the moderation log to
    # #report, announcements to #announcements.
    report_channel_id: int | None = None
    mod_log_channel_id: int | None = None
    announcement_channel_id: int | None = None

    @field_validator("database_url")
    @classmethod
    def _use_asyncpg_driver(cls, value: str) -> str:
        return normalize_database_url(value)


def load_settings() -> Settings:
    """Load and validate settings once at process startup."""
    return Settings()  # type: ignore[call-arg]  # values come from the environment
