"""GET /community/activity — chat-XP leaderboard (docs/DECISIONS.md ADR-065)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_session, get_settings
from api.schemas import CommunityActivityEntryResponse
from core.config import Settings
from services.website_service import WebsiteService

router = APIRouter(prefix="/community", tags=["community"])


@router.get("/activity", response_model=list[CommunityActivityEntryResponse])
async def get_community_activity(
    limit: int = Query(default=10, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> list[CommunityActivityEntryResponse]:
    entries = await WebsiteService(session).get_community_activity(settings.guild_id, limit=limit)
    return [
        CommunityActivityEntryResponse(
            player_name=entry.player_name,
            level=entry.level,
            rank_title=entry.rank_title,
            xp=entry.xp,
        )
        for entry in entries
    ]
