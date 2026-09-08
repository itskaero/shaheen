"""Pure /setup idempotency planning logic.

No Discord I/O and no database access happens here — this module takes a
plain snapshot of what currently exists (built by the caller from live
Discord data) plus the previously-recorded ProvisionedResource mappings, and
returns a plan of what to do. That separation is what makes setup planning
unit-testable per docs/DEVELOPMENT.md's testing priorities, and is required
for docs/SETUP_FLOW.md's idempotency contract: look up by stored ID first,
fall back to name matching, and never blindly recreate.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass

from bot.constants import CategorySpec, ChannelSpec, RoleSpec
from database.models.provisioned_resource import ResourceType


class ActionType(enum.StrEnum):
    CREATE = "create"  # no existing resource found by ID or name — must be created
    ADOPT = "adopt"  # found by name, no prior stored mapping — persist the mapping
    VERIFY = "verify"  # stored mapping still points at a matching resource — no-op
    REPAIR = "repair"  # resource exists but its attributes drifted from the spec


@dataclass(frozen=True)
class LiveRole:
    id: int
    name: str
    color: int
    hoist: bool
    mentionable: bool
    permissions_value: int


@dataclass(frozen=True)
class LiveCategory:
    id: int
    name: str


@dataclass(frozen=True)
class LiveChannel:
    id: int
    name: str
    kind: str  # "text" | "voice"
    category_id: int | None
    topic: str | None = None


@dataclass(frozen=True)
class GuildSnapshot:
    roles: tuple[LiveRole, ...] = ()
    categories: tuple[LiveCategory, ...] = ()
    channels: tuple[LiveChannel, ...] = ()


@dataclass(frozen=True)
class RoleAction:
    type: ActionType
    spec: RoleSpec
    existing_id: int | None = None
    diffs: tuple[str, ...] = ()


@dataclass(frozen=True)
class CategoryAction:
    type: ActionType
    spec: CategorySpec
    existing_id: int | None = None
    diffs: tuple[str, ...] = ()


@dataclass(frozen=True)
class ChannelAction:
    type: ActionType
    spec: ChannelSpec
    category_logical_key: str
    existing_id: int | None = None
    diffs: tuple[str, ...] = ()


@dataclass(frozen=True)
class SetupPlan:
    role_actions: tuple[RoleAction, ...]
    category_actions: tuple[CategoryAction, ...]
    channel_actions: tuple[ChannelAction, ...]

    @property
    def has_changes(self) -> bool:
        return (
            any(a.type is not ActionType.VERIFY for a in self.role_actions)
            or any(a.type is not ActionType.VERIFY for a in self.category_actions)
            or any(a.type is not ActionType.VERIFY for a in self.channel_actions)
        )


# Maps (resource_type, logical_key) -> the Discord ID previously recorded for it.
KnownResources = dict[tuple[ResourceType, str], int]


def _plan_role(spec: RoleSpec, known: KnownResources, snapshot: GuildSnapshot) -> RoleAction:
    known_id = known.get((ResourceType.ROLE, spec.logical_key))
    live_by_id = {r.id: r for r in snapshot.roles}

    live = live_by_id.get(known_id) if known_id is not None else None
    if live is not None:
        base_type = ActionType.VERIFY
    else:
        # Stored ID is gone (or never existed) — fall back to a name match.
        live = next((r for r in snapshot.roles if r.name == spec.name), None)
        base_type = ActionType.ADOPT if live is not None else ActionType.CREATE

    if live is None:
        return RoleAction(type=ActionType.CREATE, spec=spec)

    diffs = _role_diffs(spec, live)
    final_type = ActionType.REPAIR if diffs else base_type
    return RoleAction(type=final_type, spec=spec, existing_id=live.id, diffs=diffs)


def _role_diffs(spec: RoleSpec, live: LiveRole) -> tuple[str, ...]:
    diffs = []
    if live.name != spec.name:
        diffs.append(f"name: {live.name!r} -> {spec.name!r}")
    if live.color != spec.color:
        diffs.append(f"color: {live.color:#08x} -> {spec.color:#08x}")
    if live.hoist != spec.hoist:
        diffs.append(f"hoist: {live.hoist} -> {spec.hoist}")
    if live.mentionable != spec.mentionable:
        diffs.append(f"mentionable: {live.mentionable} -> {spec.mentionable}")
    if live.permissions_value != spec.permissions.value:
        diffs.append(f"permissions: {live.permissions_value} -> {spec.permissions.value}")
    return tuple(diffs)


def _plan_category(
    spec: CategorySpec, known: KnownResources, snapshot: GuildSnapshot
) -> CategoryAction:
    known_id = known.get((ResourceType.CATEGORY, spec.logical_key))
    live_by_id = {c.id: c for c in snapshot.categories}

    live = live_by_id.get(known_id) if known_id is not None else None
    if live is not None:
        base_type = ActionType.VERIFY
    else:
        live = next((c for c in snapshot.categories if c.name == spec.name), None)
        base_type = ActionType.ADOPT if live is not None else ActionType.CREATE

    if live is None:
        return CategoryAction(type=ActionType.CREATE, spec=spec)

    diffs = (f"name: {live.name!r} -> {spec.name!r}",) if live.name != spec.name else ()
    final_type = ActionType.REPAIR if diffs else base_type
    return CategoryAction(type=final_type, spec=spec, existing_id=live.id, diffs=diffs)


def _plan_channel(
    spec: ChannelSpec,
    category_logical_key: str,
    known: KnownResources,
    snapshot: GuildSnapshot,
) -> ChannelAction:
    known_id = known.get((ResourceType.CHANNEL, spec.logical_key))
    live_by_id = {c.id: c for c in snapshot.channels}

    live = live_by_id.get(known_id) if known_id is not None else None
    if live is not None:
        base_type = ActionType.VERIFY
    else:
        live = next(
            (c for c in snapshot.channels if c.name == spec.name and c.kind == spec.kind), None
        )
        base_type = ActionType.ADOPT if live is not None else ActionType.CREATE

    if live is None:
        return ChannelAction(
            type=ActionType.CREATE, spec=spec, category_logical_key=category_logical_key
        )

    diffs = _channel_diffs(spec, live)
    final_type = ActionType.REPAIR if diffs else base_type
    return ChannelAction(
        type=final_type,
        spec=spec,
        category_logical_key=category_logical_key,
        existing_id=live.id,
        diffs=diffs,
    )


def _channel_diffs(spec: ChannelSpec, live: LiveChannel) -> tuple[str, ...]:
    diffs = []
    if live.name != spec.name:
        diffs.append(f"name: {live.name!r} -> {spec.name!r}")
    if live.kind != spec.kind:
        diffs.append(f"kind: {live.kind} -> {spec.kind} (cannot be repaired automatically)")
    if spec.kind == "text" and (live.topic or None) != (spec.topic or None):
        diffs.append(f"topic: {live.topic!r} -> {spec.topic!r}")
    return tuple(diffs)


def build_plan(
    roles: tuple[RoleSpec, ...],
    categories: tuple[CategorySpec, ...],
    known: KnownResources,
    snapshot: GuildSnapshot,
) -> SetupPlan:
    """Diff the desired guild structure against `snapshot`/`known` mappings."""
    role_actions = tuple(_plan_role(spec, known, snapshot) for spec in roles)
    category_actions = tuple(_plan_category(spec, known, snapshot) for spec in categories)
    channel_actions = tuple(
        _plan_channel(channel_spec, category.logical_key, known, snapshot)
        for category in categories
        for channel_spec in category.channels
    )
    return SetupPlan(
        role_actions=role_actions,
        category_actions=category_actions,
        channel_actions=channel_actions,
    )
