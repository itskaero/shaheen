"""GET /clan-wars — Clan Wars (docs/DECISIONS.md ADR-131, ADR-136): this
week's team standings, duels and MVP, the season table with duel records,
and last week's winner and MVP. Brawlhalla identity only (ADR-040): scorers
are players, never Discord accounts.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_session, get_settings
from api.schemas import (
    ClanWarDuelResponse,
    ClanWarMemberResponse,
    ClanWarMvpResponse,
    ClanWarSeasonRowResponse,
    ClanWarsResponse,
    ClanWarStandingResponse,
    ClanWarTeamRef,
    ClanWarWinnerResponse,
)
from core.config import Settings
from database.models.team import Team
from services.clan_war_service import ClanWarService, MemberScore, Mvp
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


def _member(score: MemberScore) -> ClanWarMemberResponse:
    player = score.player
    return ClanWarMemberResponse(
        brawlhalla_id=player.brawlhalla_player_id,
        player_name=player.player_name,
        slug=player_slug(player.player_name, player.brawlhalla_player_id),
        points=score.points,
    )


def _mvp(mvp: Mvp | None) -> ClanWarMvpResponse | None:
    if mvp is None:
        return None
    return ClanWarMvpResponse(
        **_member(MemberScore(mvp.player, mvp.points)).model_dump(),
        team_slug=mvp.team.slug if mvp.team else None,
        team_name=mvp.team.name if mvp.team else None,
        team_tag=mvp.team.tag if mvp.team else None,
    )


@router.get("", response_model=ClanWarsResponse)
async def get_clan_wars(
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> ClanWarsResponse:
    board = await ClanWarService(session, min_games=settings.clan_wars_min_games).board(
        settings.guild_id
    )
    week = board.week
    last = board.last_winner
    teams = {t.team.id: t.team for t in week.standings}
    slug_of = {team_id: team.slug for team_id, team in teams.items()}
    return ClanWarsResponse(
        season=week.season,
        week_start=week.week_start,
        ends_at=week.ends_at,
        win_points=WIN_POINTS,
        top_n=TEAM_TOP_N,
        min_games=settings.clan_wars_min_games,
        roster_locked=week.roster_locked,
        standings=[
            ClanWarStandingResponse(
                **_team(standing.team),  # type: ignore[arg-type]
                place=place,
                points=standing.points,
                scorers=[_member(s) for s in standing.scorers],
                ineligible=[_member(s) for s in standing.ineligible],
            )
            for place, standing in enumerate(week.standings, start=1)
        ],
        duels=[
            ClanWarDuelResponse(
                a=ClanWarTeamRef(**_team(teams[d.team_a])),  # type: ignore[arg-type]
                b=ClanWarTeamRef(**_team(teams[d.team_b])) if d.team_b else None,  # type: ignore[arg-type]
                points_a=d.points_a,
                points_b=d.points_b,
                leader=slug_of.get(d.winner) if d.winner else None,
            )
            for d in week.duels
            if d.team_a in teams and (d.team_b is None or d.team_b in teams)
        ],
        mvp=_mvp(week.mvp),
        season_table=[
            ClanWarSeasonRowResponse(
                **_team(row.team),  # type: ignore[arg-type]
                wins=row.wins,
                points=row.points,
                weeks=row.weeks,
                duel_wins=row.duels.wins,
                duel_draws=row.duels.draws,
                duel_losses=row.duels.losses,
            )
            for row in board.season_table
        ],
        last_winner=(
            ClanWarWinnerResponse(
                **_team(last.team),  # type: ignore[arg-type]
                points=last.points,
                week_start=last.week_start,
                mvp=_mvp(last.mvp),
            )
            if last
            else None
        ),
    )
