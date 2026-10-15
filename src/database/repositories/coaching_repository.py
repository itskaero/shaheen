"""Persistence for coaches and coaching requests (docs/DECISIONS.md ADR-126)."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.coaching import Coach, CoachingRequest


class CoachingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # --- coaches ------------------------------------------------------------

    async def add_coach(self, coach: Coach) -> Coach:
        self._session.add(coach)
        await self._session.flush()
        return coach

    async def get_coach(self, coach_id: int) -> Coach | None:
        return await self._session.get(Coach, coach_id)

    async def coach_by_discord(self, guild_id: int, discord_id: int) -> Coach | None:
        stmt = select(Coach).where(Coach.guild_id == guild_id, Coach.discord_id == discord_id)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def coaches(self, guild_id: int, *, active_only: bool = True) -> list[Coach]:
        stmt = select(Coach).where(Coach.guild_id == guild_id)
        if active_only:
            stmt = stmt.where(Coach.active.is_(True))
        stmt = stmt.order_by(Coach.created_at, Coach.id)
        return list((await self._session.execute(stmt)).scalars().all())

    # --- requests -----------------------------------------------------------

    async def add_request(self, request: CoachingRequest) -> CoachingRequest:
        self._session.add(request)
        await self._session.flush()
        return request

    async def get_request(self, request_id: int) -> CoachingRequest | None:
        return await self._session.get(CoachingRequest, request_id)

    async def open_requests(
        self,
        guild_id: int,
        *,
        since: datetime,
        coach_id: int | None = None,
        student_discord_id: int | None = None,
    ) -> list[CoachingRequest]:
        """Open requests made after `since` (older ones have lapsed)."""
        stmt = select(CoachingRequest).where(
            CoachingRequest.guild_id == guild_id,
            CoachingRequest.status == "open",
            CoachingRequest.created_at >= since,
        )
        if coach_id is not None:
            stmt = stmt.where(CoachingRequest.coach_id == coach_id)
        if student_discord_id is not None:
            stmt = stmt.where(CoachingRequest.student_discord_id == student_discord_id)
        stmt = stmt.order_by(CoachingRequest.created_at)
        return list((await self._session.execute(stmt)).scalars().all())

    async def accepted_counts(self, coach_ids: Iterable[int]) -> dict[int, int]:
        ids = list(coach_ids)
        if not ids:
            return {}
        stmt = (
            select(CoachingRequest.coach_id, func.count(CoachingRequest.id))
            .where(CoachingRequest.coach_id.in_(ids), CoachingRequest.status == "accepted")
            .group_by(CoachingRequest.coach_id)
        )
        return {coach_id: int(n) for coach_id, n in (await self._session.execute(stmt)).all()}
