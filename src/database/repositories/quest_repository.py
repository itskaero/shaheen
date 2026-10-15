"""Persistence for weekly quest completions (docs/DECISIONS.md ADR-128)."""

from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.quest_completion import QuestCompletion


class QuestRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, completion: QuestCompletion) -> QuestCompletion:
        self._session.add(completion)
        await self._session.flush()
        return completion

    async def done_this_week(self, player_id: int, week_start: date) -> set[str]:
        stmt = select(QuestCompletion.quest_key).where(
            QuestCompletion.brawlhalla_player_id == player_id,
            QuestCompletion.week_start == week_start,
        )
        return set((await self._session.execute(stmt)).scalars().all())

    async def season_count(self, player_id: int, season: int) -> int:
        stmt = select(func.count(QuestCompletion.id)).where(
            QuestCompletion.brawlhalla_player_id == player_id,
            QuestCompletion.season == season,
        )
        return int((await self._session.execute(stmt)).scalar_one())
