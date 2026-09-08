"""Persistence for ShaheenMember."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.shaheen_member import ShaheenMember


class ShaheenMemberRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

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
