"""GET /featured — the staff-picked Featured Player (docs/DECISIONS.md
ADR-111). 404 when nobody is featured; the home page then falls back to the
Pakistan #1 and says so.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_session, get_settings
from api.schemas import FeaturedPlayerResponse
from core.config import Settings
from services.featured_service import FeaturedService

router = APIRouter(prefix="/featured", tags=["featured"])


@router.get("", response_model=FeaturedPlayerResponse)
async def get_featured(
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> FeaturedPlayerResponse:
    featured = await FeaturedService(session).current(settings.guild_id)
    if featured is None:
        raise HTTPException(status_code=404, detail="No featured player.")
    latest = featured.latest
    return FeaturedPlayerResponse(
        brawlhalla_id=featured.player.brawlhalla_player_id,
        player_name=featured.player.player_name,
        note=featured.note,
        featured_at=featured.featured_at,
        rating=latest.rating if latest else None,
        peak_rating=latest.peak_rating if latest else None,
        tier=latest.tier if latest else None,
    )
