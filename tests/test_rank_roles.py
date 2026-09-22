"""Tier -> Discord rank role mapping (docs/DECISIONS.md ADR-087).

Pure logic, so these are plain assertions — no session, no guild.
"""

from __future__ import annotations

from bot.constants import (
    ROLE_RANK_DIAMOND,
    ROLE_RANK_GOLD,
    ROLE_RANK_PLATINUM,
    ROLE_RANK_RISING,
    ROLE_RANK_VALHALLAN,
)
from services.rank_roles import (
    ALL_RANK_ROLE_KEYS,
    plan_rank_roles,
    rank_role_key_for_tier,
)

RISING = ROLE_RANK_RISING.logical_key
GOLD = ROLE_RANK_GOLD.logical_key
PLATINUM = ROLE_RANK_PLATINUM.logical_key
DIAMOND = ROLE_RANK_DIAMOND.logical_key
VALHALLAN = ROLE_RANK_VALHALLAN.logical_key


def test_tier_families_map_to_their_role() -> None:
    assert rank_role_key_for_tier("Gold 2") == GOLD
    assert rank_role_key_for_tier("Platinum III") == PLATINUM
    assert rank_role_key_for_tier("Diamond") == DIAMOND
    assert rank_role_key_for_tier("Valhallan") == VALHALLAN


def test_below_gold_earns_rising_shaheen() -> None:
    """Tin/Bronze/Silver collapse into one combined role (ADR-097) rather
    than a role per tier or nothing at all.
    """
    for tier in ("Tin 1", "Bronze 3", "Silver II"):
        assert rank_role_key_for_tier(tier) == RISING


def test_unranked_and_unrecognized_tiers_fail_closed() -> None:
    assert rank_role_key_for_tier(None) is None
    # A Brawlhalla rename must never hand out a *wrong* role.
    assert rank_role_key_for_tier("Some New Tier") is None


def test_promotion_grants_the_new_role_and_revokes_the_old() -> None:
    plan = plan_rank_roles(tier="Diamond", current_keys={PLATINUM})
    assert plan.grant == DIAMOND
    assert plan.revoke == (PLATINUM,)


def test_demotion_revokes_down_to_one_role() -> None:
    plan = plan_rank_roles(tier="Gold 1", current_keys={DIAMOND, VALHALLAN})
    assert plan.grant == GOLD
    assert set(plan.revoke) == {DIAMOND, VALHALLAN}


def test_unchanged_tier_is_a_noop() -> None:
    """The loop runs every six hours; a steady member must cost zero API calls."""
    plan = plan_rank_roles(tier="Platinum 1", current_keys={PLATINUM})
    assert plan.is_noop
    assert plan.grant is None and plan.revoke == ()


def test_dropping_below_gold_demotes_to_rising_shaheen() -> None:
    plan = plan_rank_roles(tier="Silver 1", current_keys={GOLD})
    assert plan.grant == RISING
    assert plan.revoke == (GOLD,)


def test_unranked_member_with_no_roles_is_a_noop() -> None:
    assert plan_rank_roles(tier=None, current_keys=set()).is_noop


def test_other_roles_are_never_touched() -> None:
    """The member's clan ladder and self-assigned roles are not our business."""
    plan = plan_rank_roles(
        tier="Diamond", current_keys={"role:shaheen_member", "role:scrim_alerts", PLATINUM}
    )
    assert plan.grant == DIAMOND
    assert plan.revoke == (PLATINUM,)


def test_all_rank_role_keys_matches_the_mapping() -> None:
    mapped = {
        rank_role_key_for_tier(t) for t in ("Tin", "Gold", "Platinum", "Diamond", "Valhallan")
    }
    assert mapped == set(ALL_RANK_ROLE_KEYS)
