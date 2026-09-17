"""Guild-level Discord stat snapshots — Discord-agnostic (docs/ARCHITECTURE.md).

Takes plain ints, never a discord.Guild object: bot/cogs/clan.py reads
guild.member_count/premium_tier/premium_subscription_count off its already-
cached Guild and passes the primitives in here, the same separation this
codebase uses everywhere else to keep the service layer usable without
discord.py (CLAUDE.md's "business rules must remain usable without
Discord"). Deliberately a separate service from SnapshotService: that one
is Brawlhalla-API-driven and explicitly documented as never touching
Discord — guild member/boost counts come from Discord, not Brawlhalla, so
they don't belong there.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from database.models.guild_snapshot import GuildSnapshot
from database.repositories.guild_snapshot_repository import GuildSnapshotRepository


class GuildSnapshotService:
    def __init__(self, session: AsyncSession) -> None:
        self._snapshots = GuildSnapshotRepository(session)

    async def record(
        self, guild_id: int, *, member_count: int, boost_tier: int, boost_count: int
    ) -> GuildSnapshot:
        snapshot = GuildSnapshot(
            guild_id=guild_id,
            captured_at=datetime.now(UTC),
            member_count=member_count,
            boost_tier=boost_tier,
            boost_count=boost_count,
        )
        return await self._snapshots.add(snapshot)
