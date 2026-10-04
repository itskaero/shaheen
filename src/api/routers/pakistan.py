"""GET /pakistan/leaderboard — the Pakistan board (docs/DECISIONS.md ADR-099).

Brawlhalla identity only, like every public endpoint (ADR-040): entries can
be players who were never Discord members, and nothing here names one who was.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_session, get_settings
from api.schemas import PakistanLeaderboardEntryResponse, RisingPlayerResponse
from core.config import Settings
from services.pakistan_board_service import MAX_PAKISTAN_BOARD, PakistanBoardService

router = APIRouter(prefix="/pakistan", tags=["pakistan"])


@router.get("/leaderboard", response_model=list[PakistanLeaderboardEntryResponse])
async def get_pakistan_leaderboard(
    limit: int = Query(default=25, ge=1, le=MAX_PAKISTAN_BOARD),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> list[PakistanLeaderboardEntryResponse]:
    rows = await PakistanBoardService(session).leaderboard(settings.guild_id, limit=limit)
    return [
        PakistanLeaderboardEntryResponse(
            brawlhalla_id=row.player.brawlhalla_player_id,
            player_name=row.player.player_name,
            region=row.snapshot.region or row.player.region,
            rating=row.snapshot.rating,
            peak_rating=row.snapshot.peak_rating,
            tier=row.snapshot.tier,
            is_clan_member=row.is_clan_member,
            is_claimed=row.is_claimed,
        )
        for row in rows
    ]


@router.get("/rising", response_model=list[RisingPlayerResponse])
async def get_pakistan_rising(
    days: int = Query(default=7, ge=1, le=30),
    limit: int = Query(default=10, ge=1, le=50),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> list[RisingPlayerResponse]:
    """Biggest rating gains on the Pakistan board over the last `days` (ADR-104)."""
    since = datetime.now(UTC) - timedelta(days=days)
    climbers = await PakistanBoardService(session).climbers(
        settings.guild_id, since=since, limit=limit
    )
    return [
        RisingPlayerResponse(
            brawlhalla_id=climber.player.brawlhalla_player_id,
            player_name=climber.player.player_name,
            rating=climber.rating,
            rating_gain=climber.rating_gain,
            is_claimed=climber.is_claimed,
        )
        for climber in climbers
    ]
