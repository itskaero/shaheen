"""GET /staff — the server's Founders and Admins (docs/DECISIONS.md ADR-135).

Name, role and avatar only. The name is the member's linked Brawlhalla name,
or their server display name if they haven't linked. No Discord id, username
or CDN URL ever appears: the avatar is the image itself, as a data URI.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_session, get_settings
from api.schemas import StaffMemberResponse
from core.config import Settings
from services.staff_service import StaffService

router = APIRouter(prefix="/staff", tags=["staff"])


@router.get("", response_model=list[StaffMemberResponse])
async def list_staff(
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> list[StaffMemberResponse]:
    entries = await StaffService(session).directory(settings.guild_id)
    return [
        StaffMemberResponse(name=e.name, role=e.role, avatar=e.avatar_data_uri, slug=e.player_slug)
        for e in entries
    ]
