"""GET /community/activity — chat-XP leaderboard (docs/DECISIONS.md ADR-065).

GET /community/matches — recent confirmed clan matches (ADR-088). The
competition subsystem has run since Phase 4 with no public surface.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_session, get_settings
from api.schemas import ClanMatchEntryResponse, CommunityActivityEntryResponse
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


@router.get("/matches", response_model=list[ClanMatchEntryResponse])
async def get_clan_matches(
    limit: int = Query(default=10, ge=1, le=50),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> list[ClanMatchEntryResponse]:
    entries = await WebsiteService(session).get_clan_matches(settings.guild_id, limit=limit)
    return [
        ClanMatchEntryResponse(
            kind=entry.kind,
            winners=entry.winners,
            losers=entry.losers,
            confirmed_at=entry.confirmed_at,
        )
        for entry in entries
    ]
