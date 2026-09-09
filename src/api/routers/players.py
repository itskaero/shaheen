"""GET /players/{brawlhalla_id}[/history] — docs/ROADMAP.md Phase 5's
"public player profiles"."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_session
from api.schemas import AchievementResponse, PlayerProfileResponse, RankingHistoryEntryResponse
from services.website_service import WebsiteService

router = APIRouter(prefix="/players", tags=["players"])


@router.get("/{brawlhalla_id}", response_model=PlayerProfileResponse)
async def get_player_profile(
    brawlhalla_id: int, session: AsyncSession = Depends(get_session)
) -> PlayerProfileResponse:
    profile = await WebsiteService(session).get_player_profile(brawlhalla_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Player not found")

    ranking = profile.latest_ranking
    return PlayerProfileResponse(
        brawlhalla_id=profile.player.brawlhalla_player_id,
        player_name=profile.player.player_name,
        region=profile.player.region,
        rating=ranking.rating if ranking else None,
        peak_rating=ranking.peak_rating if ranking else None,
        tier=ranking.tier if ranking else None,
        achievements=[
            AchievementResponse(
                key=achievement.key,
                name=achievement.name,
                description=achievement.description,
                awarded_at=awarded_at,
            )
            for achievement, awarded_at in profile.achievements
        ],
    )


@router.get("/{brawlhalla_id}/history", response_model=list[RankingHistoryEntryResponse])
async def get_player_history(
    brawlhalla_id: int,
    limit: int = Query(default=10, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> list[RankingHistoryEntryResponse]:
    history = await WebsiteService(session).get_player_history(brawlhalla_id, limit=limit)
    if history is None:
        raise HTTPException(status_code=404, detail="Player not found")
    return [
        RankingHistoryEntryResponse(
            captured_at=snapshot.captured_at,
            rating=snapshot.rating,
            peak_rating=snapshot.peak_rating,
            tier=snapshot.tier,
        )
        for snapshot in history
    ]
