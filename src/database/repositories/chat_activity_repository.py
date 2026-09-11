"""Persistence for ChatActivity — chat XP/level (docs/DECISIONS.md ADR-065).

Stays thin: XP amounts, cooldown checks, and the level curve are all
services.chat_gamification's job (pure logic), not this repository's —
this module only stores/reads rows.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.chat_activity import ChatActivity


class ChatActivityRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, *, guild_id: int, discord_id: int) -> ChatActivity | None:
        stmt = select(ChatActivity).where(
            ChatActivity.guild_id == guild_id, ChatActivity.discord_id == discord_id
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get_or_create(self, *, guild_id: int, discord_id: int) -> ChatActivity:
        existing = await self.get(guild_id=guild_id, discord_id=discord_id)
        if existing is not None:
            return existing

        row = ChatActivity(guild_id=guild_id, discord_id=discord_id)
        self._session.add(row)
        await self._session.flush()
        return row

    async def record_message(
        self, *, guild_id: int, discord_id: int, xp_gain: int, now: datetime
    ) -> ChatActivity:
        """Increments xp/message_count and stamps last_xp_at. Does not
        touch `level` — the caller computes the new level (services.
        chat_gamification.level_for_xp) and sets it directly on the
        returned row before the session commits, so it can diff old vs.
        new level to detect a level-up.
        """
        row = await self.get_or_create(guild_id=guild_id, discord_id=discord_id)
        row.xp += xp_gain
        row.message_count += 1
        row.last_xp_at = now
        await self._session.flush()
        return row

    async def list_top(self, guild_id: int, *, limit: int = 10) -> list[ChatActivity]:
        stmt = (
            select(ChatActivity)
            .where(ChatActivity.guild_id == guild_id)
            .order_by(ChatActivity.xp.desc())
            .limit(limit)
        )
        return list((await self._session.execute(stmt)).scalars().all())
