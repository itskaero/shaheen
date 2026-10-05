"""GET /seasons, /seasons/current, /seasons/{brawlhalla_season} — the
Seasons page (docs/DECISIONS.md ADR-113). Brawlhalla identity only (ADR-040).
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_session, get_settings
from api.routers.rankings import ranking_row_response
from api.schemas import (
    PakistanSeasonResponse,
    SeasonCardResponse,
    SeasonDetailResponse,
    SeasonLegendResponse,
    SeasonRiserResponse,
    TournamentSummaryResponse,
)
from core.config import Settings
from services.seasons import ANCHOR_BRAWLHALLA_SEASON, PakistanSeason, brawlhalla_season_at
from services.seasons_service import SeasonsService

router = APIRouter(prefix="/seasons", tags=["seasons"])


def _season(season: PakistanSeason) -> PakistanSeasonResponse:
    response = PakistanSeasonResponse.for_brawlhalla_season(season.brawlhalla_season)
    assert response is not None  # every PakistanSeason maps back to itself
    return response


@router.get("", response_model=list[SeasonCardResponse])
async def list_seasons(
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> list[SeasonCardResponse]:
    cards = await SeasonsService(session).overview(settings.guild_id)
    return [
        SeasonCardResponse(
            season=_season(card.season),
            status=card.status,
            has_data=card.has_data,
            champion=card.champion,
        )
        for card in cards
    ]


async def _detail(
    session: AsyncSession, settings: Settings, brawlhalla_season: int
) -> SeasonDetailResponse:
    detail = await SeasonsService(session).detail(settings.guild_id, brawlhalla_season)
    if detail is None:
        raise HTTPException(status_code=404, detail="Pakistan seasons start at Brawlhalla S42.")
    rising = detail.rising
    legend = detail.legend
    return SeasonDetailResponse(
        season=_season(detail.card.season),
        status=detail.card.status,
        has_data=detail.card.has_data,
        top=[ranking_row_response(row) for row in detail.top],
        rising=SeasonRiserResponse(
            brawlhalla_id=rising.player.brawlhalla_player_id,
            player_name=rising.player.player_name,
            rating_gain=rising.rating_gain,
            rating=rising.rating,
        )
        if rising
        else None,
        legend=SeasonLegendResponse(
            legend_name_key=legend.legend_name_key,
            games=legend.games,
            win_rate=round(legend.win_rate, 1),
            players=legend.players,
        )
        if legend
        else None,
        tournaments=[
            TournamentSummaryResponse(
                id=t.id,
                name=t.name,
                kind=t.kind.value,
                status=t.status.value,
                started_at=t.started_at,
                completed_at=t.completed_at,
            )
            for t in detail.tournaments
        ],
    )


@router.get("/current", response_model=SeasonDetailResponse)
async def get_current_season(
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> SeasonDetailResponse:
    current = brawlhalla_season_at(datetime.now(UTC), override=settings.brawlhalla_season)
    return await _detail(session, settings, current)


@router.get("/{brawlhalla_season}", response_model=SeasonDetailResponse)
async def get_season(
    brawlhalla_season: int = Path(ge=ANCHOR_BRAWLHALLA_SEASON, le=1000),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> SeasonDetailResponse:
    return await _detail(session, settings, brawlhalla_season)
