"""GET /clan-wars — Clan Wars (docs/DECISIONS.md ADR-131): this week's team
standings, the season table and last week's winner. Brawlhalla identity only
(ADR-040): scorers are players, never Discord accounts.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_session, get_settings
from api.schemas import (
    ClanWarMemberResponse,
    ClanWarSeasonRowResponse,
    ClanWarsResponse,
    ClanWarStandingResponse,
    ClanWarWinnerResponse,
)
from core.config import Settings
from database.models.team import Team
from services.clan_war_service import ClanWarService
from services.clan_wars import TEAM_TOP_N, WIN_POINTS
from services.players_service import player_slug

router = APIRouter(prefix="/clan-wars", tags=["clan-wars"])


def _team(team: Team) -> dict[str, object]:
    return {
        "slug": team.slug,
        "name": team.name,
        "tag": team.tag,
        "logo": team.logo,
        "accent": team.accent,
    }


@router.get("", response_model=ClanWarsResponse)
async def get_clan_wars(
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> ClanWarsResponse:
    board = await ClanWarService(session).board(settings.guild_id)
    week = board.week
    last = board.last_winner
    return ClanWarsResponse(
        season=week.season,
        week_start=week.week_start,
        ends_at=week.ends_at,
        win_points=WIN_POINTS,
        top_n=TEAM_TOP_N,
        standings=[
            ClanWarStandingResponse(
                **_team(standing.team),  # type: ignore[arg-type]
                place=place,
                points=standing.points,
                scorers=[
                    ClanWarMemberResponse(
                        brawlhalla_id=s.player.brawlhalla_player_id,
                        player_name=s.player.player_name,
                        slug=player_slug(s.player.player_name, s.player.brawlhalla_player_id),
                        points=s.points,
                    )
                    for s in standing.scorers
                ],
            )
            for place, standing in enumerate(week.standings, start=1)
        ],
        season_table=[
            ClanWarSeasonRowResponse(
                **_team(row.team),  # type: ignore[arg-type]
                wins=row.wins,
                points=row.points,
                weeks=row.weeks,
            )
            for row in board.season_table
        ],
        last_winner=(
            ClanWarWinnerResponse(
                **_team(last.team),  # type: ignore[arg-type]
                points=last.points,
                week_start=last.week_start,
            )
            if last
            else None
        ),
    )
