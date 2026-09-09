"""Persistence for ShaheenMember."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.discord_user import DiscordUser
from database.models.shaheen_member import ShaheenMember


class ShaheenMemberRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def count_for_guild(self, guild_id: int) -> int:
        stmt = (
            select(func.count())
            .select_from(ShaheenMember)
            .where(ShaheenMember.guild_id == guild_id)
        )
        return (await self._session.execute(stmt)).scalar_one()

    async def get_discord_id(self, shaheen_member_id: int) -> int | None:
        stmt = (
            select(DiscordUser.discord_id)
            .join(ShaheenMember, ShaheenMember.discord_user_id == DiscordUser.id)
            .where(ShaheenMember.id == shaheen_member_id)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get(self, *, discord_user_id: int, guild_id: int) -> ShaheenMember | None:
        stmt = select(ShaheenMember).where(
            ShaheenMember.discord_user_id == discord_user_id,
            ShaheenMember.guild_id == guild_id,
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get_or_create(
        self, *, discord_user_id: int, guild_id: int, joined_at: datetime | None = None
    ) -> ShaheenMember:
        existing = await self.get(discord_user_id=discord_user_id, guild_id=guild_id)
        if existing is not None:
            return existing

        member = ShaheenMember(
            discord_user_id=discord_user_id, guild_id=guild_id, joined_at=joined_at
        )
        self._session.add(member)
        await self._session.flush()
        return member
