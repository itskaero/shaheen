"""GET /roster — the full clan roster, unlike /leaderboard's top N
(docs/DECISIONS.md ADR-071).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_session, get_settings
from api.schemas import RosterEntryResponse
from core.config import Settings
from services.website_service import WebsiteService

router = APIRouter(prefix="/roster", tags=["roster"])


@router.get("", response_model=list[RosterEntryResponse])
async def get_roster(
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> list[RosterEntryResponse]:
    entries = await WebsiteService(session).get_roster(settings.guild_id)
    return [
        RosterEntryResponse(
            brawlhalla_id=entry.player.brawlhalla_player_id,
            player_name=entry.player.player_name,
            region=entry.player.region,
            rating=entry.snapshot.rating if entry.snapshot else None,
            peak_rating=entry.snapshot.peak_rating if entry.snapshot else None,
            tier=entry.snapshot.tier if entry.snapshot else None,
            member_since=entry.joined_at,
        )
        for entry in entries
    ]
