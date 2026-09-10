"""Persistent self-assign role panel for #roles (docs/DECISIONS.md ADR-058).

Opt-in pings/tags (bot.constants.SELF_ASSIGN_ROLES) — not the clan-rank
ladder, which stays staff-assigned (build_roles_embed in
bot/content/embeds.py). bot/cogs/setup.py posts this panel once,
idempotently, in launch mode; ShaheenBot.setup_hook() re-registers the view
globally on every process start so the buttons keep working across
restarts, routed by their static custom_id rather than by message.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import discord

from bot.constants import SELF_ASSIGN_ROLES, RoleSpec
from bot.views.base import PersistentView
from database.models.provisioned_resource import ResourceType
from database.repositories.provisioned_resource_repository import ProvisionedResourceRepository
from database.session import session_scope

if TYPE_CHECKING:
    from bot.client import ShaheenBot

_NOT_PROVISIONED = (
    "This role hasn't been set up yet — ask a staff member to run `/setup run`."
)


class SelfAssignRolesView(PersistentView):
    def __init__(self) -> None:
        super().__init__()
        for spec in SELF_ASSIGN_ROLES:
            self.add_item(_RoleToggleButton(spec))


class _RoleToggleButton(discord.ui.Button["SelfAssignRolesView"]):
    def __init__(self, spec: RoleSpec) -> None:
        # RoleSpec.name is "<emoji> <label>" (bot/constants.py) — split so
        # the button shows a real emoji instead of it as label text.
        emoji, _, label = spec.name.partition(" ")
        super().__init__(
            label=label,
            emoji=emoji,
            style=discord.ButtonStyle.secondary,
            custom_id=f"shaheen:role_toggle:{spec.logical_key}",
        )
        self._spec = spec

    async def callback(self, interaction: discord.Interaction) -> None:
        member = interaction.user
        if not isinstance(member, discord.Member) or interaction.guild is None:
            return

        bot = cast("ShaheenBot", interaction.client)
        async with session_scope(bot.session_factory) as session:
            resource = await ProvisionedResourceRepository(session).get(
                guild_id=interaction.guild.id,
                resource_type=ResourceType.ROLE,
                logical_key=self._spec.logical_key,
            )

        role = interaction.guild.get_role(resource.discord_id) if resource else None
        if role is None:
            await interaction.response.send_message(_NOT_PROVISIONED, ephemeral=True)
            return

        if role in member.roles:
            await member.remove_roles(role, reason="Self-assign role toggle")
            await interaction.response.send_message(f"Removed {role.mention}.", ephemeral=True)
        else:
            await member.add_roles(role, reason="Self-assign role toggle")
            await interaction.response.send_message(f"Added {role.mention}.", ephemeral=True)
