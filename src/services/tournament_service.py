"""Tournament lifecycle — usable without Discord (docs/DECISIONS.md ADR-035).

Owns the only writes to Tournament/TournamentEntrant/TournamentMatch, and
is the sole caller of the pure services/bracket.py generator. A bracket
slot becomes a normal Match (via MatchRepository) once both its entrants
are known; winning that Match through /report + confirm (or a staff
/tournament resolve) advances the bracket through `advance_from_match`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import NotFoundError, ShaheenError
from database.models.match import MatchKind, MatchSide
from database.models.tournament import (
    Tournament,
    TournamentEntrant,
    TournamentMatch,
    TournamentMatchStatus,
    TournamentStatus,
)
from database.repositories.discord_user_repository import DiscordUserRepository
from database.repositories.match_repository import MatchRepository
from database.repositories.shaheen_member_repository import ShaheenMemberRepository
from database.repositories.tournament_repository import (
    TournamentEntrantRepository,
    TournamentMatchRepository,
    TournamentRepository,
)
from services.bracket import generate_bracket, next_slot

_ENTRANT_SIZE: dict[MatchKind, int] = {MatchKind.ONE_V_ONE: 1, MatchKind.TWO_V_TWO: 2}


@dataclass
class AdvanceResult:
    bracket_match: TournamentMatch
    tournament_completed: bool
    next_bracket_match: TournamentMatch | None = None  # became AWAITING_REPORT as a result


class TournamentService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._discord_users = DiscordUserRepository(session)
        self._members = ShaheenMemberRepository(session)
        self._tournaments = TournamentRepository(session)
        self._entrants = TournamentEntrantRepository(session)
        self._bracket_matches = TournamentMatchRepository(session)
        self._matches = MatchRepository(session)

    async def _member_id(
        self, *, guild_id: int, discord_id: int, joined_at: datetime | None = None
    ) -> int:
        discord_user = await self._discord_users.get_or_create(discord_id)
        member = await self._members.get_or_create(
            discord_user_id=discord_user.id, guild_id=guild_id, joined_at=joined_at
        )
        return member.id

    # --- Setup ----------------------------------------------------------

    async def create_tournament(
        self,
        *,
        guild_id: int,
        name: str,
        kind: MatchKind,
        creator_discord_id: int,
        creator_joined_at: datetime | None,
    ) -> Tournament:
        creator_id = await self._member_id(
            guild_id=guild_id, discord_id=creator_discord_id, joined_at=creator_joined_at
        )
        return await self._tournaments.create(
            guild_id=guild_id, name=name, kind=kind, created_by_member_id=creator_id
        )

    async def get_tournament(self, tournament_id: int) -> Tournament | None:
        return await self._tournaments.get(tournament_id)

    async def register(
        self,
        *,
        tournament_id: int,
        guild_id: int,
        discord_ids: list[tuple[int, datetime | None]],
    ) -> TournamentEntrant:
        tournament = await self._tournaments.get(tournament_id)
        if tournament is None:
            raise NotFoundError("That tournament no longer exists.")
        if tournament.status != TournamentStatus.REGISTRATION:
            raise ShaheenError("Registration is closed for this tournament.")

        expected = _ENTRANT_SIZE[tournament.kind]
        if len(discord_ids) != expected:
            raise ShaheenError(
                f"A {tournament.kind.value} entrant needs exactly {expected} player(s)."
            )

        member_ids = []
        for discord_id, joined_at in discord_ids:
            member_id = await self._member_id(
                guild_id=guild_id, discord_id=discord_id, joined_at=joined_at
            )
            if await self._entrants.is_registered(tournament_id, member_id):
                raise ShaheenError("One of these players is already registered.")
            member_ids.append(member_id)

        return await self._entrants.register(
            tournament_id=tournament_id, shaheen_member_ids=member_ids
        )

    async def start_tournament(self, tournament_id: int) -> Tournament:
        tournament = await self._tournaments.get(tournament_id)
        if tournament is None:
            raise NotFoundError("That tournament no longer exists.")
        if tournament.status != TournamentStatus.REGISTRATION:
            raise ShaheenError("This tournament has already started.")

        entrants = await self._entrants.list_for_tournament(tournament_id)
        if len(entrants) < 2:
            raise ShaheenError("A tournament needs at least 2 entrants to start.")

        # Registration order (ascending id) is seed order — no skill-based
        # seeding exists yet (docs/DECISIONS.md ADR-035).
        entrants.sort(key=lambda e: e.id)
        plan = generate_bracket(len(entrants))
        entrant_by_seed = dict(enumerate(entrants, start=1))
        for seed, entrant in entrant_by_seed.items():
            await self._entrants.set_seed(entrant, seed)

        # Skeleton for every later round, so the bracket tree fully exists
        # even before earlier rounds are decided.
        slots_in_round = plan.bracket_size // 2
        for round_number in range(2, plan.total_rounds + 1):
            slots_in_round //= 2
            for slot_index in range(slots_in_round):
                await self._bracket_matches.create(
                    tournament_id=tournament_id,
                    round_number=round_number,
                    slot_index=slot_index,
                    entrant_a_id=None,
                    entrant_b_id=None,
                    status=TournamentMatchStatus.PENDING,
                )

        for slot in plan.round_one:
            entrant_a = entrant_by_seed.get(slot.entrant_a_seed) if slot.entrant_a_seed else None
            entrant_b = entrant_by_seed.get(slot.entrant_b_seed) if slot.entrant_b_seed else None
            status = (
                TournamentMatchStatus.BYE if slot.bye_winner_seed else TournamentMatchStatus.READY
            )
            bracket_match = await self._bracket_matches.create(
                tournament_id=tournament_id,
                round_number=1,
                slot_index=slot.slot_index,
                entrant_a_id=entrant_a.id if entrant_a else None,
                entrant_b_id=entrant_b.id if entrant_b else None,
                status=status,
            )

            if slot.bye_winner_seed:
                winner = entrant_by_seed[slot.bye_winner_seed]
                await self._bracket_matches.record_bye(bracket_match, winner_entrant_id=winner.id)
                if plan.total_rounds > 1:
                    await self._place_winner(tournament, 1, slot.slot_index, winner.id)
            else:
                await self._start_bracket_match(tournament, bracket_match)

        await self._tournaments.start(tournament)
        return tournament

    # --- Advancement ------------------------------------------------------

    async def get_bracket_match_for(self, match_id: int) -> TournamentMatch | None:
        return await self._bracket_matches.get_by_match_id(match_id)

    async def resolve_bracket_match(
        self,
        *,
        tournament_match_id: int,
        guild_id: int,
        resolver_discord_id: int,
        winning_side: MatchSide,
    ) -> AdvanceResult:
        """Staff override — permission is enforced at the cog layer."""
        bracket_match = await self._bracket_matches.get(tournament_match_id)
        if bracket_match is None:
            raise NotFoundError("That bracket match doesn't exist.")
        if bracket_match.match_id is None:
            raise ShaheenError("This bracket slot doesn't have both entrants yet.")

        match = await self._matches.get(bracket_match.match_id)
        if match is None:
            raise NotFoundError("The underlying match record is missing.")

        resolver_member_id = await self._member_id(
            guild_id=guild_id, discord_id=resolver_discord_id
        )
        await self._matches.resolve(
            match, winning_side=winning_side, resolved_by_member_id=resolver_member_id
        )
        return await self.advance_from_match(bracket_match, winning_side=winning_side)

    async def advance_from_match(
        self, bracket_match: TournamentMatch, *, winning_side: MatchSide
    ) -> AdvanceResult:
        tournament = await self._tournaments.get(bracket_match.tournament_id)
        if tournament is None:
            raise NotFoundError("That tournament no longer exists.")

        winner_id = (
            bracket_match.entrant_a_id
            if winning_side is MatchSide.A
            else bracket_match.entrant_b_id
        )
        loser_id = (
            bracket_match.entrant_b_id
            if winning_side is MatchSide.A
            else bracket_match.entrant_a_id
        )
        if winner_id is None or loser_id is None:
            raise ShaheenError("This bracket match doesn't have two entrants yet.")

        await self._bracket_matches.complete(bracket_match, winner_entrant_id=winner_id)
        loser = await self._entrant(loser_id)
        if loser is not None:
            await self._entrants.eliminate(loser)

        max_round = await self._bracket_matches.max_round(tournament.id)
        if bracket_match.round_number >= max_round:
            await self._tournaments.complete(tournament)
            return AdvanceResult(bracket_match=bracket_match, tournament_completed=True)

        next_bracket_match = await self._place_winner(
            tournament, bracket_match.round_number, bracket_match.slot_index, winner_id
        )
        return AdvanceResult(
            bracket_match=bracket_match,
            tournament_completed=False,
            next_bracket_match=next_bracket_match,
        )

    async def _place_winner(
        self, tournament: Tournament, round_number: int, slot_index: int, winner_entrant_id: int
    ) -> TournamentMatch | None:
        """Fills a winner into the next round's slot; starts that Match if it's now full."""
        next_round, next_index, side = next_slot(round_number, slot_index)
        target = await self._bracket_matches.get_by_slot(tournament.id, next_round, next_index)
        if target is None:
            return None  # was the final; nothing further to fill

        if side == "a":
            target.entrant_a_id = winner_entrant_id
        else:
            target.entrant_b_id = winner_entrant_id
        await self._session.flush()

        if target.entrant_a_id is not None and target.entrant_b_id is not None:
            target.status = TournamentMatchStatus.READY
            await self._session.flush()
            await self._start_bracket_match(tournament, target)
            return target
        return None

    async def _start_bracket_match(
        self, tournament: Tournament, bracket_match: TournamentMatch
    ) -> None:
        """Creates the underlying reportable Match for a bracket slot with both entrants known."""
        assert bracket_match.entrant_a_id is not None
        assert bracket_match.entrant_b_id is not None
        side_a_members = await self._entrants.members_of(bracket_match.entrant_a_id)
        side_b_members = await self._entrants.members_of(bracket_match.entrant_b_id)

        match = await self._matches.create(
            guild_id=tournament.guild_id,
            kind=tournament.kind,
            participants=[(m, MatchSide.A) for m in side_a_members]
            + [(m, MatchSide.B) for m in side_b_members],
        )
        await self._bracket_matches.attach_match(bracket_match, match_id=match.id)

    async def _entrant(self, entrant_id: int) -> TournamentEntrant | None:
        return await self._session.get(TournamentEntrant, entrant_id)
