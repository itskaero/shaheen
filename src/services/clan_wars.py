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
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from database.models.ranking_snapshot import RankingSnapshot

WIN_POINTS = 10
TEAM_TOP_N = 5


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
