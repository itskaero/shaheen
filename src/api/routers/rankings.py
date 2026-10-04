"""GET /rankings/pakistan — the Rankings page's board (docs/DECISIONS.md ADR-105)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_session, get_settings
from api.schemas import PakistanSeasonResponse, RankingRowResponse, RankingsBoardResponse
from core.config import Settings
from services.rankings_service import RankingsService

router = APIRouter(prefix="/rankings", tags=["rankings"])


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
        rows=[
            RankingRowResponse(
                brawlhalla_id=row.player.brawlhalla_player_id,
                player_name=row.player.player_name,
                country=row.country,
                team=row.team,
                is_claimed=row.is_claimed,
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
            )
            for row in board.rows
        ],
    )
