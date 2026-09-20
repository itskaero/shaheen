"""Setup idempotency planning — docs/SETUP_FLOW.md's core contract."""

import discord

from bot.constants import CategorySpec, ChannelSpec, RoleSpec
from database.models.provisioned_resource import ResourceType
from services.setup_planner import (
    ActionType,
    GuildSnapshot,
    LiveCategory,
    LiveChannel,
    LiveRole,
    build_plan,
)

ROLE = RoleSpec(
    logical_key="role:test", name="🧪 TEST ROLE", color=0x123456, hoist=True, mentionable=False
)


def _live_role_matching(spec: RoleSpec, *, id: int, **overrides: object) -> LiveRole:
    fields = {
        "id": id,
        "name": spec.name,
        "color": spec.color,
        "hoist": spec.hoist,
        "mentionable": spec.mentionable,
        "permissions_value": spec.permissions.value,
        **overrides,
    }
    return LiveRole(**fields)  # type: ignore[arg-type]


def test_role_is_created_when_nothing_exists() -> None:
    plan = build_plan((ROLE,), (), {}, GuildSnapshot())
    (action,) = plan.role_actions
    assert action.type is ActionType.CREATE
    assert plan.has_changes


def test_role_is_verified_when_known_mapping_matches_live_state() -> None:
    live = _live_role_matching(ROLE, id=42)
    known = {(ResourceType.ROLE, ROLE.logical_key): 42}
    plan = build_plan((ROLE,), (), known, GuildSnapshot(roles=(live,)))
    (action,) = plan.role_actions
    assert action.type is ActionType.VERIFY
    assert not plan.has_changes


def test_role_is_repaired_when_attributes_drift() -> None:
    live = _live_role_matching(ROLE, id=42, color=0x000000)
    known = {(ResourceType.ROLE, ROLE.logical_key): 42}
    plan = build_plan((ROLE,), (), known, GuildSnapshot(roles=(live,)))
    (action,) = plan.role_actions
    assert action.type is ActionType.REPAIR
    assert any("color" in d for d in action.diffs)
    assert plan.has_changes


def test_role_is_adopted_when_name_matches_but_nothing_is_stored() -> None:
    live = _live_role_matching(ROLE, id=99)
    plan = build_plan((ROLE,), (), {}, GuildSnapshot(roles=(live,)))
    (action,) = plan.role_actions
    assert action.type is ActionType.ADOPT
    assert action.existing_id == 99


def test_role_falls_back_to_name_match_when_stored_id_is_gone() -> None:
    live = _live_role_matching(ROLE, id=99)
    known = {(ResourceType.ROLE, ROLE.logical_key): 12345}  # deleted role's old id
    plan = build_plan((ROLE,), (), known, GuildSnapshot(roles=(live,)))
    (action,) = plan.role_actions
    assert action.type is ActionType.ADOPT
    assert action.existing_id == 99


CATEGORY = CategorySpec(
    logical_key="category:test",
    name="🧪 TEST",
    channels=(ChannelSpec("channel:test", "🧪-test", "text", topic="testing"),),
)


def test_category_and_channel_created_together() -> None:
    plan = build_plan((), (CATEGORY,), {}, GuildSnapshot())
    assert plan.category_actions[0].type is ActionType.CREATE
    assert plan.channel_actions[0].type is ActionType.CREATE
    assert plan.channel_actions[0].category_logical_key == CATEGORY.logical_key


def test_channel_repaired_on_topic_drift() -> None:
    live_category = LiveCategory(id=1, name=CATEGORY.name)
    live_channel = LiveChannel(id=2, name="🧪-test", kind="text", category_id=1, topic="old topic")
    known = {
        (ResourceType.CATEGORY, CATEGORY.logical_key): 1,
        (ResourceType.CHANNEL, "channel:test"): 2,
    }
    plan = build_plan(
        (), (CATEGORY,), known, GuildSnapshot(categories=(live_category,), channels=(live_channel,))
    )
    assert plan.category_actions[0].type is ActionType.VERIFY
    assert plan.channel_actions[0].type is ActionType.REPAIR
    assert any("topic" in d for d in plan.channel_actions[0].diffs)


def test_repair_role_diff_matches_real_discord_permissions_semantics() -> None:
    # Regression guard: RoleSpec.permissions must compare via .value, not identity.
    role = RoleSpec(
        logical_key="role:perm",
        name="🧪 PERM",
        color=0,
        permissions=discord.Permissions(manage_messages=True),
    )
    live = LiveRole(
        id=1, name=role.name, color=0, hoist=True, mentionable=False, permissions_value=0
    )
    known = {(ResourceType.ROLE, role.logical_key): 1}
    plan = build_plan((role,), (), known, GuildSnapshot(roles=(live,)))
    assert plan.role_actions[0].type is ActionType.REPAIR


def test_channel_repaired_when_its_category_moved() -> None:
    """docs/DECISIONS.md ADR-091: a channel whose CategorySpec now points
    it at a different category (e.g. leaderboard/hall-of-fame moving out of
    SHAHEEN ARENA) must be detected as needing a repair, not silently left
    parented under the old category forever.
    """
    live_category = LiveCategory(id=1, name=CATEGORY.name)
    other_category = LiveCategory(id=9, name="🧪 OLD HOME")
    # The channel actually lives under category id 9 (its old home), while
    # its CategorySpec now says it belongs under CATEGORY (live id 1).
    live_channel = LiveChannel(id=2, name="🧪-test", kind="text", category_id=9, topic="testing")
    known = {
        (ResourceType.CATEGORY, CATEGORY.logical_key): 1,
        (ResourceType.CHANNEL, "channel:test"): 2,
    }
    plan = build_plan(
        (),
        (CATEGORY,),
        known,
        GuildSnapshot(categories=(live_category, other_category), channels=(live_channel,)),
    )
    assert plan.channel_actions[0].type is ActionType.REPAIR
    assert any("category" in d for d in plan.channel_actions[0].diffs)


def test_channel_not_repaired_when_already_in_its_configured_category() -> None:
    live_category = LiveCategory(id=1, name=CATEGORY.name)
    live_channel = LiveChannel(id=2, name="🧪-test", kind="text", category_id=1, topic="testing")
    known = {
        (ResourceType.CATEGORY, CATEGORY.logical_key): 1,
        (ResourceType.CHANNEL, "channel:test"): 2,
    }
    plan = build_plan(
        (), (CATEGORY,), known, GuildSnapshot(categories=(live_category,), channels=(live_channel,))
    )
    assert plan.channel_actions[0].type is ActionType.VERIFY


def test_channel_reparenting_not_flagged_when_its_category_is_also_new() -> None:
    """A channel adopted by name inside a category that's itself being
    CREATEd this run has nothing to compare its live category_id against
    yet — it'll be correctly parented by the CREATE path, not flagged here.
    """
    # The channel already exists (adopted by name) but under some
    # unrelated, unknown category — CATEGORY itself has no known mapping,
    # so it's a fresh CREATE this run.
    live_channel = LiveChannel(id=2, name="🧪-test", kind="text", category_id=999, topic="testing")
    plan = build_plan((), (CATEGORY,), {}, GuildSnapshot(channels=(live_channel,)))
    assert plan.category_actions[0].type is ActionType.CREATE
    assert plan.channel_actions[0].type is ActionType.ADOPT
    assert not any("category" in d for d in plan.channel_actions[0].diffs)
