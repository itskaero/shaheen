"""Persistence for PakistanBoardEntry (docs/DECISIONS.md ADR-099)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.brawlhalla_player import BrawlhallaPlayer
from database.models.pakistan_board_entry import PakistanBoardEntry


class PakistanBoardRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_active(self, guild_id: int, player_id: int) -> PakistanBoardEntry | None:
        """`player_id` is the internal BrawlhallaPlayer.id, not the Brawlhalla ID."""
        stmt = select(PakistanBoardEntry).where(
            PakistanBoardEntry.guild_id == guild_id,
            PakistanBoardEntry.brawlhalla_player_id == player_id,
            PakistanBoardEntry.removed_at.is_(None),
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get_active_for_owner(
        self, guild_id: int, discord_id: int
    ) -> PakistanBoardEntry | None:
        stmt = select(PakistanBoardEntry).where(
            PakistanBoardEntry.guild_id == guild_id,
            PakistanBoardEntry.owner_discord_id == discord_id,
            PakistanBoardEntry.removed_at.is_(None),
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def count_active(self, guild_id: int) -> int:
        stmt = select(func.count(PakistanBoardEntry.id)).where(
            PakistanBoardEntry.guild_id == guild_id, PakistanBoardEntry.removed_at.is_(None)
        )
        return int((await self._session.execute(stmt)).scalar_one())

    async def add(
        self,
        *,
        guild_id: int,
        player_id: int,
        added_by_discord_id: int,
        owner_discord_id: int | None,
    ) -> PakistanBoardEntry:
        entry = PakistanBoardEntry(
            guild_id=guild_id,
            brawlhalla_player_id=player_id,
            owner_discord_id=owner_discord_id,
            added_by_discord_id=added_by_discord_id,
            added_at=datetime.now(UTC),
        )
        self._session.add(entry)
        await self._session.flush()
        return entry

    async def remove(self, entry: PakistanBoardEntry) -> None:
        entry.removed_at = datetime.now(UTC)
        await self._session.flush()

    async def list_active(self, guild_id: int) -> list[tuple[PakistanBoardEntry, BrawlhallaPlayer]]:
        stmt = (
            select(PakistanBoardEntry, BrawlhallaPlayer)
            .join(BrawlhallaPlayer, BrawlhallaPlayer.id == PakistanBoardEntry.brawlhalla_player_id)
            .where(PakistanBoardEntry.guild_id == guild_id, PakistanBoardEntry.removed_at.is_(None))
        )
        result = await self._session.execute(stmt)
        return [(entry, player) for entry, player in result]
