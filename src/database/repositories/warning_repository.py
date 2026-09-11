"""Persistence for Warning — moderation records (docs/DECISIONS.md ADR-065)."""

from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.warning import Warning


class WarningRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(
        self, *, guild_id: int, discord_id: int, moderator_discord_id: int, reason: str
    ) -> Warning:
        warning = Warning(
            guild_id=guild_id,
            discord_id=discord_id,
            moderator_discord_id=moderator_discord_id,
            reason=reason,
        )
        self._session.add(warning)
        await self._session.flush()
        return warning

    async def list_active_for_member(self, *, guild_id: int, discord_id: int) -> list[Warning]:
        stmt = (
            select(Warning)
            .where(
                Warning.guild_id == guild_id,
                Warning.discord_id == discord_id,
                Warning.active.is_(True),
            )
            .order_by(Warning.created_at.desc())
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def count_active_for_member(self, *, guild_id: int, discord_id: int) -> int:
        return len(await self.list_active_for_member(guild_id=guild_id, discord_id=discord_id))

    async def clear_all_for_member(self, *, guild_id: int, discord_id: int) -> int:
        """Soft-clears every active warning for a member — returns the
        count cleared. Rows stay in the table (active=False) rather than
        being deleted, preserving the audit trail.
        """
        active = await self.list_active_for_member(guild_id=guild_id, discord_id=discord_id)
        if not active:
            return 0
        await self._session.execute(
            update(Warning)
            .where(Warning.id.in_([w.id for w in active]))
            .values(active=False)
        )
        return len(active)
