"""GET /teams and GET /teams/{slug} — the Teams pages (docs/DECISIONS.md
ADR-114). Brawlhalla identity only (ADR-040): a captain is a player, never a
Discord account.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_session, get_settings
from api.schemas import (
    PakistanSeasonResponse,
    TeamAchievementResponse,
    TeamDetailResponse,
    TeamPlayerResponse,
    TeamSeasonResponse,
    TeamSummaryResponse,
)
from core.config import Settings
from services.players_service import player_slug
from services.team_service import RosterEntry, TeamService, TeamSummary

router = APIRouter(prefix="/teams", tags=["teams"])

_ACHIEVEMENTS_SHOWN = 12


def _player(entry: RosterEntry) -> TeamPlayerResponse:
    snap = entry.snapshot
    return TeamPlayerResponse(
        brawlhalla_id=entry.player.brawlhalla_player_id,
        player_name=entry.player.player_name,
        slug=player_slug(entry.player.player_name, entry.player.brawlhalla_player_id),
        role=entry.member.role,
        rating=snap.rating if snap else None,
        peak_rating=snap.peak_rating if snap else None,
        tier=snap.tier if snap else None,
        main_legend=entry.main_legend,
    )


def _summary_fields(summary: TeamSummary) -> dict[str, object]:
    team = summary.team
    return {
        "slug": team.slug,
        "name": team.name,
        "tag": team.tag,
        "country": team.country,
        "logo": team.logo,
        "description": team.description,
        "is_founding": team.is_founding,
        "members": summary.members,
        "rating": summary.rating,
        "best": _player(summary.best) if summary.best else None,
    }


@router.get("", response_model=list[TeamSummaryResponse])
async def list_teams(
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> list[TeamSummaryResponse]:
    summaries = await TeamService(session).overview(settings.guild_id)
    return [TeamSummaryResponse.model_validate(_summary_fields(s)) for s in summaries]


@router.get("/{slug}", response_model=TeamDetailResponse)
async def get_team(
    slug: str,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> TeamDetailResponse:
    if len(slug) > 48:
        raise HTTPException(status_code=404, detail="No such team.")
    detail = await TeamService(session).detail(settings.guild_id, slug)
    if detail is None:
        raise HTTPException(status_code=404, detail="No such team.")
    return TeamDetailResponse.model_validate(
        {
            **_summary_fields(detail.summary),
            "roster": [_player(e) for e in detail.roster],
            "achievements": [
                TeamAchievementResponse(
                    player_name=name, key=achievement.key, name=achievement.name, awarded_at=at
                )
                for name, achievement, at in detail.achievements[:_ACHIEVEMENTS_SHOWN]
            ],
            "seasons": [
                TeamSeasonResponse(
                    season=result.season,
                    pakistan_season=PakistanSeasonResponse.for_brawlhalla_season(result.season),
                    best=result.best,
                    average=result.average,
                    players=result.players,
                )
                for result in detail.seasons
            ],
        }
    )
