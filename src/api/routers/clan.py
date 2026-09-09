"""GET /clan — docs/ROADMAP.md Phase 5's "clan page"."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_session, get_settings
from api.schemas import ClanInfoResponse
from core.config import Settings
from services.website_service import WebsiteService

router = APIRouter(prefix="/clan", tags=["clan"])


@router.get("", response_model=ClanInfoResponse)
async def get_clan(
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> ClanInfoResponse:
    info = await WebsiteService(session).get_clan_info(settings.guild_id)
    return ClanInfoResponse(
        name=info.name, motto=info.motto, tagline=info.tagline, member_count=info.member_count
    )
