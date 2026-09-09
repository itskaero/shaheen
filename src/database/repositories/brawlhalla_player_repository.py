"""Persistence for BrawlhallaPlayer — a cached player identity."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.brawlhalla_player import BrawlhallaPlayer


class BrawlhallaPlayerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_brawlhalla_id(self, brawlhalla_player_id: int) -> BrawlhallaPlayer | None:
        stmt = select(BrawlhallaPlayer).where(
            BrawlhallaPlayer.brawlhalla_player_id == brawlhalla_player_id
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get_by_id(self, player_id: int) -> BrawlhallaPlayer | None:
        return await self._session.get(BrawlhallaPlayer, player_id)

    async def upsert(
        self, *, brawlhalla_player_id: int, player_name: str, region: str | None
    ) -> BrawlhallaPlayer:
        existing = await self.get_by_brawlhalla_id(brawlhalla_player_id)
        if existing is not None:
            existing.player_name = player_name
            existing.region = region
            return existing

        player = BrawlhallaPlayer(
            brawlhalla_player_id=brawlhalla_player_id, player_name=player_name, region=region
        )
        self._session.add(player)
        await self._session.flush()
        return player
