"""GET /players/{brawlhalla_id}[/history|/legends|/matches] — docs/ROADMAP.md
Phase 5's "public player profiles", extended in Phase 7 with legend
mastery and match history (docs/DECISIONS.md ADR-051)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_session
from api.schemas import (
    AchievementResponse,
    LegendMasteryResponse,
    MatchResultResponse,
    PlayerProfileResponse,
    RankingHistoryEntryResponse,
)
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
        global_rank=profile.global_rank,
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


@router.get("/{brawlhalla_id}/legends", response_model=list[LegendMasteryResponse])
async def get_player_legends(
    brawlhalla_id: int,
    limit: int = Query(default=6, ge=1, le=20),
    session: AsyncSession = Depends(get_session),
) -> list[LegendMasteryResponse]:
    legends = await WebsiteService(session).get_player_legends(brawlhalla_id, limit=limit)
    if legends is None:
        raise HTTPException(status_code=404, detail="Player not found")
    return [
        LegendMasteryResponse(
            legend_name_key=legend.legend_name_key,
            games=legend.games,
            wins=legend.wins,
            kos=legend.kos,
            damagedealt=legend.damagedealt,
            falls=legend.falls,
        )
        for legend in legends
    ]


@router.get("/{brawlhalla_id}/matches", response_model=list[MatchResultResponse])
async def get_player_matches(
    brawlhalla_id: int,
    limit: int = Query(default=10, ge=1, le=50),
    session: AsyncSession = Depends(get_session),
) -> list[MatchResultResponse]:
    matches = await WebsiteService(session).get_player_matches(brawlhalla_id, limit=limit)
    if matches is None:
        raise HTTPException(status_code=404, detail="Player not found")
    return [
        MatchResultResponse(
            kind=match.kind,
            opponents=match.opponents,
            won=match.won,
            confirmed_at=match.confirmed_at,
        )
        for match in matches
    ]
