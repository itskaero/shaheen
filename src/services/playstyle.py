"""Deriving "playstyle" tags from a member's per-Legend stats.

Brawlhalla's API has no such field — this is a heuristic label, not a
reported stat, and both call sites (docs/DECISIONS.md ADR-096: the /profile
embed, and the website player card) must say so rather than presenting it
as if the API reported it. Thresholds below are approximate, hand-picked
constants, not derived from any clan-wide baseline — tune them if they
feel wrong in practice, there's nothing sacred about the exact numbers.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

_AGGRESSIVE_KOS_PER_GAME = 1.2
_HEAVY_HITTER_DAMAGE_PER_GAME = 600.0
_SURVIVOR_FALLS_PER_GAME = 1.0

_FALLBACK_TAG = "Well-Rounded"


class _LegendStatsLike(Protocol):
    games: int
    kos: int
    damagedealt: int
    falls: int


def derive_playstyle_tags(legends: Sequence[_LegendStatsLike]) -> list[str]:
    """1-3 tags summarizing a member's aggregate per-game stats across every
    played Legend. Falls back to a single "Well-Rounded" tag when there
    aren't enough games to say anything meaningful, or when no tag's
    threshold is crossed.
    """
    total_games = sum(legend.games for legend in legends)
    if total_games == 0:
        return [_FALLBACK_TAG]

    kos_per_game = sum(legend.kos for legend in legends) / total_games
    damage_per_game = sum(legend.damagedealt for legend in legends) / total_games
    falls_per_game = sum(legend.falls for legend in legends) / total_games

    tags = []
    if kos_per_game >= _AGGRESSIVE_KOS_PER_GAME:
        tags.append("Aggressive")
    if damage_per_game >= _HEAVY_HITTER_DAMAGE_PER_GAME:
        tags.append("Heavy Hitter")
    if falls_per_game <= _SURVIVOR_FALLS_PER_GAME:
        tags.append("Survivor")

    return tags or [_FALLBACK_TAG]
