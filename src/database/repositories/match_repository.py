"""Persistence for Match/MatchParticipant."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.discord_user import DiscordUser
from database.models.match import Match, MatchKind, MatchParticipant, MatchSide, MatchStatus
from database.models.shaheen_member import ShaheenMember


class MatchRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        guild_id: int,
        kind: MatchKind,
        participants: list[tuple[int, MatchSide]],
    ) -> Match:
        """`participants`: (shaheen_member_id, side) pairs."""
        match = Match(guild_id=guild_id, kind=kind, status=MatchStatus.PENDING_CONFIRMATION)
        # confirmed_at/status default correctly, but a Match starts with no
        # report yet — PENDING_CONFIRMATION is reused loosely until /report;
        # see MatchService for the actual state machine.
        self._session.add(match)
        await self._session.flush()

        for shaheen_member_id, side in participants:
            self._session.add(
                MatchParticipant(match_id=match.id, shaheen_member_id=shaheen_member_id, side=side)
            )
        await self._session.flush()
        return match

    async def get(self, match_id: int) -> Match | None:
        return await self._session.get(Match, match_id)

    async def get_participants(self, match_id: int) -> list[MatchParticipant]:
        stmt = select(MatchParticipant).where(MatchParticipant.match_id == match_id)
        return list((await self._session.execute(stmt)).scalars().all())

    async def is_participant(self, match_id: int, shaheen_member_id: int) -> MatchSide | None:
        stmt = select(MatchParticipant.side).where(
            MatchParticipant.match_id == match_id,
            MatchParticipant.shaheen_member_id == shaheen_member_id,
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def report(
        self, match: Match, *, reported_by_member_id: int, winning_side: MatchSide
    ) -> None:
        match.reported_by_member_id = reported_by_member_id
        match.reported_winning_side = winning_side
        match.status = MatchStatus.PENDING_CONFIRMATION
        await self._session.flush()

    async def confirm(self, match: Match) -> None:
        match.winning_side = match.reported_winning_side
        match.status = MatchStatus.CONFIRMED
        match.confirmed_at = datetime.now(UTC)
        await self._session.flush()

    async def dispute(self, match: Match) -> None:
        match.status = MatchStatus.DISPUTED
        await self._session.flush()

    async def resolve(
        self, match: Match, *, winning_side: MatchSide, resolved_by_member_id: int
    ) -> None:
        match.winning_side = winning_side
        match.status = MatchStatus.CONFIRMED
        match.resolved_by_member_id = resolved_by_member_id
        match.confirmed_at = datetime.now(UTC)
        await self._session.flush()

    async def list_recent_for_member(
        self, shaheen_member_id: int, *, limit: int = 10
    ) -> list[Match]:
        stmt = (
            select(Match)
            .join(MatchParticipant, MatchParticipant.match_id == Match.id)
            .where(MatchParticipant.shaheen_member_id == shaheen_member_id)
            .order_by(Match.created_at.desc())
            .limit(limit)
        )
        return list((await self._session.execute(stmt)).scalars().unique().all())

    async def participants_on_side(self, match_id: int, side: MatchSide) -> list[MatchParticipant]:
        stmt = select(MatchParticipant).where(
            MatchParticipant.match_id == match_id, MatchParticipant.side == side
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def discord_ids_on_side(self, match_id: int, side: MatchSide) -> list[int]:
        stmt = (
            select(DiscordUser.discord_id)
            .join(ShaheenMember, ShaheenMember.discord_user_id == DiscordUser.id)
            .join(MatchParticipant, MatchParticipant.shaheen_member_id == ShaheenMember.id)
            .where(MatchParticipant.match_id == match_id, MatchParticipant.side == side)
        )
        return list((await self._session.execute(stmt)).scalars().all())
