"""Persistence for Scrim/ScrimSignup."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.match import MatchKind, MatchSide
from database.models.scrim import Scrim, ScrimSignup, ScrimStatus


class ScrimRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, *, guild_id: int, created_by_member_id: int, kind: MatchKind) -> Scrim:
        scrim = Scrim(guild_id=guild_id, created_by_member_id=created_by_member_id, kind=kind)
        self._session.add(scrim)
        await self._session.flush()
        return scrim

    async def get(self, scrim_id: int) -> Scrim | None:
        return await self._session.get(Scrim, scrim_id)

    async def set_announcement(self, scrim: Scrim, *, channel_id: int, message_id: int) -> None:
        scrim.announcement_channel_id = channel_id
        scrim.announcement_message_id = message_id
        await self._session.flush()

    async def mark_full(self, scrim: Scrim, *, match_id: int) -> None:
        scrim.status = ScrimStatus.FULL
        scrim.match_id = match_id
        await self._session.flush()

    async def cancel(self, scrim: Scrim) -> None:
        scrim.status = ScrimStatus.CANCELLED
        await self._session.flush()


class ScrimSignupRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_scrim(self, scrim_id: int) -> list[ScrimSignup]:
        stmt = select(ScrimSignup).where(ScrimSignup.scrim_id == scrim_id)
        return list((await self._session.execute(stmt)).scalars().all())

    async def get_for_member(self, scrim_id: int, shaheen_member_id: int) -> ScrimSignup | None:
        stmt = select(ScrimSignup).where(
            ScrimSignup.scrim_id == scrim_id, ScrimSignup.shaheen_member_id == shaheen_member_id
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def add(self, *, scrim_id: int, shaheen_member_id: int, side: MatchSide) -> ScrimSignup:
        signup = ScrimSignup(scrim_id=scrim_id, shaheen_member_id=shaheen_member_id, side=side)
        self._session.add(signup)
        await self._session.flush()
        return signup
