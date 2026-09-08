"""Persistence for DiscordUser."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.discord_user import DiscordUser


class DiscordUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_discord_id(self, discord_id: int) -> DiscordUser | None:
        stmt = select(DiscordUser).where(DiscordUser.discord_id == discord_id)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get_or_create(self, discord_id: int) -> DiscordUser:
        existing = await self.get_by_discord_id(discord_id)
        if existing is not None:
            return existing

        user = DiscordUser(discord_id=discord_id)
        self._session.add(user)
        await self._session.flush()
        return user
