"""Clan Wars fairness and rivalry (docs/DECISIONS.md ADR-136): rosters locked
at week start, the eligibility floor, weekly duels and the MVP."""

from __future__ import annotations

from datetime import date, timedelta
from itertools import combinations

from sqlalchemy.ext.asyncio import AsyncSession

from database.repositories.brawlhalla_player_repository import BrawlhallaPlayerRepository
from database.repositories.team_repository import TeamRepository
from services.clan_war_service import ClanWarService
from services.clan_wars import (
    WIN_POINTS,
    DuelResult,
    duel_pairs,
    duel_records,
    duel_results,
    eligible,
)
from tests.test_clan_wars import GUILD, MONDAY, NOW, WEEK_START, _member, _snap, _team

BEFORE = WEEK_START - timedelta(hours=3)
LATER = NOW - timedelta(hours=1)


# --- rules ------------------------------------------------------------------


def test_eligible_needs_an_account_seen_before_the_week_with_enough_games() -> None:
    assert not eligible(None)
    assert not eligible(_snap(wins=2, rating=1500), min_games=10)  # 4 games
    assert eligible(_snap(wins=5, rating=1500), min_games=10)  # 10 games
    assert eligible(_snap(wins=0, rating=None), min_games=0)


def test_duel_pairs_are_a_round_robin_with_a_bye_for_odd_teams() -> None:
    teams = [11, 12, 13, 14, 15]
    seen: set[tuple[int, int]] = set()
    byes: list[int] = []
    # Five teams (six slots with the bye): five weeks meet everyone once.
    for week in range(5):
        pairs = duel_pairs(teams, MONDAY + timedelta(weeks=week))
        assert len(pairs) == 3
        playing = [t for a, b in pairs for t in (a, b) if t is not None]
        assert sorted(playing) == teams  # everyone plays or has the bye once a week
        for a, b in pairs:
            if b is None:
                byes.append(a)
            else:
                seen.add((a, b))
    assert seen == set(combinations(teams, 2))
    assert sorted(byes) == teams
    assert duel_pairs(teams, MONDAY) == duel_pairs(list(reversed(teams)), MONDAY)
    assert duel_pairs([1], MONDAY) == []


def test_duel_results_and_season_records() -> None:
    week1 = duel_results([(1, 2), (3, None)], {1: 50, 2: 30, 3: 99})
    assert [d.winner for d in week1] == [1, None]
    week2 = duel_results([(1, 3), (2, None)], {1: 10, 3: 10})
    week3 = duel_results([(2, 3)], {})  # 0-0: no contest
    records = duel_records([week1, week2, week3])
    assert (records[1].wins, records[1].draws, records[1].losses) == (1, 1, 0)
    assert (records[2].wins, records[2].losses) == (0, 1)
    assert (records[3].draws, records[3].wins) == (1, 0)
    assert DuelResult(1, 2, 5, 5).winner is None


# --- the database ---------------------------------------------------------------


async def test_a_mid_week_transfer_does_not_move_points(session: AsyncSession) -> None:
    red = await _team(session, "Red Hawks", "RH")
    blue = await _team(session, "Blue Wolves", "BW")
    await _member(session, red, 1, [(BEFORE, 20, 1500), (LATER, 24, 1540)])
    service = ClanWarService(session)
    assert await service.lock_roster(GUILD, now=WEEK_START + timedelta(hours=1)) == 1
    assert await service.lock_roster(GUILD, now=NOW) == 0  # once a week

    # P1 moves to Blue mid-week: their points stay with Red this week.
    player = await BrawlhallaPlayerRepository(session).get_by_brawlhalla_id(1)
    assert player is not None
    repo = TeamRepository(session)
    membership = await repo.active_membership(player.id)
    assert membership is not None
    membership[0].left_at = NOW - timedelta(hours=2)
    await repo.add_member(team_id=blue.id, player_id=player.id, role="player", joined_at=NOW)

    week = await service.week(GUILD, now=NOW)
    assert week.roster_locked
    assert [(t.team.tag, t.points) for t in week.standings] == [
        ("RH", 4 * WIN_POINTS + 40),
        ("BW", 0),
    ]


async def test_a_fresh_account_is_shown_but_not_counted(session: AsyncSession) -> None:
    red = await _team(session, "Red Hawks", "RH")
    # First seen mid-week: no reading before the week, so it can't count yet.
    await _member(session, red, 1, [(WEEK_START + timedelta(hours=2), 0, 1000), (LATER, 9, 1200)])
    # Seen before the week with too few games (3 wins = 6 games < 10).
    await _member(session, red, 2, [(BEFORE, 3, 1100), (LATER, 8, 1180)])
    await _member(session, red, 3, [(BEFORE, 30, 1500), (LATER, 31, 1510)])

    week = await ClanWarService(session, min_games=10).week(GUILD, now=NOW)
    red_week = week.standings[0]
    assert [s.player.player_name for s in red_week.scorers] == ["P3"]
    assert sorted(s.player.player_name for s in red_week.ineligible) == ["P1", "P2"]
    assert red_week.points == WIN_POINTS + 10


async def test_duels_mvp_and_recorded_mvp(session: AsyncSession) -> None:
    red = await _team(session, "Red Hawks", "RH")
    blue = await _team(session, "Blue Wolves", "BW")
    last_start = WEEK_START - timedelta(days=7)
    await _member(
        session,
        red,
        1,
        [(last_start - timedelta(hours=1), 20, 1500), (WEEK_START - timedelta(hours=1), 25, 1530)],
    )
    await _member(
        session,
        blue,
        2,
        [(last_start - timedelta(hours=1), 20, 1500), (WEEK_START - timedelta(hours=1), 21, 1500)],
    )
    service = ClanWarService(session)

    finished = await service.finished_week(GUILD, now=NOW)
    assert finished.week_start == date(2026, 10, 5)
    (duel,) = finished.duels
    assert duel.winner == red.id
    assert finished.mvp is not None
    assert (finished.mvp.player.player_name, finished.mvp.points) == ("P1", 5 * WIN_POINTS + 30)

    await service.record_finished(GUILD, now=NOW)
    board = await service.board(GUILD, now=NOW)
    assert board.last_winner is not None and board.last_winner.mvp is not None
    assert board.last_winner.mvp.player.player_name == "P1"
    red_row = next(r for r in board.season_table if r.team.tag == "RH")
    blue_row = next(r for r in board.season_table if r.team.tag == "BW")
    assert (red_row.duels.wins, blue_row.duels.losses) == (1, 1)
