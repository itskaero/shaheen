"""Achievement catalog and pure evaluation logic (docs/DECISIONS.md ADR-030).

No Discord or database dependency here — evaluate_snapshot_achievements()
takes plain values and returns which achievements were newly earned, the
same "pure planning, testable in isolation" shape as
services/setup_planner.py.

This module is the source of truth for the catalog; the Phase 3 migration
seeds the `achievements` table from a literal copy of these values rather
than importing this module, since migrations should stay stable even if
this catalog changes later.
"""

from __future__ import annotations

from dataclasses import dataclass

# Ordered lowest to highest. Best-effort and may not match every real tier
# name the API returns — see docs/DECISIONS.md ADR-031: an unrecognized
# tier simply doesn't match, it never raises.
_TIER_ORDER = ("tin", "bronze", "silver", "gold", "platinum", "diamond", "diamond+", "valhallan")


@dataclass(frozen=True)
class AchievementDef:
    key: str
    name: str
    description: str


FIRST_LINK = AchievementDef(
    "first_link", "First Contact", "Linked a Brawlhalla account to Shaheen."
)
GAMES_100 = AchievementDef("games_100", "Centurion", "Played 100 games.")
GAMES_500 = AchievementDef("games_500", "Battle-Hardened", "Played 500 games.")
TIER_PLATINUM = AchievementDef(
    "tier_platinum", "Platinum Shaheen", "Reached Platinum tier in ranked."
)
TIER_DIAMOND_PLUS = AchievementDef(
    "tier_diamond_plus", "Diamond Shaheen", "Reached Diamond tier or higher in ranked."
)

CATALOG: tuple[AchievementDef, ...] = (
    FIRST_LINK,
    GAMES_100,
    GAMES_500,
    TIER_PLATINUM,
    TIER_DIAMOND_PLUS,
)

# Achievements evaluated from a scheduled snapshot cycle. first_link is
# awarded immediately by /link instead (see ADR-030).
SNAPSHOT_EVALUATED: tuple[AchievementDef, ...] = (
    GAMES_100,
    GAMES_500,
    TIER_PLATINUM,
    TIER_DIAMOND_PLUS,
)


def _tier_index(tier: str) -> int | None:
    normalized = tier.strip().lower()
    for index, name in enumerate(_TIER_ORDER):
        if normalized.startswith(name):
            return index
    return None


def tier_at_least(tier: str | None, threshold: str) -> bool:
    """True if `tier` is at or above `threshold` in _TIER_ORDER. Fails open (False)."""
    if tier is None:
        return False
    tier_index = _tier_index(tier)
    if tier_index is None:
        return False
    return tier_index >= _TIER_ORDER.index(threshold)


def evaluate_snapshot_achievements(
    *, games: int, ranked_tier: str | None, already_earned: set[str]
) -> tuple[AchievementDef, ...]:
    """Which of SNAPSHOT_EVALUATED are newly earned, given this cycle's stats."""
    earned = []
    if games >= 100 and GAMES_100.key not in already_earned:
        earned.append(GAMES_100)
    if games >= 500 and GAMES_500.key not in already_earned:
        earned.append(GAMES_500)
    if tier_at_least(ranked_tier, "platinum") and TIER_PLATINUM.key not in already_earned:
        earned.append(TIER_PLATINUM)
    if tier_at_least(ranked_tier, "diamond") and TIER_DIAMOND_PLUS.key not in already_earned:
        earned.append(TIER_DIAMOND_PLUS)
    return tuple(earned)
