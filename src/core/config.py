"""Application configuration.

All configuration is loaded from environment variables (optionally via a
local .env file during development). Nothing here should ever be logged
verbatim — see core.logging for the redaction guard.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, SecretStr
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


def load_settings() -> Settings:
    """Load and validate settings once at process startup."""
    return Settings()  # type: ignore[call-arg]  # values come from the environment
