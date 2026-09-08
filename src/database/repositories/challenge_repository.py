"""Persistence for Challenge."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from database.models.challenge import Challenge, ChallengeStatus


class ChallengeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self, *, guild_id: int, challenger_member_id: int, opponent_member_id: int
    ) -> Challenge:
        challenge = Challenge(
            guild_id=guild_id,
            challenger_member_id=challenger_member_id,
            opponent_member_id=opponent_member_id,
        )
        self._session.add(challenge)
        await self._session.flush()
        return challenge

    async def get(self, challenge_id: int) -> Challenge | None:
        return await self._session.get(Challenge, challenge_id)

    async def accept(self, challenge: Challenge, *, match_id: int) -> None:
        challenge.status = ChallengeStatus.ACCEPTED
        challenge.match_id = match_id
        challenge.responded_at = datetime.now(UTC)
        await self._session.flush()

    async def decline(self, challenge: Challenge) -> None:
        challenge.status = ChallengeStatus.DECLINED
        challenge.responded_at = datetime.now(UTC)
        await self._session.flush()
