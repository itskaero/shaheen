"""Persistence for LegendSnapshot — append-only, never updated."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.legend_snapshot import LegendSnapshot


class LegendSnapshotRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_all(self, snapshots: list[LegendSnapshot]) -> None:
        self._session.add_all(snapshots)
        await self._session.flush()

    async def list_latest_per_legend(self, brawlhalla_player_id: int) -> list[LegendSnapshot]:
        """One row per Legend this player has snapshots for — their most
        recent snapshot of each — ordered by games played, most first.

        Used for "legend mastery" (website + could back a future /legends
        summary command); snapshots are append-only per ADR-029, so the
        latest row per legend_name_key is the current lifetime total.
        """
        latest_per_legend = (
            select(
                LegendSnapshot.legend_name_key,
                func.max(LegendSnapshot.captured_at).label("captured_at"),
            )
            .where(LegendSnapshot.brawlhalla_player_id == brawlhalla_player_id)
            .group_by(LegendSnapshot.legend_name_key)
            .subquery()
        )
        stmt = (
            select(LegendSnapshot)
            .join(
                latest_per_legend,
                (LegendSnapshot.legend_name_key == latest_per_legend.c.legend_name_key)
                & (LegendSnapshot.captured_at == latest_per_legend.c.captured_at),
            )
            .where(LegendSnapshot.brawlhalla_player_id == brawlhalla_player_id)
            .order_by(LegendSnapshot.games.desc())
        )
        return list((await self._session.execute(stmt)).scalars().all())
