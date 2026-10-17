"""Clan Wars rules (docs/DECISIONS.md ADR-131). Pure: no database, no Discord.

A weekly team league, Monday 00:00 to Monday 00:00 Pakistan time (the same
week as the quests, services/quests.py). Each member earns war points from
their ranked play that week, worked out from the ranking snapshots the bot
already takes, never self-reported:

    WIN_POINTS per ranked win, plus every rating point gained (net, never
    negative).

A team's score is the sum of its best TEAM_TOP_N members, so a big roster
can't win on headcount alone, but a team still needs that many active
players. The season table ranks teams by weeks won, then total points.

ADR-136 adds fairness and rivalry:
- a member counts for the team they were on when the week began (the roster
  is locked), and only if their account already had MIN_GAMES ranked games
  before the week, so a fresh alt can't farm a week;
- every week the teams are paired into head-to-head duels (round robin), and
  the week's top scorer is its MVP.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date

from database.models.ranking_snapshot import RankingSnapshot

WIN_POINTS = 10
TEAM_TOP_N = 5
# Ranked games an account needs before the week starts for its points to
# count (ADR-136). Settings.clan_wars_min_games overrides it.
MIN_GAMES = 10
# Duel pairings rotate from this Monday, one round-robin round per week.
_EPOCH_MONDAY = date(2026, 1, 5)


def eligible(before_week: RankingSnapshot | None, min_games: int = MIN_GAMES) -> bool:
    """Whether a member's points count this week: their account was already
    seen before the week began, with at least `min_games` ranked games."""
    return before_week is not None and before_week.games >= min_games


def player_points(start: RankingSnapshot | None, latest: RankingSnapshot | None) -> int:
    """A member's war points for the week, from where it began to now."""
    if start is None or latest is None:
        return 0
    wins = max(0, latest.wins - start.wins)
    gain = 0
    if start.rating is not None and latest.rating is not None:
        gain = max(0, latest.rating - start.rating)
    return wins * WIN_POINTS + gain


def team_points(member_points: Iterable[int]) -> int:
    return sum(sorted((p for p in member_points if p > 0), reverse=True)[:TEAM_TOP_N])


@dataclass(frozen=True)
class SeasonRecord:
    team_id: int
    wins: int
    points: int
    weeks: int


def season_table(results: Sequence[tuple[int, int, int]]) -> list[SeasonRecord]:
    """(team_id, points, place) per recorded team-week -> the season table:
    most weeks won first, then most points, then fewest weeks played."""
    totals: dict[int, list[int]] = {}
    for team_id, points, place in results:
        wins, total, weeks = totals.setdefault(team_id, [0, 0, 0])
        totals[team_id] = [wins + (place == 1), total + points, weeks + 1]
    table = [SeasonRecord(t, w, p, n) for t, (w, p, n) in totals.items()]
    table.sort(key=lambda r: (-r.wins, -r.points, r.weeks, r.team_id))
    return table


# --- duels (ADR-136) -----------------------------------------------------------


def duel_pairs(team_ids: Sequence[int], week_start: date) -> list[tuple[int, int | None]]:
    """This week's head-to-head pairings, by the circle method: over N-1
    weeks (N rounded up to even) every team meets every other once. With an
    odd number of teams one team has a bye (paired with None). Deterministic
    for a given set of teams and week."""
    teams: list[int | None] = list(sorted(team_ids))
    if len(teams) < 2:
        return []
    if len(teams) % 2:
        teams.append(None)
    n = len(teams)
    week_index = (week_start - _EPOCH_MONDAY).days // 7
    shift = week_index % (n - 1)
    rest = teams[1:]
    rest = rest[-shift:] + rest[:-shift] if shift else rest
    order = [teams[0], *rest]
    pairs: list[tuple[int, int | None]] = []
    for i in range(n // 2):
        a, b = order[i], order[n - 1 - i]
        if a is None:
            a, b = b, None
        assert a is not None
        pairs.append((a, b) if b is None or a < b else (b, a))
    return pairs


@dataclass(frozen=True)
class DuelResult:
    team_a: int
    team_b: int | None  # None: a bye
    points_a: int
    points_b: int

    @property
    def winner(self) -> int | None:
        """The team ahead, or None for a draw or a bye."""
        if self.team_b is None or self.points_a == self.points_b:
            return None
        return self.team_a if self.points_a > self.points_b else self.team_b


def duel_results(
    pairs: Sequence[tuple[int, int | None]], points: dict[int, int]
) -> list[DuelResult]:
    return [DuelResult(a, b, points.get(a, 0), points.get(b, 0) if b else 0) for a, b in pairs]


@dataclass(frozen=True)
class DuelRecord:
    wins: int = 0
    draws: int = 0
    losses: int = 0


def duel_records(weeks: Iterable[Sequence[DuelResult]]) -> dict[int, DuelRecord]:
    """Each team's season duel record. Byes and 0-0 weeks don't count."""
    tally: dict[int, list[int]] = {}
    for week in weeks:
        for duel in week:
            if duel.team_b is None or (duel.points_a == 0 and duel.points_b == 0):
                continue
            for team, mine, theirs in (
                (duel.team_a, duel.points_a, duel.points_b),
                (duel.team_b, duel.points_b, duel.points_a),
            ):
                won, drew, lost = tally.setdefault(team, [0, 0, 0])
                tally[team] = [
                    won + (mine > theirs),
                    drew + (mine == theirs),
                    lost + (mine < theirs),
                ]
    return {team: DuelRecord(*counts) for team, counts in tally.items()}
