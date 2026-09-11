"""Structural invariants on bot/constants.py's role list — docs/DECISIONS.md
ADR-058. A duplicate logical_key would silently break ProvisionedResource
idempotency (ADR-011), so these are worth a regression guard.
"""

from __future__ import annotations

from bot.constants import CATEGORIES, ROLES, ROLES_WITH_STAFF_ACCESS, SELF_ASSIGN_ROLES


def test_role_logical_keys_are_unique() -> None:
    keys = [role.logical_key for role in ROLES]
    assert len(keys) == len(set(keys))


def test_role_names_are_unique() -> None:
    names = [role.name for role in ROLES]
    assert len(names) == len(set(names))


def test_self_assign_roles_are_a_subset_of_roles() -> None:
    role_keys = {role.logical_key for role in ROLES}
    for role in SELF_ASSIGN_ROLES:
        assert role.logical_key in role_keys


def test_self_assign_roles_carry_no_permissions() -> None:
    for role in SELF_ASSIGN_ROLES:
        assert role.permissions.value == 0


def test_self_assign_roles_are_not_staff_roles() -> None:
    staff_keys = {role.logical_key for role in ROLES_WITH_STAFF_ACCESS}
    for role in SELF_ASSIGN_ROLES:
        assert role.logical_key not in staff_keys


def test_self_assign_roles_positioned_below_rank_roles() -> None:
    """/setup repositions roles in ROLES order, highest first — self-assign
    roles must come after every rank role so they never outrank one.
    """
    self_assign_keys = {role.logical_key for role in SELF_ASSIGN_ROLES}
    seen_self_assign = False
    for role in ROLES:
        if role.logical_key in self_assign_keys:
            seen_self_assign = True
        elif seen_self_assign:
            raise AssertionError(f"rank role {role.logical_key!r} appears after a self-assign role")


def test_announcements_channel_is_staff_only_send() -> None:
    """docs/DECISIONS.md ADR-060 — everyone can read, only staff can post."""
    all_channels = (c for category in CATEGORIES for c in category.channels)
    channel = next(c for c in all_channels if c.logical_key == "channel:announcements")
    assert channel.staff_only_send is True


def test_moderation_category_is_restricted_to_staff() -> None:
    """docs/DECISIONS.md ADR-065 — #mod-log must stay staff-only, same as
    the DEVELOPMENT/SHAHEEN ARENA restricted categories.
    """
    category = next(c for c in CATEGORIES if c.logical_key == "category:moderation")
    assert category.restricted is True


def test_mod_log_channel_exists_in_moderation_category() -> None:
    category = next(c for c in CATEGORIES if c.logical_key == "category:moderation")
    channel = next(c for c in category.channels if c.logical_key == "channel:mod_log")
    assert channel.kind == "text"
