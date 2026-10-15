"""Weekly quests and the season level (docs/DECISIONS.md ADR-128). Pure rules.

Three quests a week, verified from the ranking snapshots the bot already
takes every few hours, never self-reported:
- play ranked games, win ranked games, gain rating (net, this season).
A week runs Monday 00:00 to Monday 00:00 Pakistan time. Each completed quest
is worth XP_PER_QUEST season XP; the season level is 1 + XP / XP_PER_QUEST,
capped at MAX_LEVEL, and starts again with each new Brawlhalla season.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta, timezone

from database.models.ranking_snapshot import RankingSnapshot

PKT = timezone(timedelta(hours=5), "PKT")
XP_PER_QUEST = 100
MAX_LEVEL = 30


@dataclass(frozen=True)
class Quest:
    key: str
    label: str
    target: int


QUESTS: tuple[Quest, ...] = (
    Quest("grind", "Play 15 ranked games", 15),
    Quest("win", "Win 8 ranked games", 8),
    Quest("climb", "Gain 50 rating", 50),
)


def week_bounds(now: datetime) -> tuple[date, datetime, datetime]:
    """(the Monday, the week's start, its end) for `now`, in Pakistan time."""
    local = now.astimezone(PKT)
    monday = local.date() - timedelta(days=local.weekday())
    start = datetime(monday.year, monday.month, monday.day, tzinfo=PKT)
    return monday, start.astimezone(UTC), (start + timedelta(days=7)).astimezone(UTC)


def baseline(
    snapshots: Sequence[RankingSnapshot], *, week_start: datetime, season: int
) -> RankingSnapshot | None:
    """Where the week's progress counts from: the last reading of this
    season before the week began, or else the week's first reading (a player
    first seen, or a season that started, mid-week). Oldest-first input."""
    same_season = [s for s in snapshots if s.season == season]
    before = [s for s in same_season if _aware(s.captured_at) < week_start]
    if before:
        return before[-1]
    return same_season[0] if same_season else None


def progress(quest: Quest, start: RankingSnapshot | None, latest: RankingSnapshot | None) -> int:
    if start is None or latest is None:
        return 0
    if quest.key == "grind":
        value = latest.games - start.games
    elif quest.key == "win":
        value = latest.wins - start.wins
    elif start.rating is None or latest.rating is None:
        value = 0
    else:
        value = latest.rating - start.rating
    return max(0, value)


def level(xp: int) -> int:
    return min(MAX_LEVEL, 1 + xp // XP_PER_QUEST)


def _aware(moment: datetime) -> datetime:
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)  # SQLite drops the zone
