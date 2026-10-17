"""Reaction role bindings (docs/DECISIONS.md ADR-137)."""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.reaction_role import ReactionRole


class ReactionRoleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def for_message(self, message_id: int) -> list[ReactionRole]:
        stmt = select(ReactionRole).where(ReactionRole.message_id == message_id)
        return list((await self._session.execute(stmt.order_by(ReactionRole.id))).scalars())

    async def for_guild(self, guild_id: int) -> list[ReactionRole]:
        stmt = select(ReactionRole).where(ReactionRole.guild_id == guild_id)
        return list((await self._session.execute(stmt.order_by(ReactionRole.id))).scalars())

    async def message_ids(self) -> set[int]:
        return set((await self._session.execute(select(ReactionRole.message_id))).scalars())

    async def add(self, binding: ReactionRole) -> ReactionRole:
        self._session.add(binding)
        await self._session.flush()
        return binding

    async def delete(self, binding: ReactionRole) -> None:
        await self._session.delete(binding)
        await self._session.flush()

    async def delete_message(self, message_id: int) -> int:
        stmt = delete(ReactionRole).where(ReactionRole.message_id == message_id)
        result = await self._session.execute(stmt.returning(ReactionRole.id))
        return len(result.all())
