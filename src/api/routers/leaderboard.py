"""GET /leaderboard — docs/ROADMAP.md Phase 5's "leaderboard"."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_session, get_settings
from api.schemas import LeaderboardEntryResponse
from core.config import Settings
from services.website_service import WebsiteService

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])


@router.get("", response_model=list[LeaderboardEntryResponse])
async def get_leaderboard(
    limit: int = Query(default=10, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> list[LeaderboardEntryResponse]:
    entries = await WebsiteService(session).get_leaderboard(settings.guild_id, limit=limit)
    return [
        LeaderboardEntryResponse(
            brawlhalla_id=entry.player.brawlhalla_player_id,
            player_name=entry.player.player_name,
            region=entry.player.region,
            rating=entry.snapshot.rating,
            peak_rating=entry.snapshot.peak_rating,
            tier=entry.snapshot.tier,
        )
        for entry in entries
    ]
