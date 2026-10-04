"""/link and /unlink.

Stays thin (docs/ARCHITECTURE.md): all persistence/Brawlhalla orchestration
lives in services/link_service.py; this cog only handles the Discord-side
flow (confirmation, role promotion) described in docs/COMMANDS.md.
"""

from __future__ import annotations

import logging

import discord
from discord import app_commands
from discord.ext import commands

from bot.checks.permissions import require_staff_authorized
from bot.client import ShaheenBot
from bot.constants import FULL_MEMBER_ROLES, ROLE_ALLY, ROLE_TRIAL
from bot.content.profile_embeds import (
    build_link_code_embed,
    build_link_preview_embed,
    build_link_success_embed,
    build_unlink_confirm_embed,
    build_unlink_success_embed,
    build_verify_embed,
)
from bot.views.confirm import ConfirmView
from core.exceptions import ShaheenError
from database.models.provisioned_resource import ResourceType
from database.repositories.audit_log_repository import AuditLogRepository
from database.repositories.provisioned_resource_repository import ProvisionedResourceRepository
from database.session import session_scope
from integrations.brawlhalla.errors import BrawlhallaAPIError
from services.link_code_service import LinkCodeService
from services.link_service import LinkService
from services.snapshot_service import SnapshotRunResult, SnapshotService

logger = logging.getLogger(__name__)


class LinkCog(commands.Cog):
    def __init__(self, bot: ShaheenBot) -> None:
        self.bot = bot

    @app_commands.command(
        name="link", description="Link your Discord account to your Brawlhalla profile"
    )
    @app_commands.describe(
        identifier="Your Brawlhalla or Steam64 ID — or leave empty for a website link code"
    )
    async def link(self, interaction: discord.Interaction, identifier: str | None = None) -> None:
        member = interaction.user
        if not isinstance(member, discord.Member):
            raise ShaheenError("This command can only be used inside the server.")

        await interaction.response.defer(ephemeral=True)

        if identifier is None:
            # Website claim flow (ADR-107): a one-time code to enter on the
            # player's profile page.
            async with session_scope(self.bot.session_factory) as session:
                issued = await LinkCodeService(session).issue(
                    guild_id=member.guild.id, discord_id=member.id
                )
            await interaction.followup.send(
                embed=build_link_code_embed(
                    code=issued.code,
                    expires_at=issued.expires_at,
                    site_url=self.bot.settings.site_url,
                ),
                ephemeral=True,
            )
            return

        async with session_scope(self.bot.session_factory) as session:
            link_service = LinkService(session, self.bot.brawlhalla)
            candidate = await link_service.resolve_candidate(identifier)
            existing = await link_service.get_active_link(
                guild_id=member.guild.id, discord_id=member.id
            )
        previous_name = existing[1].player_name if existing else None

        preview = build_link_preview_embed(
            candidate_name=candidate.name,
            candidate_id=candidate.brawlhalla_id,
            previous_player_name=previous_name,
        )
        view = ConfirmView(author_id=member.id)
        message = await interaction.followup.send(
            embed=preview, view=view, ephemeral=True, wait=True
        )
        await view.wait()
        if not view.confirmed:
            await message.edit(content="Link cancelled.", embed=None, view=None)
            return

        async with session_scope(self.bot.session_factory) as session:
            link_service = LinkService(session, self.bot.brawlhalla)
            outcome = await link_service.link(
                guild_id=member.guild.id,
                discord_id=member.id,
                joined_at=member.joined_at,
                candidate=candidate,
            )

        # Take an initial snapshot now instead of leaving the member absent
        # from /leaderboard and the website until the next scheduled
        # snapshot tick (up to SNAPSHOT_INTERVAL_HOURS later, ADR-059) —
        # both leaderboards skip any player with zero RankingSnapshot rows.
        # A Brawlhalla hiccup here must never fail /link itself, matching
        # link_service.py's own "region is a nice-to-have" pattern.
        try:
            async with session_scope(self.bot.session_factory) as session:
                await SnapshotService(
                    session,
                    self.bot.brawlhalla,
                    season=self.bot.current_brawlhalla_season(),
                ).snapshot_member(outcome.member, outcome.player, member.id, SnapshotRunResult())
        except BrawlhallaAPIError as exc:
            logger.warning("Initial snapshot after /link failed for %s: %s", member.id, exc)

        promoted = await self._maybe_promote(member)
        embed = build_link_success_embed(player_name=outcome.player.player_name, promoted=promoted)
        await message.edit(content=None, embed=embed, view=None)

    @app_commands.command(name="unlink", description="Remove your active Brawlhalla link")
    async def unlink(self, interaction: discord.Interaction) -> None:
        member = interaction.user
        if not isinstance(member, discord.Member):
            raise ShaheenError("This command can only be used inside the Shaheen server.")

        await interaction.response.defer(ephemeral=True)

        async with session_scope(self.bot.session_factory) as session:
            link_service = LinkService(session, self.bot.brawlhalla)
            existing = await link_service.get_active_link(
                guild_id=member.guild.id, discord_id=member.id
            )

        if existing is None:
            await interaction.followup.send(
                "You don't have an active Brawlhalla link.", ephemeral=True
            )
            return

        player_name = existing[1].player_name
        view = ConfirmView(author_id=member.id)
        message = await interaction.followup.send(
            embed=build_unlink_confirm_embed(player_name), view=view, ephemeral=True, wait=True
        )
        await view.wait()
        if not view.confirmed:
            await message.edit(content="Unlink cancelled.", embed=None, view=None)
            return

        async with session_scope(self.bot.session_factory) as session:
            link_service = LinkService(session, self.bot.brawlhalla)
            await link_service.unlink(guild_id=member.guild.id, discord_id=member.id)

        await message.edit(content=None, embed=build_unlink_success_embed(player_name), view=None)

    @app_commands.command(
        name="verify",
        description="Confirm a member owns their linked Brawlhalla account (staff)",
    )
    @app_commands.describe(
        user="The member to verify", revoke="Withdraw verification instead of granting it"
    )
    @require_staff_authorized()
    async def verify(
        self, interaction: discord.Interaction, user: discord.Member, revoke: bool = False
    ) -> None:
        """Staff-only (ADR-107): a link or website claim proves Discord
        ownership, not Brawlhalla ownership. Staff check that separately
        (e.g. a screenshot of the in-game profile) and mark it here.
        """
        await interaction.response.defer(ephemeral=True)
        guild = user.guild
        async with session_scope(self.bot.session_factory) as session:
            player = await LinkService(session, self.bot.brawlhalla).set_verified(
                guild_id=guild.id,
                discord_id=user.id,
                staff_discord_id=interaction.user.id,
                verified=not revoke,
            )
            if player is None:
                raise ShaheenError(f"{user.display_name} hasn't linked a Brawlhalla account yet.")
            await AuditLogRepository(session).add(
                guild_id=guild.id,
                action="link.unverify" if revoke else "link.verify",
                source="discord",
                actor_discord_id=interaction.user.id,
                subject=f"{player.player_name} ({player.brawlhalla_player_id})",
            )
            role_resource = await ProvisionedResourceRepository(session).get(
                guild_id=guild.id, resource_type=ResourceType.ROLE, logical_key="role:verified"
            )
        role = guild.get_role(role_resource.discord_id) if role_resource else None
        if role is not None:
            try:
                if revoke:
                    await user.remove_roles(role, reason="BRAWLISTAN /verify revoke")
                else:
                    await user.add_roles(role, reason="BRAWLISTAN /verify")
            except discord.Forbidden:
                logger.warning("Missing permission to change the Verified role on %s", user.id)
        await interaction.followup.send(
            embed=build_verify_embed(player_name=player.player_name, verified=not revoke),
            ephemeral=True,
        )

    async def _maybe_promote(self, member: discord.Member) -> bool:
        """Promote ALLY -> TRIAL SHAHEEN on link (docs/DECISIONS.md ADR-090,
        superseding ADR-026).

        ADR-026 promoted straight from Guest, which let anyone skip the
        approval flow (docs/DECISIONS.md ADR-089) entirely by simply
        running /link before ever applying. Only an already-approved Ally
        gets promoted here now; a Guest who links stays Guest until they
        apply and staff approves them. Members who already hold Trial or
        any higher rank role are left unchanged — promotion beyond Trial
        stays a manual staff decision.
        """
        member_role_names = {role.name for role in member.roles}
        full_member_role_names = {role.name for role in FULL_MEMBER_ROLES}
        if member_role_names & full_member_role_names:
            return False  # already Trial or above — nothing to do
        if ROLE_ALLY.name not in member_role_names:
            return False  # not yet approved — /link alone doesn't grant access

        guild = member.guild
        ally_role = discord.utils.get(guild.roles, name=ROLE_ALLY.name)
        trial_role = discord.utils.get(guild.roles, name=ROLE_TRIAL.name)
        if trial_role is None:
            return False  # /setup hasn't run yet; nothing to assign.

        try:
            if ally_role is not None and ally_role in member.roles:
                await member.remove_roles(ally_role, reason="Shaheen /link")
            await member.add_roles(trial_role, reason="Shaheen /link")
        except discord.Forbidden:
            logger.warning("Missing permission to promote %s after /link", member.id)
            return False
        return True


async def setup(bot: ShaheenBot) -> None:
    await bot.add_cog(LinkCog(bot))
