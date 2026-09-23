"""GET /achievements — clan-wide achievement gallery, including
zero-holder achievements (docs/DECISIONS.md ADR-071).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_session, get_settings
from api.schemas import AchievementGalleryEntryResponse, AchievementHolderResponse
from core.config import Settings
from services.website_service import WebsiteService

router = APIRouter(prefix="/achievements", tags=["achievements"])


@router.get("", response_model=list[AchievementGalleryEntryResponse])
async def get_achievement_gallery(
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> list[AchievementGalleryEntryResponse]:
    entries = await WebsiteService(session).get_achievement_gallery(settings.guild_id)
    return [
        AchievementGalleryEntryResponse(
            key=entry.achievement.key,
            name=entry.achievement.name,
            description=entry.achievement.description,
            category=entry.achievement.category,
            holder_count=entry.holder_count,
            total_members=entry.total_members,
            completion_pct=entry.completion_pct,
            rarity=entry.rarity,
            holders=[
                AchievementHolderResponse(
                    brawlhalla_id=holder.player.brawlhalla_player_id,
                    player_name=holder.player.player_name,
                    earned_at=holder.earned_at,
                )
                for holder in entry.holders
            ],
        )
        for entry in entries
    ]
