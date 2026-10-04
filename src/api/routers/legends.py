"""GET /legends/meta — Legend popularity across the network (ADR-104).

Lifetime games and wins from each tracked player's latest per-Legend
snapshot. No Discord identity, like every public endpoint (ADR-040).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_session, get_settings
from api.schemas import LegendMetaResponse
from core.config import Settings
from services.network_service import NetworkService

router = APIRouter(prefix="/legends", tags=["legends"])


@router.get("/meta", response_model=list[LegendMetaResponse])
async def get_legend_meta(
    limit: int = Query(default=10, ge=1, le=60),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> list[LegendMetaResponse]:
    entries = await NetworkService(session).legend_meta(settings.guild_id, limit=limit)
    return [
        LegendMetaResponse(
            legend_name_key=entry.legend_name_key,
            player_count=entry.player_count,
            total_games=entry.total_games,
            win_rate=round(entry.win_rate, 1),
        )
        for entry in entries
    ]
