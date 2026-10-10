"""GET /coaches — the coach directory (docs/DECISIONS.md ADR-126).

Only coaches with a linked Brawlhalla account are listed, named by that
account (ADR-040); a coach's Discord identity never leaves the bot. Members
book a coach in Discord with /coach request.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_session, get_settings
from api.schemas import CoachResponse
from core.config import Settings
from services.coaching_service import CoachingService
from services.players_service import player_slug

router = APIRouter(prefix="/coaches", tags=["coaches"])


@router.get("", response_model=list[CoachResponse])
async def list_coaches(
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> list[CoachResponse]:
    entries = await CoachingService(session).directory(settings.guild_id)
    return [
        CoachResponse(
            brawlhalla_id=entry.player.brawlhalla_player_id,
            player_name=entry.player.player_name,
            slug=player_slug(entry.player.player_name, entry.player.brawlhalla_player_id),
            specialty=entry.coach.specialty,
            legends=entry.legend_keys,
            availability=entry.coach.availability,
            bio=entry.coach.bio,
            accepting=entry.coach.accepting,
            sessions=entry.sessions,
            rating=entry.snapshot.rating if entry.snapshot else None,
            tier=entry.snapshot.tier if entry.snapshot else None,
            team=entry.team.name if entry.team else None,
            team_slug=entry.team.slug if entry.team else None,
            team_tag=entry.team.tag if entry.team else None,
        )
        for entry in entries
        if entry.player is not None
    ]
