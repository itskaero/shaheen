"""Settings validation — docs/DECISIONS.md ADR-044 (managed Postgres URLs)."""

from __future__ import annotations

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
