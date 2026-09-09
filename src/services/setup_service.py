"""Executes a SetupPlan against a live Discord guild and the database.

docs/SETUP_FLOW.md order: roles -> categories -> channels -> permissions ->
verification/report. This module is the only place that mutates Discord
guild structure; bot/cogs/setup.py stays a thin wrapper around it
(docs/ARCHITECTURE.md).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import discord
from sqlalchemy.ext.asyncio import AsyncSession

from bot.constants import (
    CATEGORIES,
    ROLES,
    ROLES_WITH_STAFF_ACCESS,
    CategorySpec,
    ChannelSpec,
)
from core.config import SetupMode
from database.models.provisioned_resource import ResourceType
from database.repositories.guild_settings_repository import GuildSettingsRepository
from database.repositories.provisioned_resource_repository import ProvisionedResourceRepository
from services.setup_planner import (
    ActionType,
    CategoryAction,
    ChannelAction,
    GuildSnapshot,
    LiveCategory,
    LiveChannel,
    LiveRole,
    RoleAction,
    SetupPlan,
    build_plan,
)

logger = logging.getLogger(__name__)

OverwriteTarget = discord.Role | discord.Member | discord.Object


@dataclass
class ActionSummary:
    created: list[str] = field(default_factory=list)
    adopted: list[str] = field(default_factory=list)
    repaired: list[str] = field(default_factory=list)
    verified: int = 0

    def record(self, action_type: ActionType, label: str) -> None:
        if action_type is ActionType.CREATE:
            self.created.append(label)
        elif action_type is ActionType.ADOPT:
            self.adopted.append(label)
        elif action_type is ActionType.REPAIR:
            self.repaired.append(label)
        else:
            self.verified += 1

    @property
    def total(self) -> int:
        return len(self.created) + len(self.adopted) + len(self.repaired) + self.verified


@dataclass
class SetupReport:
    mode: SetupMode
    roles: ActionSummary = field(default_factory=ActionSummary)
    categories: ActionSummary = field(default_factory=ActionSummary)
    channels: ActionSummary = field(default_factory=ActionSummary)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def build_snapshot(guild: discord.Guild) -> GuildSnapshot:
    """Convert live discord.py objects into the plain snapshot the planner reads."""
    roles = tuple(
        LiveRole(
            id=role.id,
            name=role.name,
            color=role.color.value,
            hoist=role.hoist,
            mentionable=role.mentionable,
            permissions_value=role.permissions.value,
        )
        for role in guild.roles
        if not role.is_default()
    )
    categories = tuple(
        LiveCategory(id=category.id, name=category.name) for category in guild.categories
    )

    text_and_voice: list[discord.TextChannel | discord.VoiceChannel] = [
        *guild.text_channels,
        *guild.voice_channels,
    ]
    channels = tuple(
        LiveChannel(
            id=chan.id,
            name=chan.name,
            kind="text" if isinstance(chan, discord.TextChannel) else "voice",
            category_id=chan.category_id,
            topic=chan.topic if isinstance(chan, discord.TextChannel) else None,
        )
        for chan in text_and_voice
    )
    return GuildSnapshot(roles=roles, categories=categories, channels=channels)


class SetupService:
    """Business logic for /setup — usable independently of any Discord cog."""

    def __init__(self, guild: discord.Guild, session: AsyncSession) -> None:
        self._guild = guild
        self._session = session
        self._resources = ProvisionedResourceRepository(session)
        self._settings = GuildSettingsRepository(session)

    async def plan(self) -> SetupPlan:
        """Read-only diff of desired vs. live guild structure."""
        known = await self._known_resources()
        snapshot = build_snapshot(self._guild)
        return build_plan(ROLES, CATEGORIES, known, snapshot)

    async def apply(self, mode: SetupMode) -> SetupReport:
        """Create/verify/repair the guild structure. Never deletes anything."""
        report = SetupReport(mode=mode)
        current_plan = await self.plan()

        role_by_key = await self._apply_roles(current_plan.role_actions, report)
        await self._reposition_roles(role_by_key, report)

        category_by_key = await self._apply_categories(
            current_plan.category_actions, role_by_key, report
        )
        await self._apply_channels(current_plan.channel_actions, category_by_key, report)

        await self._settings.set_mode(self._guild.id, mode)
        return report

    async def _known_resources(self) -> dict[tuple[ResourceType, str], int]:
        rows = await self._resources.list_for_guild(self._guild.id)
        return {(row.resource_type, row.logical_key): row.discord_id for row in rows}

    async def _remember(
        self, resource_type: ResourceType, logical_key: str, discord_id: int
    ) -> None:
        await self._resources.upsert(
            guild_id=self._guild.id,
            resource_type=resource_type,
            logical_key=logical_key,
            discord_id=discord_id,
        )

    async def _apply_roles(
        self, actions: tuple[RoleAction, ...], report: SetupReport
    ) -> dict[str, discord.Role]:
        role_by_key: dict[str, discord.Role] = {}
        for action in actions:
            spec = action.spec
            try:
                resolved_role: discord.Role | None
                if action.type is ActionType.CREATE:
                    resolved_role = await self._guild.create_role(
                        name=spec.name,
                        colour=discord.Colour(spec.color),
                        hoist=spec.hoist,
                        mentionable=spec.mentionable,
                        permissions=spec.permissions,
                        reason="Shaheen /setup",
                    )
                else:
                    assert action.existing_id is not None
                    resolved_role = self._guild.get_role(action.existing_id)
                    if resolved_role is None:
                        report.warnings.append(
                            f"Role {spec.name!r} was recorded but no longer exists; recreating."
                        )
                        resolved_role = await self._guild.create_role(
                            name=spec.name,
                            colour=discord.Colour(spec.color),
                            hoist=spec.hoist,
                            mentionable=spec.mentionable,
                            permissions=spec.permissions,
                            reason="Shaheen /setup (repair: missing role)",
                        )
                        action = RoleAction(type=ActionType.CREATE, spec=spec)
                    elif action.type is ActionType.REPAIR:
                        await resolved_role.edit(
                            name=spec.name,
                            colour=discord.Colour(spec.color),
                            hoist=spec.hoist,
                            mentionable=spec.mentionable,
                            permissions=spec.permissions,
                            reason="Shaheen /setup (repair)",
                        )

                role_by_key[spec.logical_key] = resolved_role
                await self._remember(ResourceType.ROLE, spec.logical_key, resolved_role.id)
                report.roles.record(action.type, spec.name)
            except discord.Forbidden:
                report.errors.append(f"Missing permission to create/edit role {spec.name!r}.")
            except discord.HTTPException as exc:
                report.errors.append(f"Discord error for role {spec.name!r}: {exc}")
        return role_by_key

    async def _reposition_roles(
        self, role_by_key: dict[str, discord.Role], report: SetupReport
    ) -> None:
        me = self._guild.me
        if me is None or me.top_role is None:
            return
        ordered = [
            role_by_key[spec.logical_key] for spec in ROLES if spec.logical_key in role_by_key
        ]
        if not ordered:
            return
        top = me.top_role.position
        positions: dict[discord.abc.Snowflake, int] = {
            role: max(1, top - 1 - idx)
            for idx, role in enumerate(ordered)
            if role.position != max(1, top - 1 - idx)
        }
        if not positions:
            return
        try:
            await self._guild.edit_role_positions(positions=positions, reason="Shaheen /setup")
        except discord.Forbidden:
            report.warnings.append(
                "Could not reorder roles — Shaheen's own role must be moved above the roles it "
                "manages in Server Settings."
            )
        except discord.HTTPException as exc:
            report.warnings.append(f"Could not reorder roles: {exc}")

    async def _apply_categories(
        self,
        actions: tuple[CategoryAction, ...],
        role_by_key: dict[str, discord.Role],
        report: SetupReport,
    ) -> dict[str, discord.CategoryChannel]:
        category_by_key: dict[str, discord.CategoryChannel] = {}
        for action in actions:
            spec = action.spec
            overwrites = self._category_overwrites(spec, role_by_key)
            try:
                resolved_category: discord.CategoryChannel | None
                if action.type is ActionType.CREATE:
                    resolved_category = await self._guild.create_category(
                        name=spec.name, overwrites=overwrites, reason="Shaheen /setup"
                    )
                else:
                    assert action.existing_id is not None
                    channel = self._guild.get_channel(action.existing_id)
                    resolved_category = (
                        channel if isinstance(channel, discord.CategoryChannel) else None
                    )
                    if resolved_category is None:
                        report.warnings.append(
                            f"Category {spec.name!r} was recorded but no longer exists; recreating."
                        )
                        resolved_category = await self._guild.create_category(
                            name=spec.name, overwrites=overwrites, reason="Shaheen /setup (repair)"
                        )
                        action = CategoryAction(type=ActionType.CREATE, spec=spec)
                    else:
                        if action.type is ActionType.REPAIR:
                            await resolved_category.edit(
                                name=spec.name, reason="Shaheen /setup (repair)"
                            )
                        if overwrites:
                            await resolved_category.edit(
                                overwrites=overwrites, reason="Shaheen /setup"
                            )

                category_by_key[spec.logical_key] = resolved_category
                await self._remember(ResourceType.CATEGORY, spec.logical_key, resolved_category.id)
                report.categories.record(action.type, spec.name)
            except discord.Forbidden:
                report.errors.append(f"Missing permission to create/edit category {spec.name!r}.")
            except discord.HTTPException as exc:
                report.errors.append(f"Discord error for category {spec.name!r}: {exc}")
        return category_by_key

    def _category_overwrites(
        self, spec: CategorySpec, role_by_key: dict[str, discord.Role]
    ) -> dict[OverwriteTarget, discord.PermissionOverwrite]:
        if not spec.restricted:
            return {}
        overwrites: dict[OverwriteTarget, discord.PermissionOverwrite] = {
            self._guild.default_role: discord.PermissionOverwrite(view_channel=False)
        }
        for staff_spec in ROLES_WITH_STAFF_ACCESS:
            role = role_by_key.get(staff_spec.logical_key)
            if role is not None:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True)
        return overwrites

    async def _apply_channels(
        self,
        actions: tuple[ChannelAction, ...],
        category_by_key: dict[str, discord.CategoryChannel],
        report: SetupReport,
    ) -> None:
        for action in actions:
            spec = action.spec
            category = category_by_key.get(action.category_logical_key)
            try:
                resolved_channel: discord.TextChannel | discord.VoiceChannel | None
                if action.type is ActionType.CREATE:
                    resolved_channel = await self._create_channel(spec, category)
                else:
                    assert action.existing_id is not None
                    live_channel = self._guild.get_channel(action.existing_id)
                    resolved_channel = (
                        live_channel
                        if isinstance(live_channel, discord.TextChannel | discord.VoiceChannel)
                        else None
                    )
                    if resolved_channel is None:
                        report.warnings.append(
                            f"Channel {spec.name!r} was recorded but no longer exists; recreating."
                        )
                        resolved_channel = await self._create_channel(spec, category)
                        action = ChannelAction(
                            type=ActionType.CREATE,
                            spec=spec,
                            category_logical_key=action.category_logical_key,
                        )
                    elif action.type is ActionType.REPAIR:
                        if any("kind:" in d for d in action.diffs):
                            report.warnings.append(
                                f"Channel {spec.name!r} exists as the wrong type and needs "
                                "manual recreation."
                            )
                        elif isinstance(resolved_channel, discord.TextChannel):
                            # discord.py's stub requires str, but the runtime accepts None to
                            # clear an existing topic — which is exactly what a spec with no
                            # topic should repair to.
                            await resolved_channel.edit(
                                name=spec.name,
                                topic=spec.topic,  # type: ignore[arg-type]
                                reason="Shaheen /setup (repair)",
                            )
                        else:
                            await resolved_channel.edit(
                                name=spec.name, reason="Shaheen /setup (repair)"
                            )

                await self._remember(ResourceType.CHANNEL, spec.logical_key, resolved_channel.id)
                report.channels.record(action.type, spec.name)
            except discord.Forbidden:
                report.errors.append(f"Missing permission to create/edit channel {spec.name!r}.")
            except discord.HTTPException as exc:
                report.errors.append(f"Discord error for channel {spec.name!r}: {exc}")

    async def _create_channel(
        self, spec: ChannelSpec, category: discord.CategoryChannel | None
    ) -> discord.TextChannel | discord.VoiceChannel:
        if spec.kind == "text":
            return await self._guild.create_text_channel(
                name=spec.name,
                category=category,
                topic=spec.topic or discord.utils.MISSING,
                reason="Shaheen /setup",
            )
        return await self._guild.create_voice_channel(
            name=spec.name, category=category, reason="Shaheen /setup"
        )
