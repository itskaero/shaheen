"""GuildSnapshotService + GuildSnapshotRepository: persistence, get_latest ordering."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from database.repositories.guild_snapshot_repository import GuildSnapshotRepository
from services.guild_snapshot_service import GuildSnapshotService

GUILD_ID = 1


async def test_get_latest_returns_none_when_no_snapshot_exists(session: AsyncSession) -> None:
    repo = GuildSnapshotRepository(session)
    assert await repo.get_latest(GUILD_ID) is None


async def test_record_persists_a_snapshot(session: AsyncSession) -> None:
    service = GuildSnapshotService(session)

    snapshot = await service.record(GUILD_ID, member_count=42, boost_tier=1, boost_count=3)

    assert snapshot.guild_id == GUILD_ID
    assert snapshot.member_count == 42
    assert snapshot.boost_tier == 1
    assert snapshot.boost_count == 3
    assert snapshot.captured_at is not None


async def test_get_latest_returns_the_most_recently_recorded_snapshot(
    session: AsyncSession,
) -> None:
    service = GuildSnapshotService(session)
    repo = GuildSnapshotRepository(session)

    await service.record(GUILD_ID, member_count=40, boost_tier=0, boost_count=0)
    latest = await service.record(GUILD_ID, member_count=45, boost_tier=1, boost_count=2)

    result = await repo.get_latest(GUILD_ID)
    assert result is not None
    assert result.id == latest.id
    assert result.member_count == 45


async def test_get_latest_is_scoped_to_the_given_guild(session: AsyncSession) -> None:
    service = GuildSnapshotService(session)
    repo = GuildSnapshotRepository(session)

    await service.record(GUILD_ID, member_count=10, boost_tier=0, boost_count=0)
    await service.record(GUILD_ID + 1, member_count=99, boost_tier=0, boost_count=0)

    result = await repo.get_latest(GUILD_ID)
    assert result is not None
    assert result.member_count == 10
