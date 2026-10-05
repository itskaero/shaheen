"""Settings validation — docs/DECISIONS.md ADR-044 (managed Postgres URLs),
ADR-109 (BRAWLISTAN environment variables).
"""

from __future__ import annotations

import pytest
from pydantic import SecretStr

from core.config import Settings


def _settings(database_url: str) -> Settings:
    return Settings(
        discord_token=SecretStr("t"),
        guild_id=1,
        database_url=database_url,
        brawlhalla_api_key=SecretStr("k"),
    )


def test_bare_postgres_url_gets_asyncpg_driver() -> None:
    settings = _settings("postgres://user:pass@host:5432/db")
    assert settings.database_url == "postgresql+asyncpg://user:pass@host:5432/db"


def test_bare_postgresql_url_gets_asyncpg_driver() -> None:
    settings = _settings("postgresql://user:pass@host:5432/db")
    assert settings.database_url == "postgresql+asyncpg://user:pass@host:5432/db"


def test_url_with_driver_already_set_is_left_alone() -> None:
    settings = _settings("postgresql+asyncpg://user:pass@host:5432/db")
    assert settings.database_url == "postgresql+asyncpg://user:pass@host:5432/db"


def test_sqlite_url_is_left_alone() -> None:
    settings = _settings("sqlite+aiosqlite:///:memory:")
    assert settings.database_url == "sqlite+aiosqlite:///:memory:"


_REQUIRED_ENV = {
    "DISCORD_TOKEN": "t",
    "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
    "BRAWLHALLA_API_KEY": "k",
}


def _from_env(monkeypatch: pytest.MonkeyPatch, **env: str) -> Settings:
    for name in ("GUILD_ID", "DISCORD_GUILD_ID"):
        monkeypatch.delenv(name, raising=False)
    for name, value in {**_REQUIRED_ENV, **env}.items():
        monkeypatch.setenv(name, value)
    return Settings(_env_file=None)  # type: ignore[call-arg]


def test_discord_guild_id_is_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    assert _from_env(monkeypatch, DISCORD_GUILD_ID="123").guild_id == 123


def test_guild_id_still_works(monkeypatch: pytest.MonkeyPatch) -> None:
    assert _from_env(monkeypatch, GUILD_ID="456").guild_id == 456


def test_empty_optional_ids_mean_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    """.env.example ships `REPORT_CHANNEL_ID=` etc.; copying it unchanged
    must not fail validation."""
    settings = _from_env(
        monkeypatch,
        GUILD_ID="1",
        REPORT_CHANNEL_ID="",
        MOD_LOG_CHANNEL_ID="",
        ANNOUNCEMENT_CHANNEL_ID="",
        BOT_OWNER_ID="",
        DISCORD_CLIENT_ID="",
    )
    assert settings.report_channel_id is None
    assert settings.mod_log_channel_id is None
    assert settings.announcement_channel_id is None
    assert settings.bot_owner_id is None
    assert settings.discord_client_id is None


def test_channel_overrides_parse(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _from_env(monkeypatch, GUILD_ID="1", MOD_LOG_CHANNEL_ID="99")
    assert settings.mod_log_channel_id == 99


def test_level_up_posts_are_off_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _from_env(monkeypatch, GUILD_ID="1")
    assert settings.announce_level_ups is False
    assert settings.announce_season_start is True
    assert _from_env(monkeypatch, GUILD_ID="1", ANNOUNCE_LEVEL_UPS="true").announce_level_ups
