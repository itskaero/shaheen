"""Persistence for MemberPlayerLink — link/unlink history."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.member_player_link import MemberPlayerLink


class MemberPlayerLinkRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_active(self, shaheen_member_id: int) -> MemberPlayerLink | None:
        stmt = select(MemberPlayerLink).where(
            MemberPlayerLink.shaheen_member_id == shaheen_member_id,
            MemberPlayerLink.unlinked_at.is_(None),
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def link(self, *, shaheen_member_id: int, brawlhalla_player_id: int) -> MemberPlayerLink:
        """Unlink any existing active link, then create a new one (ADR-025)."""
        active = await self.get_active(shaheen_member_id)
        if active is not None:
            active.unlinked_at = datetime.now(UTC)

        link = MemberPlayerLink(
            shaheen_member_id=shaheen_member_id,
            brawlhalla_player_id=brawlhalla_player_id,
            linked_at=datetime.now(UTC),
        )
        self._session.add(link)
        await self._session.flush()
        return link

    async def unlink(self, shaheen_member_id: int) -> MemberPlayerLink | None:
        active = await self.get_active(shaheen_member_id)
        if active is None:
            return None
        active.unlinked_at = datetime.now(UTC)
        return active
