from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from database.repositories.chat_activity_repository import ChatActivityRepository

GUILD_ID = 1
NOW = datetime(2026, 1, 1, tzinfo=UTC)


async def test_get_returns_none_when_missing(session: AsyncSession) -> None:
    repo = ChatActivityRepository(session)
    assert await repo.get(guild_id=GUILD_ID, discord_id=100) is None


async def test_get_or_create_creates_a_zeroed_row(session: AsyncSession) -> None:
    repo = ChatActivityRepository(session)
    row = await repo.get_or_create(guild_id=GUILD_ID, discord_id=100)
    assert row.xp == 0
    assert row.level == 1
    assert row.message_count == 0
    assert row.last_xp_at is None


async def test_get_or_create_is_idempotent(session: AsyncSession) -> None:
    repo = ChatActivityRepository(session)
    first = await repo.get_or_create(guild_id=GUILD_ID, discord_id=100)
    second = await repo.get_or_create(guild_id=GUILD_ID, discord_id=100)
    assert first.id == second.id


async def test_record_message_increments_xp_and_message_count(session: AsyncSession) -> None:
    repo = ChatActivityRepository(session)
    row = await repo.record_message(guild_id=GUILD_ID, discord_id=100, xp_gain=10, now=NOW)
    assert row.xp == 10
    assert row.message_count == 1
    assert row.last_xp_at == NOW

    row = await repo.record_message(guild_id=GUILD_ID, discord_id=100, xp_gain=5, now=NOW)
    assert row.xp == 15
    assert row.message_count == 2


async def test_record_message_does_not_touch_level(session: AsyncSession) -> None:
    """By design (docs/DECISIONS.md ADR-065): `level` is the caller's job
    to set after diffing old-vs-new for level-up detection — this
    repository only ever writes xp/message_count/last_xp_at.
    """
    repo = ChatActivityRepository(session)
    row = await repo.record_message(guild_id=GUILD_ID, discord_id=100, xp_gain=10_000, now=NOW)
    assert row.xp == 10_000
    assert row.level == 1  # unchanged, despite xp far exceeding level 1's threshold


async def test_list_top_orders_by_xp_descending_and_scopes_by_guild(
    session: AsyncSession,
) -> None:
    repo = ChatActivityRepository(session)
    await repo.record_message(guild_id=GUILD_ID, discord_id=1, xp_gain=5, now=NOW)
    await repo.record_message(guild_id=GUILD_ID, discord_id=2, xp_gain=50, now=NOW)
    await repo.record_message(guild_id=GUILD_ID, discord_id=3, xp_gain=20, now=NOW)
    await repo.record_message(guild_id=2, discord_id=4, xp_gain=999, now=NOW)

    top = await repo.list_top(GUILD_ID, limit=10)
    assert [row.discord_id for row in top] == [2, 3, 1]


async def test_list_top_respects_limit(session: AsyncSession) -> None:
    repo = ChatActivityRepository(session)
    for discord_id in range(5):
        await repo.record_message(guild_id=GUILD_ID, discord_id=discord_id, xp_gain=1, now=NOW)

    top = await repo.list_top(GUILD_ID, limit=2)
    assert len(top) == 2


async def test_record_message_increments_weekly_xp_alongside_xp(session: AsyncSession) -> None:
    repo = ChatActivityRepository(session)
    row = await repo.record_message(guild_id=GUILD_ID, discord_id=100, xp_gain=10, now=NOW)
    assert row.weekly_xp == 10
    row = await repo.record_message(guild_id=GUILD_ID, discord_id=100, xp_gain=5, now=NOW)
    assert row.weekly_xp == 15


async def test_list_top_weekly_orders_by_weekly_xp_and_excludes_zero(
    session: AsyncSession,
) -> None:
    repo = ChatActivityRepository(session)
    await repo.record_message(guild_id=GUILD_ID, discord_id=1, xp_gain=10, now=NOW)
    await repo.record_message(guild_id=GUILD_ID, discord_id=2, xp_gain=50, now=NOW)
    await repo.get_or_create(guild_id=GUILD_ID, discord_id=3)  # never talked — weekly_xp stays 0

    top = await repo.list_top_weekly(GUILD_ID, limit=10)
    assert [row.discord_id for row in top] == [2, 1]


async def test_reset_weekly_zeroes_weekly_xp_but_not_xp(session: AsyncSession) -> None:
    repo = ChatActivityRepository(session)
    await repo.record_message(guild_id=GUILD_ID, discord_id=1, xp_gain=10, now=NOW)
    await repo.record_message(guild_id=2, discord_id=1, xp_gain=99, now=NOW)  # other guild

    await repo.reset_weekly(GUILD_ID)

    row = await repo.get(guild_id=GUILD_ID, discord_id=1)
    assert row is not None
    assert row.weekly_xp == 0
    assert row.xp == 10  # all-time total untouched

    other_guild_row = await repo.get(guild_id=2, discord_id=1)
    assert other_guild_row is not None
    assert other_guild_row.weekly_xp == 99  # a different guild's counter is untouched
