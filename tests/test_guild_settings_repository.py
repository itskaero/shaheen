from sqlalchemy.ext.asyncio import AsyncSession

from database.repositories.guild_settings_repository import GuildSettingsRepository


async def test_set_mode_creates_then_updates(session: AsyncSession) -> None:
    repo = GuildSettingsRepository(session)

    assert await repo.get(1) is None

    created = await repo.set_mode(1, "development")
    assert created.setup_mode == "development"
    assert created.last_setup_at is not None

    updated = await repo.set_mode(1, "launch")
    assert updated.guild_id == created.guild_id
    assert updated.setup_mode == "launch"


async def test_mark_season_announced_creates_or_updates(session: AsyncSession) -> None:
    """ADR-102: works before /setup ever ran, and keeps an existing mode."""
    repo = GuildSettingsRepository(session)

    await repo.mark_season_announced(1, 42)
    settings = await repo.get(1)
    assert settings is not None
    assert (settings.announced_season, settings.setup_mode) == (42, "development")

    await repo.set_mode(1, "launch")
    await repo.mark_season_announced(1, 43)
    settings = await repo.get(1)
    assert settings is not None
    assert (settings.announced_season, settings.setup_mode) == (43, "launch")
