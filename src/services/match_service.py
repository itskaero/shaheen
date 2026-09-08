"""Business logic behind /challenge, /scrim, /match, /report — usable
without Discord.

docs/DECISIONS.md ADR-033 (confirm/dispute), ADR-034 (1v1/2v2 via sides).
Competitive matches don't require a linked Brawlhalla account — this is
internal clan record-keeping, distinct from live Brawlhalla data.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import NotFoundError, PermissionDeniedError, ShaheenError
from database.models.challenge import Challenge
from database.models.match import Match, MatchKind, MatchSide
from database.models.scrim import Scrim, ScrimStatus
from database.repositories.challenge_repository import ChallengeRepository
from database.repositories.discord_user_repository import DiscordUserRepository
from database.repositories.match_repository import MatchRepository
from database.repositories.scrim_repository import ScrimRepository, ScrimSignupRepository
from database.repositories.shaheen_member_repository import ShaheenMemberRepository

_SIDE_CAPACITY: dict[MatchKind, int] = {MatchKind.ONE_V_ONE: 1, MatchKind.TWO_V_TWO: 2}


def _other_side(side: MatchSide) -> MatchSide:
    return MatchSide.B if side is MatchSide.A else MatchSide.A


@dataclass
class ScrimJoinResult:
    scrim: Scrim
    match: Match | None  # set once the scrim just filled
    side_counts: tuple[int, int]  # (side A, side B) after this join


class MatchService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._discord_users = DiscordUserRepository(session)
        self._members = ShaheenMemberRepository(session)
        self._matches = MatchRepository(session)
        self._challenges = ChallengeRepository(session)
        self._scrims = ScrimRepository(session)
        self._scrim_signups = ScrimSignupRepository(session)

    async def _member_id(
        self, *, guild_id: int, discord_id: int, joined_at: datetime | None = None
    ) -> int:
        discord_user = await self._discord_users.get_or_create(discord_id)
        member = await self._members.get_or_create(
            discord_user_id=discord_user.id, guild_id=guild_id, joined_at=joined_at
        )
        return member.id

    # --- Challenges -----------------------------------------------------

    async def create_challenge(
        self,
        *,
        guild_id: int,
        challenger_discord_id: int,
        challenger_joined_at: datetime | None,
        opponent_discord_id: int,
        opponent_joined_at: datetime | None,
    ) -> Challenge:
        if challenger_discord_id == opponent_discord_id:
            raise ShaheenError("You can't challenge yourself.")
        challenger_id = await self._member_id(
            guild_id=guild_id, discord_id=challenger_discord_id, joined_at=challenger_joined_at
        )
        opponent_id = await self._member_id(
            guild_id=guild_id, discord_id=opponent_discord_id, joined_at=opponent_joined_at
        )
        return await self._challenges.create(
            guild_id=guild_id, challenger_member_id=challenger_id, opponent_member_id=opponent_id
        )

    async def accept_challenge(self, challenge_id: int) -> Match:
        challenge = await self._challenges.get(challenge_id)
        if challenge is None:
            raise NotFoundError("That challenge no longer exists.")
        match = await self._matches.create(
            guild_id=challenge.guild_id,
            kind=MatchKind.ONE_V_ONE,
            participants=[
                (challenge.challenger_member_id, MatchSide.A),
                (challenge.opponent_member_id, MatchSide.B),
            ],
        )
        await self._challenges.accept(challenge, match_id=match.id)
        return match

    async def decline_challenge(self, challenge_id: int) -> None:
        challenge = await self._challenges.get(challenge_id)
        if challenge is None:
            raise NotFoundError("That challenge no longer exists.")
        await self._challenges.decline(challenge)

    # --- Scrims -----------------------------------------------------------

    async def create_scrim(
        self,
        *,
        guild_id: int,
        creator_discord_id: int,
        creator_joined_at: datetime | None,
        kind: MatchKind,
    ) -> Scrim:
        creator_id = await self._member_id(
            guild_id=guild_id, discord_id=creator_discord_id, joined_at=creator_joined_at
        )
        return await self._scrims.create(
            guild_id=guild_id, created_by_member_id=creator_id, kind=kind
        )

    async def resolve_scrim_side(self, scrim_id: int) -> MatchSide:
        """For 1v1's single "Join" button: whichever side still has room."""
        scrim = await self._scrims.get(scrim_id)
        if scrim is None:
            raise NotFoundError("That scrim no longer exists.")
        signups = await self._scrim_signups.list_for_scrim(scrim_id)
        capacity = _SIDE_CAPACITY[scrim.kind]
        a_count = len([s for s in signups if s.side == MatchSide.A])
        return MatchSide.A if a_count < capacity else MatchSide.B

    async def join_scrim(
        self,
        *,
        scrim_id: int,
        discord_id: int,
        joined_at: datetime | None,
        side: MatchSide,
    ) -> ScrimJoinResult:
        scrim = await self._scrims.get(scrim_id)
        if scrim is None:
            raise NotFoundError("That scrim no longer exists.")
        if scrim.status != ScrimStatus.OPEN:
            raise ShaheenError("This scrim is no longer open for sign-ups.")

        member_id = await self._member_id(
            guild_id=scrim.guild_id, discord_id=discord_id, joined_at=joined_at
        )
        if await self._scrim_signups.get_for_member(scrim_id, member_id) is not None:
            raise ShaheenError("You've already signed up for this scrim.")

        signups = await self._scrim_signups.list_for_scrim(scrim_id)
        capacity = _SIDE_CAPACITY[scrim.kind]
        if len([s for s in signups if s.side == side]) >= capacity:
            raise ShaheenError(f"Side {side.value} is already full.")

        new_signup = await self._scrim_signups.add(
            scrim_id=scrim_id, shaheen_member_id=member_id, side=side
        )
        signups.append(new_signup)

        a_count = len([s for s in signups if s.side == MatchSide.A])
        b_count = len([s for s in signups if s.side == MatchSide.B])
        if a_count < capacity or b_count < capacity:
            return ScrimJoinResult(scrim=scrim, match=None, side_counts=(a_count, b_count))

        match = await self._matches.create(
            guild_id=scrim.guild_id,
            kind=scrim.kind,
            participants=[(s.shaheen_member_id, s.side) for s in signups],
        )
        await self._scrims.mark_full(scrim, match_id=match.id)
        return ScrimJoinResult(scrim=scrim, match=match, side_counts=(a_count, b_count))

    # --- Ad-hoc matches -----------------------------------------------------

    async def create_match(
        self,
        *,
        guild_id: int,
        kind: MatchKind,
        side_a: list[tuple[int, datetime | None]],
        side_b: list[tuple[int, datetime | None]],
    ) -> Match:
        capacity = _SIDE_CAPACITY[kind]
        if len(side_a) != capacity or len(side_b) != capacity:
            raise ShaheenError(f"A {kind.value} match needs exactly {capacity} player(s) per side.")
        if {d for d, _ in side_a} & {d for d, _ in side_b}:
            raise ShaheenError("A player can't be on both sides.")

        participants = []
        for discord_id, joined_at in side_a:
            member_id = await self._member_id(
                guild_id=guild_id, discord_id=discord_id, joined_at=joined_at
            )
            participants.append((member_id, MatchSide.A))
        for discord_id, joined_at in side_b:
            member_id = await self._member_id(
                guild_id=guild_id, discord_id=discord_id, joined_at=joined_at
            )
            participants.append((member_id, MatchSide.B))

        return await self._matches.create(guild_id=guild_id, kind=kind, participants=participants)

    # --- Reporting / confirmation -----------------------------------------

    async def report_result(
        self, *, match_id: int, guild_id: int, reporter_discord_id: int, reporter_won: bool
    ) -> Match:
        match = await self._matches.get(match_id)
        if match is None:
            raise NotFoundError("That match no longer exists.")

        reporter_member_id = await self._member_id(
            guild_id=guild_id, discord_id=reporter_discord_id
        )
        reporter_side = await self._matches.is_participant(match_id, reporter_member_id)
        if reporter_side is None:
            raise PermissionDeniedError("Only match participants can report a result.")

        winning_side = reporter_side if reporter_won else _other_side(reporter_side)
        await self._matches.report(
            match, reported_by_member_id=reporter_member_id, winning_side=winning_side
        )
        return match

    async def confirming_side(self, match: Match) -> MatchSide | None:
        """Which side must confirm — the side that did *not* report."""
        if match.reported_by_member_id is None:
            return None
        reporter_side = await self._matches.is_participant(match.id, match.reported_by_member_id)
        return _other_side(reporter_side) if reporter_side is not None else None

    async def confirm_result(
        self, *, match_id: int, guild_id: int, confirmer_discord_id: int
    ) -> Match:
        match = await self._matches.get(match_id)
        if match is None:
            raise NotFoundError("That match no longer exists.")

        confirmer_member_id = await self._member_id(
            guild_id=guild_id, discord_id=confirmer_discord_id
        )
        confirmer_side = await self._matches.is_participant(match_id, confirmer_member_id)
        expected_side = await self.confirming_side(match)
        if confirmer_side is None or confirmer_side != expected_side:
            raise PermissionDeniedError("Only the other side can confirm this result.")

        await self._matches.confirm(match)
        return match

    async def dispute_result(
        self, *, match_id: int, guild_id: int, disputer_discord_id: int
    ) -> Match:
        match = await self._matches.get(match_id)
        if match is None:
            raise NotFoundError("That match no longer exists.")

        disputer_member_id = await self._member_id(
            guild_id=guild_id, discord_id=disputer_discord_id
        )
        disputer_side = await self._matches.is_participant(match_id, disputer_member_id)
        expected_side = await self.confirming_side(match)
        if disputer_side is None or disputer_side != expected_side:
            raise PermissionDeniedError("Only the other side can dispute this result.")

        await self._matches.dispute(match)
        return match

    async def resolve_result(
        self, *, match_id: int, guild_id: int, resolver_discord_id: int, winning_side: MatchSide
    ) -> Match:
        """Staff-only override — permission is enforced at the cog layer."""
        match = await self._matches.get(match_id)
        if match is None:
            raise NotFoundError("That match no longer exists.")
        resolver_member_id = await self._member_id(
            guild_id=guild_id, discord_id=resolver_discord_id
        )
        await self._matches.resolve(
            match, winning_side=winning_side, resolved_by_member_id=resolver_member_id
        )
        return match

    # --- History ------------------------------------------------------------

    async def get_match_history(
        self, *, guild_id: int, discord_id: int, limit: int = 10
    ) -> list[Match]:
        member_id = await self._member_id(guild_id=guild_id, discord_id=discord_id)
        return await self._matches.list_recent_for_member(member_id, limit=limit)
