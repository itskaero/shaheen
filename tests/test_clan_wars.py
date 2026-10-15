"""Clan Wars (docs/DECISIONS.md ADR-131): the rules, the live week, recording
finished weeks once, and the season table."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from database.models.ranking_snapshot import RankingSnapshot
from database.models.team import Team
from database.repositories.brawlhalla_player_repository import BrawlhallaPlayerRepository
from database.repositories.ranking_snapshot_repository import RankingSnapshotRepository
from database.repositories.team_repository import TeamRepository
from services.clan_war_service import ClanWarService
from services.clan_wars import TEAM_TOP_N, WIN_POINTS, player_points, season_table, team_points
from services.team_service import TeamService

GUILD = 1
# Thursday 15 Oct 2026, 12:00 PKT. The week began Monday 12 Oct 00:00 PKT
# (Sunday 11 Oct 19:00 UTC).
NOW = datetime(2026, 10, 15, 7, tzinfo=UTC)
WEEK_START = datetime(2026, 10, 11, 19, tzinfo=UTC)
MONDAY = date(2026, 10, 12)


def _snap(*, wins: int, rating: int | None, season: int = 42) -> RankingSnapshot:
    return RankingSnapshot(
        brawlhalla_player_id=0,
        captured_at=NOW,
        rating=rating,
        peak_rating=rating,
        tier=None,
        wins=wins,
        games=wins * 2,
        season=season,
    )


# --- rules -------------------------------------------------------------------


def test_player_points_are_wins_and_rating_gained() -> None:
    start, latest = _snap(wins=10, rating=1500), _snap(wins=14, rating=1530)
    assert player_points(start, latest) == 4 * WIN_POINTS + 30


def test_a_rating_loss_costs_nothing_but_wins_still_count() -> None:
    assert player_points(_snap(wins=10, rating=1500), _snap(wins=12, rating=1440)) == 2 * WIN_POINTS


def test_no_readings_score_nothing() -> None:
    assert player_points(None, _snap(wins=1, rating=1)) == 0
    assert player_points(_snap(wins=1, rating=1), None) == 0
    assert player_points(_snap(wins=3, rating=None), _snap(wins=5, rating=1600)) == 2 * WIN_POINTS


def test_team_points_sum_the_best_members_only() -> None:
    assert team_points([5, 50, 0, 40, 30, 20, 10, 1]) == 50 + 40 + 30 + 20 + 10
    assert TEAM_TOP_N == 5
    assert team_points([]) == 0


def test_season_table_orders_by_wins_then_points_then_fewer_weeks() -> None:
    table = season_table(
        [
            (1, 100, 1),
            (2, 300, 2),
            (1, 90, 2),
            (2, 400, 1),
            (3, 500, 1),
            (3, 10, 3),
        ]
    )
    assert [(r.team_id, r.wins, r.points, r.weeks) for r in table] == [
        (2, 1, 700, 2),
        (3, 1, 510, 2),
        (1, 1, 190, 2),
    ]


# --- the database ---------------------------------------------------------------


async def _team(session: AsyncSession, name: str, tag: str) -> Team:
    return await TeamService(session).create(
        guild_id=GUILD, name=name, tag=tag, actor_discord_id=999
    )


async def _member(
    session: AsyncSession,
    team: Team,
    bid: int,
    readings: list[tuple[datetime, int, int]],
    *,
    season: int = 42,
) -> None:
    """A team member with (captured_at, wins, rating) readings."""
    player = await BrawlhallaPlayerRepository(session).upsert(
        brawlhalla_player_id=bid, player_name=f"P{bid}", region=None
    )
    await TeamRepository(session).add_member(
        team_id=team.id, player_id=player.id, role="player", joined_at=NOW - timedelta(days=30)
    )
    for at, wins, rating in readings:
        await RankingSnapshotRepository(session).add(
            RankingSnapshot(
                brawlhalla_player_id=player.id,
                captured_at=at,
                rating=rating,
                peak_rating=rating,
                tier="Gold",
                wins=wins,
                games=wins * 2,
                season=season,
            )
        )


async def test_the_live_week_counts_from_the_last_reading_before_it(
    session: AsyncSession,
) -> None:
    red = await _team(session, "Red Hawks", "RH")
    blue = await _team(session, "Blue Wolves", "BW")
    before = WEEK_START - timedelta(hours=3)
    # Red: one player, +3 wins and +40 rating this week.
    await _member(session, red, 1, [(before, 20, 1500), (NOW - timedelta(hours=1), 23, 1540)])
    # Blue: two players; one gained, one only lost rating (scores wins only).
    await _member(session, blue, 2, [(before, 5, 1600), (NOW - timedelta(hours=2), 6, 1650)])
    await _member(session, blue, 3, [(before, 9, 1700), (NOW - timedelta(hours=2), 11, 1650)])

    week = await ClanWarService(session).week(GUILD, now=NOW)

    assert week.week_start == MONDAY
    assert week.season == 42
    # Blue: P2 1 win + 50 rating = 60, P3 2 wins + 0 = 20, so 80. Red: 3 wins + 40 = 70.
    assert [(t.team.tag, t.points) for t in week.standings] == [("BW", 80), ("RH", 70)]
    blue_week = week.standings[0]
    assert [s.player.player_name for s in blue_week.scorers] == ["P2", "P3"]


async def test_a_team_with_nobody_playing_scores_zero_and_still_shows(
    session: AsyncSession,
) -> None:
    await _team(session, "Quiet Ones", "QO")
    week = await ClanWarService(session).week(GUILD, now=NOW)
    assert [(t.team.tag, t.points, t.scorers) for t in week.standings] == [("QO", 0, [])]


async def test_last_week_is_recorded_once_from_readings_before_it_ended(
    session: AsyncSession,
) -> None:
    red = await _team(session, "Red Hawks", "RH")
    blue = await _team(session, "Blue Wolves", "BW")
    last_start = WEEK_START - timedelta(days=7)
    # Red won last week (+5 wins); its reading this week must not count.
    await _member(
        session,
        red,
        1,
        [
            (last_start - timedelta(hours=1), 10, 1500),
            (WEEK_START - timedelta(hours=1), 15, 1500),
            (NOW - timedelta(hours=1), 40, 1900),
        ],
    )
    await _member(
        session,
        blue,
        2,
        [(last_start - timedelta(hours=1), 10, 1500), (WEEK_START - timedelta(hours=1), 12, 1510)],
    )
    service = ClanWarService(session)

    recorded = await service.record_finished(GUILD, now=NOW)
    assert [(r.team_id, r.points, r.place, r.week_start) for r in recorded] == [
        (red.id, 5 * WIN_POINTS, 1, MONDAY - timedelta(days=7)),
        (blue.id, 2 * WIN_POINTS + 10, 2, MONDAY - timedelta(days=7)),
    ]
    # A second tick records nothing.
    assert await service.record_finished(GUILD, now=NOW + timedelta(hours=6)) == []

    board = await service.board(GUILD, now=NOW)
    assert [(r.team.tag, r.wins, r.points, r.weeks) for r in board.season_table] == [
        ("RH", 1, 50, 1),
        ("BW", 0, 30, 1),
    ]
    assert board.last_winner is not None
    assert board.last_winner.team.tag == "RH"


async def test_a_week_nobody_scored_in_records_nothing(session: AsyncSession) -> None:
    await _team(session, "Red Hawks", "RH")
    assert await ClanWarService(session).record_finished(GUILD, now=NOW) == []


async def test_a_finished_week_keeps_its_own_season(session: AsyncSession) -> None:
    """A new Brawlhalla season starting this Monday doesn't zero last week."""
    red = await _team(session, "Red Hawks", "RH")
    last_start = WEEK_START - timedelta(days=7)
    await _member(
        session,
        red,
        1,
        [(last_start - timedelta(hours=1), 10, 1500), (WEEK_START - timedelta(hours=1), 13, 1520)],
        season=42,
    )
    # Season 43 readings this week, for someone else.
    other = await _team(session, "Blue Wolves", "BW")
    await _member(session, other, 2, [(NOW - timedelta(hours=1), 1, 1000)], season=43)

    recorded = await ClanWarService(session).record_finished(GUILD, now=NOW)
    assert [(r.season, r.points) for r in recorded] == [(42, 3 * WIN_POINTS + 20)]
