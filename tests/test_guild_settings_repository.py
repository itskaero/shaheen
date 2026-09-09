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
