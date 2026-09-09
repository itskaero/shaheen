"""Persistence for Tournament, TournamentEntrant(Member), TournamentMatch."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.match import MatchKind
from database.models.tournament import (
    Tournament,
    TournamentEntrant,
    TournamentEntrantMember,
    TournamentMatch,
    TournamentMatchStatus,
    TournamentStatus,
)


class TournamentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self, *, guild_id: int, name: str, kind: MatchKind, created_by_member_id: int
    ) -> Tournament:
        tournament = Tournament(
            guild_id=guild_id, name=name, kind=kind, created_by_member_id=created_by_member_id
        )
        self._session.add(tournament)
        await self._session.flush()
        return tournament

    async def get(self, tournament_id: int) -> Tournament | None:
        return await self._session.get(Tournament, tournament_id)

    async def start(self, tournament: Tournament) -> None:
        tournament.status = TournamentStatus.IN_PROGRESS
        tournament.started_at = datetime.now(UTC)
        await self._session.flush()

    async def complete(self, tournament: Tournament) -> None:
        tournament.status = TournamentStatus.COMPLETED
        tournament.completed_at = datetime.now(UTC)
        await self._session.flush()

    async def cancel(self, tournament: Tournament) -> None:
        tournament.status = TournamentStatus.CANCELLED
        await self._session.flush()


class TournamentEntrantRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_tournament(self, tournament_id: int) -> list[TournamentEntrant]:
        stmt = select(TournamentEntrant).where(TournamentEntrant.tournament_id == tournament_id)
        return list((await self._session.execute(stmt)).scalars().all())

    async def register(
        self, *, tournament_id: int, shaheen_member_ids: list[int]
    ) -> TournamentEntrant:
        entrant = TournamentEntrant(tournament_id=tournament_id)
        self._session.add(entrant)
        await self._session.flush()
        for member_id in shaheen_member_ids:
            self._session.add(
                TournamentEntrantMember(
                    tournament_entrant_id=entrant.id, shaheen_member_id=member_id
                )
            )
        await self._session.flush()
        return entrant

    async def is_registered(self, tournament_id: int, shaheen_member_id: int) -> bool:
        stmt = (
            select(TournamentEntrantMember.id)
            .join(
                TournamentEntrant,
                TournamentEntrant.id == TournamentEntrantMember.tournament_entrant_id,
            )
            .where(
                TournamentEntrant.tournament_id == tournament_id,
                TournamentEntrantMember.shaheen_member_id == shaheen_member_id,
            )
        )
        return (await self._session.execute(stmt)).scalar_one_or_none() is not None

    async def members_of(self, tournament_entrant_id: int) -> list[int]:
        stmt = select(TournamentEntrantMember.shaheen_member_id).where(
            TournamentEntrantMember.tournament_entrant_id == tournament_entrant_id
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def set_seed(self, entrant: TournamentEntrant, seed: int) -> None:
        entrant.seed = seed
        await self._session.flush()

    async def eliminate(self, entrant: TournamentEntrant) -> None:
        entrant.eliminated = True
        await self._session.flush()


class TournamentMatchRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        tournament_id: int,
        round_number: int,
        slot_index: int,
        entrant_a_id: int | None,
        entrant_b_id: int | None,
        status: TournamentMatchStatus,
    ) -> TournamentMatch:
        bracket_match = TournamentMatch(
            tournament_id=tournament_id,
            round_number=round_number,
            slot_index=slot_index,
            entrant_a_id=entrant_a_id,
            entrant_b_id=entrant_b_id,
            status=status,
        )
        self._session.add(bracket_match)
        await self._session.flush()
        return bracket_match

    async def get(self, tournament_match_id: int) -> TournamentMatch | None:
        return await self._session.get(TournamentMatch, tournament_match_id)

    async def get_by_slot(
        self, tournament_id: int, round_number: int, slot_index: int
    ) -> TournamentMatch | None:
        stmt = select(TournamentMatch).where(
            TournamentMatch.tournament_id == tournament_id,
            TournamentMatch.round_number == round_number,
            TournamentMatch.slot_index == slot_index,
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get_by_match_id(self, match_id: int) -> TournamentMatch | None:
        stmt = select(TournamentMatch).where(TournamentMatch.match_id == match_id)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_for_round(self, tournament_id: int, round_number: int) -> list[TournamentMatch]:
        stmt = (
            select(TournamentMatch)
            .where(
                TournamentMatch.tournament_id == tournament_id,
                TournamentMatch.round_number == round_number,
            )
            .order_by(TournamentMatch.slot_index)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def list_all(self, tournament_id: int) -> list[TournamentMatch]:
        stmt = (
            select(TournamentMatch)
            .where(TournamentMatch.tournament_id == tournament_id)
            .order_by(TournamentMatch.round_number, TournamentMatch.slot_index)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def max_round(self, tournament_id: int) -> int:
        rows = await self.list_all(tournament_id)
        return max((row.round_number for row in rows), default=0)

    async def attach_match(self, bracket_match: TournamentMatch, *, match_id: int) -> None:
        bracket_match.match_id = match_id
        bracket_match.status = TournamentMatchStatus.AWAITING_REPORT
        await self._session.flush()

    async def complete(self, bracket_match: TournamentMatch, *, winner_entrant_id: int) -> None:
        bracket_match.winner_entrant_id = winner_entrant_id
        bracket_match.status = TournamentMatchStatus.COMPLETED
        await self._session.flush()

    async def record_bye(self, bracket_match: TournamentMatch, *, winner_entrant_id: int) -> None:
        """Like `complete`, but keeps status=BYE — the winner advanced without playing."""
        bracket_match.winner_entrant_id = winner_entrant_id
        await self._session.flush()
