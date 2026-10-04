"""Persistence for LinkCode (docs/DECISIONS.md ADR-107)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.link_code import LinkCode


class LinkCodeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, code: LinkCode) -> LinkCode:
        self._session.add(code)
        await self._session.flush()
        return code

    async def get_by_hash(self, code_hash: str) -> LinkCode | None:
        stmt = select(LinkCode).where(LinkCode.code_hash == code_hash)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def count_issued_since(self, *, guild_id: int, discord_id: int, since: datetime) -> int:
        stmt = select(func.count()).where(
            LinkCode.guild_id == guild_id,
            LinkCode.discord_id == discord_id,
            LinkCode.created_at >= since,
        )
        return int((await self._session.execute(stmt)).scalar_one())

    async def expire_pending(self, *, guild_id: int, discord_id: int, now: datetime) -> None:
        """A new code replaces any still-pending one: only the latest works."""
        await self._session.execute(
            update(LinkCode)
            .where(
                LinkCode.guild_id == guild_id,
                LinkCode.discord_id == discord_id,
                LinkCode.used_at.is_(None),
                LinkCode.expires_at > now,
            )
            .values(expires_at=now)
        )
