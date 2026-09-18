"""Which Discord rank role a Brawlhalla tier earns (docs/DECISIONS.md ADR-087).

Pure: plain strings in, plain strings out, no Discord and no database — the
snapshot loop already knows every member's tier, and bot/cogs/clan.py turns
the plan below into actual role edits. Keeping it here means the mapping is
unit-testable and stays usable by the future website/API.

Only Gold and above map to a role. Below that a tier label says more about
how much ranked someone has played than how good they are.
"""

from __future__ import annotations

from dataclasses import dataclass

from bot.constants import (
    ROLE_RANK_DIAMOND,
    ROLE_RANK_GOLD,
    ROLE_RANK_PLATINUM,
    ROLE_RANK_VALHALLAN,
)
from services.achievements import tier_index

# Index into services/achievements.py's _TIER_ORDER
# ("tin", "bronze", "silver", "gold", "platinum", "diamond", "diamond+",
# "valhallan") -> the logical key of the role that tier earns. tin/bronze/
# silver are deliberately absent, and "diamond+" collapses into Diamond
# rather than getting a role of its own.
_TIER_INDEX_TO_ROLE_KEY: dict[int, str] = {
    3: ROLE_RANK_GOLD.logical_key,
    4: ROLE_RANK_PLATINUM.logical_key,
    5: ROLE_RANK_DIAMOND.logical_key,
    6: ROLE_RANK_DIAMOND.logical_key,
    7: ROLE_RANK_VALHALLAN.logical_key,
}

ALL_RANK_ROLE_KEYS: frozenset[str] = frozenset(
    (
        ROLE_RANK_GOLD.logical_key,
        ROLE_RANK_PLATINUM.logical_key,
        ROLE_RANK_DIAMOND.logical_key,
        ROLE_RANK_VALHALLAN.logical_key,
    )
)


@dataclass(frozen=True)
class RankRolePlan:
    """What to change for one member. Both fields empty means "nothing to do".

    `grant` is the single role the member's current tier earns (None when
    they're below Gold or unranked); `revoke` is every other rank role they
    currently hold, so a demotion or a promotion both leave exactly one.
    """

    grant: str | None
    revoke: tuple[str, ...]

    @property
    def is_noop(self) -> bool:
        return self.grant is None and not self.revoke


def rank_role_key_for_tier(tier: str | None) -> str | None:
    """The rank role a tier earns, or None for unranked/below Gold.

    Fails closed on an unrecognized tier string (`tier_index` returns None),
    which means a Brawlhalla rename can never hand out a wrong role — it just
    stops granting until the tier table is updated.
    """
    if tier is None:
        return None
    index = tier_index(tier)
    if index is None:
        return None
    return _TIER_INDEX_TO_ROLE_KEY.get(index)


def plan_rank_roles(*, tier: str | None, current_keys: set[str]) -> RankRolePlan:
    """Diff a member's current rank roles against the one their tier earns.

    `current_keys` is the set of rank-role logical keys the member already
    holds; anything outside ALL_RANK_ROLE_KEYS is ignored, so a member's clan
    ladder and self-assigned roles are never touched.
    """
    earned = rank_role_key_for_tier(tier)
    held = current_keys & ALL_RANK_ROLE_KEYS
    revoke = tuple(sorted(held - {earned} if earned is not None else held))
    grant = earned if earned is not None and earned not in held else None
    return RankRolePlan(grant=grant, revoke=revoke)
