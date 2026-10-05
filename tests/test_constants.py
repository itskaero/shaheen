"""Structural invariants on bot/constants.py — the BRAWLISTAN server spec
(docs/DECISIONS.md ADR-109). A duplicate logical_key would silently break
ProvisionedResource idempotency (ADR-011), so these are worth a regression
guard, as is the brief's exact role and channel list.
"""

from __future__ import annotations

from bot.constants import (
    CATEGORIES,
    LEADERSHIP_ROLES,
    ROLES,
    STAFF_ROLES,
    spec_keys,
)


def _channels() -> list[str]:
    return [channel.name for category in CATEGORIES for channel in category.channels]


def test_role_logical_keys_are_unique() -> None:
    keys = [role.logical_key for role in ROLES]
    assert len(keys) == len(set(keys))


def test_role_names_are_unique() -> None:
    names = [role.name for role in ROLES]
    assert len(names) == len(set(names))


def test_exactly_the_brief_roles_in_order() -> None:
    assert [role.name for role in ROLES] == [
        "Founder",
        "Admin",
        "Moderator",
        "Team Captain",
        "Contributor",
        "Verified",
        "Player",
    ]


def test_no_role_is_created_with_any_permission() -> None:
    """The owner grants permissions by hand; /setup never does."""
    for role in ROLES:
        assert role.permissions.value == 0, role.name


def test_no_rank_specific_roles() -> None:
    tiers = ("valhallan", "diamond", "platinum", "gold", "silver", "bronze", "tin", "rank")
    for role in ROLES:
        assert not any(tier in role.name.lower() for tier in tiers), role.name


def test_founder_keeps_the_old_leader_key_so_the_role_carries_over() -> None:
    assert ROLES[0].logical_key == "role:shaheen_leader"


def test_staff_and_leadership_roles_are_spec_roles() -> None:
    keys = {role.logical_key for role in ROLES}
    assert {role.logical_key for role in STAFF_ROLES} <= keys
    assert set(LEADERSHIP_ROLES) <= set(STAFF_ROLES)


def test_exactly_the_brief_channels_by_category() -> None:
    layout = {category.name: [c.name for c in category.channels] for category in CATEGORIES}
    assert layout == {
        "START HERE": ["welcome", "rules", "announcements"],
        "BRAWLISTAN": ["rankings", "tournaments", "looking-for-game"],
        "COMMUNITY": ["general", "clips", "achievements"],
        "SUPPORT": ["bot-commands", "report"],
    }


def test_channel_names_and_keys_are_unique() -> None:
    names = _channels()
    assert len(names) == len(set(names))
    keys = [c.logical_key for category in CATEGORIES for c in category.channels]
    assert len(keys) == len(set(keys))


def test_spec_keys_cover_every_role_category_and_channel() -> None:
    keys = spec_keys()
    assert len(keys) == len(ROLES) + len(CATEGORIES) + len(_channels())
    assert "channel:mod_log" not in keys
    assert "role:guest" not in keys
