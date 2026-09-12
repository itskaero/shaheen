"""GET /achievements — clan-wide achievement gallery, including
zero-holder achievements (docs/DECISIONS.md ADR-071).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_session, get_settings
from api.schemas import AchievementGalleryEntryResponse
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
            holder_count=entry.holder_count,
            total_members=entry.total_members,
            completion_pct=entry.completion_pct,
        )
        for entry in entries
    ]
