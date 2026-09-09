"""GET /tournaments and GET /tournaments/{id} — Phase 7's tournament
bracket viewer (docs/DECISIONS.md ADR-051)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_session, get_settings
from api.schemas import (
    BracketEntrantResponse,
    BracketMatchResponse,
    TournamentBracketResponse,
    TournamentSummaryResponse,
)
from core.config import Settings
from services.website_service import BracketEntrant, WebsiteService

router = APIRouter(prefix="/tournaments", tags=["tournaments"])


def _entrant_response(entrant: BracketEntrant | None) -> BracketEntrantResponse | None:
    if entrant is None:
        return None
    return BracketEntrantResponse(
        id=entrant.id, seed=entrant.seed, names=entrant.names, eliminated=entrant.eliminated
    )


@router.get("", response_model=list[TournamentSummaryResponse])
async def list_tournaments(
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> list[TournamentSummaryResponse]:
    tournaments = await WebsiteService(session).list_tournaments(settings.guild_id, limit=limit)
    return [
        TournamentSummaryResponse(
            id=t.id,
            name=t.name,
            kind=t.kind,
            status=t.status,
            started_at=t.started_at,
            completed_at=t.completed_at,
        )
        for t in tournaments
    ]


@router.get("/{tournament_id}", response_model=TournamentBracketResponse)
async def get_tournament_bracket(
    tournament_id: int, session: AsyncSession = Depends(get_session)
) -> TournamentBracketResponse:
    bracket = await WebsiteService(session).get_tournament_bracket(tournament_id)
    if bracket is None:
        raise HTTPException(status_code=404, detail="Tournament not found")

    return TournamentBracketResponse(
        tournament=TournamentSummaryResponse(
            id=bracket.tournament.id,
            name=bracket.tournament.name,
            kind=bracket.tournament.kind,
            status=bracket.tournament.status,
            started_at=bracket.tournament.started_at,
            completed_at=bracket.tournament.completed_at,
        ),
        entrants=[
            BracketEntrantResponse(id=e.id, seed=e.seed, names=e.names, eliminated=e.eliminated)
            for e in bracket.entrants
        ],
        matches=[
            BracketMatchResponse(
                round_number=m.round_number,
                slot_index=m.slot_index,
                entrant_a=_entrant_response(m.entrant_a),
                entrant_b=_entrant_response(m.entrant_b),
                winner_entrant_id=m.winner_entrant_id,
                status=m.status,
            )
            for m in bracket.matches
        ],
    )
