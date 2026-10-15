"""Persistence for finished Clan Wars weeks (docs/DECISIONS.md ADR-131)."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.clan_war_result import ClanWarResult


class ClanWarRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_all(self, results: list[ClanWarResult]) -> None:
        self._session.add_all(results)
        await self._session.flush()

    async def week_recorded(self, guild_id: int, week_start: date) -> bool:
        stmt = (
            select(ClanWarResult.id)
            .where(ClanWarResult.guild_id == guild_id, ClanWarResult.week_start == week_start)
            .limit(1)
        )
        return (await self._session.execute(stmt)).first() is not None

    async def for_season(self, guild_id: int, season: int) -> list[ClanWarResult]:
        """Every recorded team-week of a season, newest week first."""
        stmt = (
            select(ClanWarResult)
            .where(ClanWarResult.guild_id == guild_id, ClanWarResult.season == season)
            .order_by(ClanWarResult.week_start.desc(), ClanWarResult.place)
        )
        return list((await self._session.execute(stmt)).scalars().all())
