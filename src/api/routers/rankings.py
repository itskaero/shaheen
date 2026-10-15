"""GET /rankings/pakistan — the Rankings page's board (docs/DECISIONS.md ADR-105) —
and GET /rankings/cities, City Wars (ADR-128)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_session, get_settings
from api.schemas import (
    CityBoardResponse,
    CityStandingResponse,
    PakistanSeasonResponse,
    RankingRowResponse,
    RankingsBoardResponse,
)
from core.config import Settings
from services.cities import CITY_TOP_N, city_label
from services.rankings_service import RankingRow, RankingsService

router = APIRouter(prefix="/rankings", tags=["rankings"])


def ranking_row_response(row: RankingRow) -> RankingRowResponse:
    """Shared with the Seasons page (ADR-113)."""
    return RankingRowResponse(
        brawlhalla_id=row.player.brawlhalla_player_id,
        player_name=row.player.player_name,
        country=row.country,
        team=row.team,
        team_slug=row.team_slug,
        team_tag=row.team_tag,
        is_claimed=row.is_claimed,
        is_verified=row.is_verified,
        region=row.snapshot.region or row.player.region,
        rating=row.snapshot.rating,
        peak_rating=row.snapshot.peak_rating,
        tier=row.snapshot.tier,
        wins=row.snapshot.wins,
        games=row.snapshot.games,
        global_rank=row.snapshot.global_rank,
        region_rank=row.snapshot.region_rank,
        rating_2v2=row.snapshot.rating_2v2,
        peak_rating_2v2=row.snapshot.peak_rating_2v2,
        tier_2v2=row.snapshot.tier_2v2,
        partner_2v2=row.snapshot.partner_2v2,
        trend=row.trend,
        main_legend=row.main_legend,
        city=row.city,
        city_label=city_label(row.city),
    )


@router.get("/pakistan", response_model=RankingsBoardResponse)
async def get_pakistan_rankings(
    season: int | None = Query(default=None, ge=1, le=1000),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> RankingsBoardResponse:
    board = await RankingsService(session).pakistan(settings.guild_id, season=season)
    return RankingsBoardResponse(
        season=board.season,
        pakistan_season=PakistanSeasonResponse.for_brawlhalla_season(board.season),
        seasons=board.seasons,
        rows=[ranking_row_response(row) for row in board.rows],
    )


@router.get("/cities", response_model=CityBoardResponse)
async def get_city_board(
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> CityBoardResponse:
    """City Wars (ADR-128)."""
    season, standings = await RankingsService(session).cities(settings.guild_id)
    return CityBoardResponse(
        season=season,
        top_n=CITY_TOP_N,
        cities=[
            CityStandingResponse(
                key=c.key,
                label=c.label,
                rating=c.rating,
                players=c.players,
                top=[name for name, _rating in c.top],
            )
            for c in standings
        ],
    )
