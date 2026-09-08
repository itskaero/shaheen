"""Persistence for LegendSnapshot — append-only, never updated."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from database.models.legend_snapshot import LegendSnapshot


class LegendSnapshotRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_all(self, snapshots: list[LegendSnapshot]) -> None:
        self._session.add_all(snapshots)
        await self._session.flush()
