"""Persistence for RankingSnapshot — append-only, never updated.

`player_id` throughout this repository is BrawlhallaPlayer's internal PK
(the same value RankingSnapshot.brawlhalla_player_id stores as a foreign
key) — not the external Brawlhalla player ID from the API. Mixing the two
up is an easy, silent bug (docs/DECISIONS.md callers must pass `player.id`,
never `player.brawlhalla_player_id`, here).
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.ranking_snapshot import RankingSnapshot


class RankingSnapshotRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, snapshot: RankingSnapshot) -> RankingSnapshot:
        self._session.add(snapshot)
        await self._session.flush()
        return snapshot

    async def get_latest(self, player_id: int) -> RankingSnapshot | None:
        stmt = (
            select(RankingSnapshot)
            .where(RankingSnapshot.brawlhalla_player_id == player_id)
            .order_by(RankingSnapshot.captured_at.desc())
            .limit(1)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_recent(self, player_id: int, *, limit: int = 10) -> list[RankingSnapshot]:
        stmt = (
            select(RankingSnapshot)
            .where(RankingSnapshot.brawlhalla_player_id == player_id)
            .order_by(RankingSnapshot.captured_at.desc())
            .limit(limit)
        )
        return list((await self._session.execute(stmt)).scalars().all())
