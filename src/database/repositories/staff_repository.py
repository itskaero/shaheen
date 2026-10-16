"""Persistence for the mirrored Founder/Admin role holders (docs/DECISIONS.md ADR-135)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.brawlhalla_player import BrawlhallaPlayer
from database.models.staff_member import StaffMember


class StaffRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, staff: StaffMember) -> StaffMember:
        self._session.add(staff)
        await self._session.flush()
        return staff

    async def all_for_guild(self, guild_id: int) -> list[StaffMember]:
        stmt = select(StaffMember).where(StaffMember.guild_id == guild_id).order_by(StaffMember.id)
        return list((await self._session.execute(stmt)).scalars().all())

    async def by_discord(self, guild_id: int, discord_id: int) -> StaffMember | None:
        stmt = select(StaffMember).where(
            StaffMember.guild_id == guild_id, StaffMember.discord_id == discord_id
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def active_with_players(
        self, guild_id: int
    ) -> list[tuple[StaffMember, BrawlhallaPlayer | None]]:
        stmt = (
            select(StaffMember, BrawlhallaPlayer)
            .outerjoin(BrawlhallaPlayer, BrawlhallaPlayer.id == StaffMember.brawlhalla_player_id)
            .where(StaffMember.guild_id == guild_id, StaffMember.active.is_(True))
        )
        return [(row[0], row[1]) for row in (await self._session.execute(stmt)).all()]
