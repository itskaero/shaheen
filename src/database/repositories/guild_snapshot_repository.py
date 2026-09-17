"""Persistence for GuildSnapshot — append-only, never updated.

Same shape as RankingSnapshotRepository.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.guild_snapshot import GuildSnapshot


class GuildSnapshotRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, snapshot: GuildSnapshot) -> GuildSnapshot:
        self._session.add(snapshot)
        await self._session.flush()
        return snapshot

    async def get_latest(self, guild_id: int) -> GuildSnapshot | None:
        stmt = (
            select(GuildSnapshot)
            .where(GuildSnapshot.guild_id == guild_id)
            .order_by(GuildSnapshot.captured_at.desc())
            .limit(1)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()
