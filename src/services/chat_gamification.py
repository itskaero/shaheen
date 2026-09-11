"""Chat-message XP/leveling — pure logic (docs/DECISIONS.md ADR-065).

Discord/DB-free, same shape as services/achievements.py (ADR-030): the XP
curve, rank-title ladder, and per-message XP roll are all pure functions
callers combine with database/repositories/chat_activity_repository.py and
a Discord listener. Kept as a distinct system from services/achievements.py
— achievements track *Brawlhalla* progress (games played, ranked tier);
this tracks *in-Discord* activity, entirely independent of the external
Brawlhalla API.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

# xp_for_level(n) = 100 * n**2 — a standard quadratic Discord-bot XP curve:
# fast early levels (level 2 at 100xp, level 3 at 400xp), slowing down at
# higher levels (level 10 needs 8,100xp) so leveling stays meaningful.
_XP_PER_LEVEL_SQUARED = 100

# Per-message XP is a small random range rather than a fixed amount, so
# activity isn't perfectly predictable/farmable.
_MIN_MESSAGE_XP = 5
_MAX_MESSAGE_XP = 15

# Cooldown between XP-earning messages, in seconds — prevents spamming
# short messages to farm levels.
MESSAGE_XP_COOLDOWN_SECONDS = 60


@dataclass(frozen=True)
class RankTitle:
    name: str
    min_level: int


# A Brawlhalla-flavored community rank ladder — deliberately distinct from
# Brawlhalla's own ranked tiers (Bronze/Platinum/Diamond/...) so a member's
# chat level is never confused with their ranked standing. "Valhallan" is
# the one deliberate echo — Brawlhalla's own top ranked tier, reused here
# as the chat ladder's capstone.
RANK_TITLES: tuple[RankTitle, ...] = (
    RankTitle("Hatchling", min_level=1),
    RankTitle("Brawler", min_level=5),
    RankTitle("Warrior", min_level=10),
    RankTitle("Veteran", min_level=15),
    RankTitle("Elite", min_level=20),
    RankTitle("Legend", min_level=25),
    RankTitle("Valhallan", min_level=30),
)


def level_for_xp(xp: int) -> int:
    """The level reached at `xp` total experience. Monotonic and the
    exact inverse of xp_for_level — level_for_xp(xp_for_level(n)) == n.
    """
    if xp <= 0:
        return 1
    return max(1, math.isqrt(xp // _XP_PER_LEVEL_SQUARED) + 1)


def xp_for_level(level: int) -> int:
    """Total XP required to *reach* `level` (i.e. the xp threshold at
    which level_for_xp first returns `level`)."""
    if level <= 1:
        return 0
    return _XP_PER_LEVEL_SQUARED * (level - 1) ** 2


def rank_title_for_level(level: int) -> str:
    """The highest rank title whose min_level is at or below `level`.
    RANK_TITLES is defined lowest-to-highest, so the last match wins.
    """
    title = RANK_TITLES[0].name
    for rank in RANK_TITLES:
        if level >= rank.min_level:
            title = rank.name
    return title


def roll_message_xp() -> int:
    """A random per-message XP award in [_MIN_MESSAGE_XP, _MAX_MESSAGE_XP]."""
    return random.randint(_MIN_MESSAGE_XP, _MAX_MESSAGE_XP)  # noqa: S311 - gameplay flavor, not security
