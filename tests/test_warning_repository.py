from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from database.repositories.warning_repository import WarningRepository

GUILD_ID = 1


async def test_add_creates_active_warning(session: AsyncSession) -> None:
    repo = WarningRepository(session)
    warning = await repo.add(
        guild_id=GUILD_ID, discord_id=100, moderator_discord_id=999, reason="spam"
    )
    assert warning.active is True
    assert warning.reason == "spam"
    assert warning.discord_id == 100
    assert warning.moderator_discord_id == 999


async def test_list_active_for_member_scopes_by_guild_and_member(session: AsyncSession) -> None:
    repo = WarningRepository(session)
    await repo.add(guild_id=GUILD_ID, discord_id=100, moderator_discord_id=1, reason="a")
    await repo.add(guild_id=GUILD_ID, discord_id=100, moderator_discord_id=1, reason="b")
    await repo.add(guild_id=GUILD_ID, discord_id=200, moderator_discord_id=1, reason="c")
    await repo.add(guild_id=2, discord_id=100, moderator_discord_id=1, reason="d")

    warnings = await repo.list_active_for_member(guild_id=GUILD_ID, discord_id=100)
    assert {w.reason for w in warnings} == {"a", "b"}


async def test_list_active_for_member_most_recent_first(session: AsyncSession) -> None:
    repo = WarningRepository(session)
    await repo.add(guild_id=GUILD_ID, discord_id=100, moderator_discord_id=1, reason="first")
    await repo.add(guild_id=GUILD_ID, discord_id=100, moderator_discord_id=1, reason="second")

    warnings = await repo.list_active_for_member(guild_id=GUILD_ID, discord_id=100)
    assert warnings[0].reason == "second"
    assert warnings[1].reason == "first"


async def test_count_active_for_member(session: AsyncSession) -> None:
    repo = WarningRepository(session)
    assert await repo.count_active_for_member(guild_id=GUILD_ID, discord_id=100) == 0

    await repo.add(guild_id=GUILD_ID, discord_id=100, moderator_discord_id=1, reason="a")
    await repo.add(guild_id=GUILD_ID, discord_id=100, moderator_discord_id=1, reason="b")

    assert await repo.count_active_for_member(guild_id=GUILD_ID, discord_id=100) == 2


async def test_clear_all_for_member_soft_clears_and_returns_count(session: AsyncSession) -> None:
    repo = WarningRepository(session)
    await repo.add(guild_id=GUILD_ID, discord_id=100, moderator_discord_id=1, reason="a")
    await repo.add(guild_id=GUILD_ID, discord_id=100, moderator_discord_id=1, reason="b")
    await repo.add(guild_id=GUILD_ID, discord_id=200, moderator_discord_id=1, reason="unrelated")

    cleared = await repo.clear_all_for_member(guild_id=GUILD_ID, discord_id=100)
    assert cleared == 2

    # Soft-cleared, not deleted — active_for_member no longer returns them.
    assert await repo.list_active_for_member(guild_id=GUILD_ID, discord_id=100) == []
    # Untouched member's warning stays active.
    assert len(await repo.list_active_for_member(guild_id=GUILD_ID, discord_id=200)) == 1


async def test_clear_all_for_member_with_no_warnings_returns_zero(session: AsyncSession) -> None:
    repo = WarningRepository(session)
    assert await repo.clear_all_for_member(guild_id=GUILD_ID, discord_id=100) == 0
