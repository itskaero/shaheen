"""Join access (docs/DECISIONS.md ADR-123): /access and /approval.

- `/access roles`: the join role (new members wait in it while approval is
  on) and the approved role (lets them in). Setup-level.
- `/access approval`: turn approval on or off. Setup-level.
- `/access status`: the current setup and what's missing.
- `/access sync`: give the join-time role to every member missing it. Setup-level.
- `/approval member`: swap a member's join role for the approved role. Staff.

New members get their role on join, or once they pass Discord's rules
screening if the server uses it. A join the bot missed (it was restarting,
or the role edit failed) is caught up by a sync every few minutes (ADR-126),
which only touches members with no other roles. The rules live in services/access_service.py;
this cog only reads and changes Discord roles. Channel access stays the
owner's to configure (ADR-109): the bot never edits permissions.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Set

import discord
from discord import app_commands
from discord.ext import commands, tasks

from bot.checks.permissions import require_setup_authorized, require_staff_authorized
from bot.client import ShaheenBot
from bot.constants import ROLE_PLAYER, ROLE_VERIFIED
from bot.palette import EMERALD
from bot.views.confirm import ConfirmView
from core.exceptions import ShaheenError
from database.models.provisioned_resource import ResourceType
from database.repositories.provisioned_resource_repository import ProvisionedResourceRepository
from database.session import session_scope
from services.access_service import (
    AccessConfig,
    AccessService,
    MemberRoles,
    members_missing_access,
    plan_approval,
)

logger = logging.getLogger(__name__)

# How often the catch-up sync runs, and how many members one pass may change
# (Discord rate-limits role edits; the rest wait for the next pass).
SYNC_MINUTES = 10
SYNC_BATCH = 50

# A join or approved role is handed out automatically, so it must not carry
# anything beyond ordinary member access.
_ELEVATED_PERMISSIONS = (
    "administrator",
    "manage_guild",
    "manage_roles",
    "manage_channels",
    "manage_webhooks",
    "manage_messages",
    "manage_nicknames",
    "manage_expressions",
    "manage_events",
    "kick_members",
    "ban_members",
    "moderate_members",
    "mention_everyone",
)


def role_problem(
    role: discord.Role,
    *,
    bot_top: discord.Role,
    actor: discord.Member,
    bot_managed: Set[int],
) -> str | None:
    """Why `role` can't be a join/approved role, or None if it can."""
    if role.is_default():
        return "@everyone can't be used: every member already has it."
    if role.managed:
        return f"{role.mention} belongs to an integration or bot, so it can't be handed out."
    if role.id in bot_managed:
        return (
            f"{role.mention} is handed out by the bot: only members with a linked "
            "Brawlhalla account keep it, so anyone approved without a link would lose it "
            "on the next sync. Create a separate role (for example Member) for approval."
        )
    elevated = [name for name in _ELEVATED_PERMISSIONS if getattr(role.permissions, name, False)]
    if elevated:
        listed = ", ".join(name.replace("_", " ") for name in elevated)
        return (
            f"{role.mention} has staff permissions ({listed}), "
            "so it can't be given out automatically."
        )
    if role >= bot_top:
        return f"Move the bot's role above {role.mention} in Server Settings → Roles first."
    if actor.id != actor.guild.owner_id and role >= actor.top_role:
        return f"You can only pick roles below your own highest role, and {role.mention} isn't."
    return None


def _member(interaction: discord.Interaction) -> discord.Member:
    member = interaction.user
    if not isinstance(member, discord.Member):
        raise ShaheenError("This command can only be used inside the BRAWLISTAN server.")
    return member


def _role_text(guild: discord.Guild, role_id: int | None) -> str:
    if role_id is None:
        return "not set"
    role = guild.get_role(role_id)
    return role.mention if role is not None else "a deleted role (set it again)"


def member_roles(members: Iterable[discord.Member]) -> list[MemberRoles]:
    return [
        MemberRoles(
            discord_id=m.id,
            role_ids=frozenset(r.id for r in m.roles if not r.is_default()),
            is_bot=m.bot,
            pending=m.pending,
        )
        for m in members
    ]


def placement_problems(guild: discord.Guild, config: AccessConfig) -> list[str]:
    """Configured roles the bot can't hand out any more, e.g. someone moved
    the role above the bot's own (the usual reason members get nothing)."""
    me = guild.me
    if me is None:
        return []
    problems = []
    for label, role_id in (("join", config.join_role_id), ("approved", config.approved_role_id)):
        role = guild.get_role(role_id) if role_id else None
        if role is not None and role >= me.top_role:
            problems.append(
                f"The {label} role {role.mention} is at or above the bot's role, so the bot "
                "can't give it. Drag the bot's role above it in Server Settings → Roles."
            )
    return problems


def build_status_embed(
    guild: discord.Guild, config: AccessConfig, *, missing: int | None = None
) -> discord.Embed:
    join_text = _role_text(guild, config.join_role_id)
    approved_text = _role_text(guild, config.approved_role_id)
    if config.approval_enabled:
        flow = f"New members get {join_text}. Staff run `/approval` to give them {approved_text}."
    else:
        flow = f"New members get {approved_text} straight away."
    embed = discord.Embed(title="🚪 Join access", description=flow, colour=EMERALD)
    embed.add_field(name="Approval", value="On" if config.approval_enabled else "Off")
    embed.add_field(name="Join role", value=join_text)
    embed.add_field(name="Approved role", value=approved_text)
    join_role = guild.get_role(config.join_role_id) if config.join_role_id else None
    if join_role is not None:
        waiting = sum(1 for member in join_role.members if not member.bot)
        embed.add_field(name="Waiting for approval", value=str(waiting))
    if missing:
        embed.add_field(
            name="Missing their role",
            value=f"{missing} member(s) hold neither role. `/access sync` gives it to them.",
            inline=False,
        )
    problems = config.warnings() + placement_problems(guild, config)
    me = guild.me
    if me is not None and not me.guild_permissions.manage_roles:
        problems.append("The bot is missing the Manage Roles permission.")
    if problems:
        embed.add_field(name="⚠️ Needs attention", value="\n".join(problems), inline=False)
    return embed


class AccessCog(commands.Cog):
    access = app_commands.Group(
        name="access", description="Which role new members get, and approval (admin)"
    )

    def __init__(self, bot: ShaheenBot) -> None:
        self.bot = bot
        self.sync_loop = tasks.loop(minutes=SYNC_MINUTES)(self._sync_tick)

    async def cog_load(self) -> None:
        self.sync_loop.before_loop(self.bot.wait_until_ready)
        self.sync_loop.start()

    async def cog_unload(self) -> None:
        self.sync_loop.cancel()

    # --- configuration ------------------------------------------------------

    async def _bot_managed_role_ids(self, guild: discord.Guild) -> set[int]:
        async with session_scope(self.bot.session_factory) as session:
            repo = ProvisionedResourceRepository(session)
            ids = set()
            for spec in (ROLE_PLAYER, ROLE_VERIFIED):
                resource = await repo.get(
                    guild_id=guild.id, resource_type=ResourceType.ROLE, logical_key=spec.logical_key
                )
                if resource is not None:
                    ids.add(resource.discord_id)
            return ids

    async def _check_roles(self, actor: discord.Member, *roles: discord.Role | None) -> None:
        guild = actor.guild
        me = guild.me
        if me is None or not me.guild_permissions.manage_roles:
            raise ShaheenError("The bot needs the Manage Roles permission to hand out roles.")
        bot_managed = await self._bot_managed_role_ids(guild)
        for role in roles:
            if role is None:
                continue
            problem = role_problem(role, bot_top=me.top_role, actor=actor, bot_managed=bot_managed)
            if problem:
                raise ShaheenError(problem)

    @access.command(name="status", description="Show the join role, approved role and approval")
    @require_setup_authorized()
    async def status(self, interaction: discord.Interaction) -> None:
        actor = _member(interaction)
        await interaction.response.defer(ephemeral=True)
        async with session_scope(self.bot.session_factory) as session:
            config = await AccessService(session).config(actor.guild.id)
        missing = members_missing_access(config, member_roles(actor.guild.members), everyone=True)
        await interaction.followup.send(
            embed=build_status_embed(actor.guild, config, missing=len(missing)), ephemeral=True
        )

    @access.command(name="roles", description="Set the join role and the approved role")
    @app_commands.describe(
        join_role="The role new members wait in while approval is on",
        approved_role="The role that lets members into the server",
        clear="Unset both roles (only while approval is off)",
    )
    @require_setup_authorized()
    async def roles(
        self,
        interaction: discord.Interaction,
        join_role: discord.Role | None = None,
        approved_role: discord.Role | None = None,
        clear: bool = False,
    ) -> None:
        actor = _member(interaction)
        if not clear and join_role is None and approved_role is None:
            raise ShaheenError("Pick a join role, an approved role, or both.")
        await interaction.response.defer(ephemeral=True)
        await self._check_roles(actor, join_role, approved_role)
        async with session_scope(self.bot.session_factory) as session:
            service = AccessService(session)
            current = await service.config(actor.guild.id)
            if clear:
                join_id, approved_id = None, None
            else:
                join_id = join_role.id if join_role else current.join_role_id
                approved_id = approved_role.id if approved_role else current.approved_role_id
            config = await service.set_roles(
                actor.guild.id,
                join_role_id=join_id,
                approved_role_id=approved_id,
                staff_discord_id=actor.id,
            )
        logger.info("/access roles by %s (clear=%s)", actor.id, clear)
        await interaction.followup.send(
            "Saved.", embed=build_status_embed(actor.guild, config), ephemeral=True
        )

    @access.command(name="approval", description="Turn member approval on or off")
    @app_commands.describe(
        enabled="On: new members get the join role and wait for /approval. "
        "Off: they get the approved role straight away."
    )
    @require_setup_authorized()
    async def approval_switch(self, interaction: discord.Interaction, enabled: bool) -> None:
        actor = _member(interaction)
        await interaction.response.defer(ephemeral=True)
        if enabled:
            async with session_scope(self.bot.session_factory) as session:
                current = await AccessService(session).config(actor.guild.id)
            await self._check_roles(
                actor,
                actor.guild.get_role(current.join_role_id or 0),
                actor.guild.get_role(current.approved_role_id or 0),
            )
        async with session_scope(self.bot.session_factory) as session:
            config = await AccessService(session).set_enabled(
                actor.guild.id, enabled=enabled, staff_discord_id=actor.id
            )
        logger.info("/access approval %s by %s", "on" if enabled else "off", actor.id)
        note = (
            "Approval is **on**."
            if enabled
            else "Approval is **off**. Members already waiting keep the join role until "
            "someone runs `/approval` for them."
        )
        await interaction.followup.send(
            note, embed=build_status_embed(actor.guild, config), ephemeral=True
        )

    # --- approving a member -------------------------------------------------

    @app_commands.command(name="approval", description="Let a member into the server (staff)")
    @app_commands.describe(member="The member to approve")
    @require_staff_authorized()
    async def approve(self, interaction: discord.Interaction, member: discord.Member) -> None:
        staff = _member(interaction)
        if member.bot:
            raise ShaheenError("Bots don't need approval.")
        await interaction.response.defer(ephemeral=True)
        async with session_scope(self.bot.session_factory) as session:
            config = await AccessService(session).config(staff.guild.id)
        change = plan_approval(config, {role.id for role in member.roles})
        if change.is_noop:
            await interaction.followup.send(
                f"{member.mention} is already approved.", ephemeral=True
            )
            return
        add = staff.guild.get_role(change.add) if change.add else None
        remove = staff.guild.get_role(change.remove) if change.remove else None
        if change.add and add is None:
            raise ShaheenError("The approved role was deleted. Set it again with /access roles.")
        await self._check_roles(staff, add, remove)

        reason = f"BRAWLISTAN approval by {staff}"
        try:
            if add is not None:
                await member.add_roles(add, reason=reason)
            if remove is not None:
                await member.remove_roles(remove, reason=reason)
        except discord.Forbidden as exc:
            raise ShaheenError(
                "Discord refused the role change; check the bot's role position."
            ) from exc
        except discord.HTTPException as exc:
            logger.warning("/approval role change failed for %s: %s", member.id, exc)
            raise ShaheenError(
                "Discord didn't accept the role change just now. Try again in a moment."
            ) from exc
        async with session_scope(self.bot.session_factory) as session:
            await AccessService(session).record_approval(
                staff.guild.id, member_discord_id=member.id, staff_discord_id=staff.id
            )
        logger.info("/approval: %s approved by %s", member.id, staff.id)
        await interaction.followup.send(
            f"✅ {member.mention} is approved" + (f" and now has {add.mention}." if add else "."),
            ephemeral=True,
        )

    # --- catching up -------------------------------------------------------

    @access.command(name="sync", description="Give the join-time role to every member missing it")
    @require_setup_authorized()
    async def sync(self, interaction: discord.Interaction) -> None:
        actor = _member(interaction)
        await interaction.response.defer(ephemeral=True)
        async with session_scope(self.bot.session_factory) as session:
            config = await AccessService(session).config(actor.guild.id)
        role_id = config.role_on_join()
        role = actor.guild.get_role(role_id) if role_id else None
        if role is None:
            raise ShaheenError("No role to give: set one with /access roles first.")
        await self._check_roles(actor, role)
        missing = members_missing_access(config, member_roles(actor.guild.members), everyone=True)
        if not missing:
            await interaction.followup.send(
                f"Everyone already has {role.mention} or the other access role.", ephemeral=True
            )
            return

        view = ConfirmView(author_id=actor.id)
        message = await interaction.followup.send(
            f"Give {role.mention} to **{len(missing)}** member(s) who hold neither access role? "
            "This includes members with other roles (staff, captains).",
            view=view,
            ephemeral=True,
            wait=True,
        )
        await view.wait()
        if not view.confirmed:
            await message.edit(content="Sync cancelled.", view=None)
            return
        await message.edit(content=f"Giving {role.mention} to {len(missing)} member(s)…", view=None)
        given, failed = await self._hand_out(actor.guild, role, missing, f"/access sync by {actor}")
        async with session_scope(self.bot.session_factory) as session:
            await AccessService(session).record_sync(
                actor.guild.id, given=given, staff_discord_id=actor.id
            )
        logger.info("/access sync by %s: %d given, %d failed", actor.id, given, failed)
        note = f" {failed} failed; check the bot's role position." if failed else ""
        await message.edit(content=f"✅ Gave {role.mention} to {given} member(s).{note}")

    async def _sync_tick(self) -> None:
        """Every few minutes: give the join-time role to members the join
        handler missed (ADR-126). Only members with no other roles, so staff
        and hand-picked roles are never touched; never raises."""
        guild = self.bot.get_guild(self.bot.settings.guild_id)
        if guild is None:
            return
        try:
            async with session_scope(self.bot.session_factory) as session:
                config = await AccessService(session).config(guild.id)
            role_id = config.role_on_join()
            role = guild.get_role(role_id) if role_id else None
            me = guild.me
            if role is None or me is None or role >= me.top_role:
                return
            ignored = await self._bot_managed_role_ids(guild)
            ignored |= {r.id for r in guild.roles if r.managed}
            missing = members_missing_access(
                config, member_roles(guild.members), ignored_role_ids=ignored
            )[:SYNC_BATCH]
            if not missing:
                return
            given, _failed = await self._hand_out(guild, role, missing, "BRAWLISTAN access sync")
            if given:
                async with session_scope(self.bot.session_factory) as session:
                    await AccessService(session).record_sync(
                        guild.id, given=given, staff_discord_id=None
                    )
                logger.info("Access sync gave the join-time role to %d member(s)", given)
        except Exception:
            logger.exception("Access sync failed")

    async def _hand_out(
        self, guild: discord.Guild, role: discord.Role, member_ids: list[int], reason: str
    ) -> tuple[int, int]:
        given = failed = 0
        for member_id in member_ids:
            member = guild.get_member(member_id)
            if member is None:
                continue
            try:
                await member.add_roles(role, reason=reason)
                given += 1
            except discord.HTTPException as exc:
                failed += 1
                logger.warning("Couldn't give the access role to %s: %s", member_id, exc)
        return given, failed

    # --- new members --------------------------------------------------------

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        # Discord holds back roles until a member passes rules screening;
        # on_member_update catches that moment.
        if member.bot or member.pending:
            return
        await self._give_join_role(member)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member) -> None:
        if before.pending and not after.pending and not after.bot:
            await self._give_join_role(after)

    async def _give_join_role(self, member: discord.Member) -> None:
        # Never raises: a failure here (database or Discord) is logged, and
        # the next sync tick catches the member up.
        try:
            async with session_scope(self.bot.session_factory) as session:
                config = await AccessService(session).config(member.guild.id)
            role_id = config.role_on_join()
            if role_id is None:
                return
            role = member.guild.get_role(role_id)
            if role is None:
                logger.warning("Join access role no longer exists; run /access roles")
                return
            if role in member.roles:
                return
            await member.add_roles(role, reason="BRAWLISTAN join access")
        except Exception:
            logger.warning(
                "Couldn't give the join access role to %s; the sync will retry",
                member.id,
                exc_info=True,
            )


async def setup(bot: ShaheenBot) -> None:
    await bot.add_cog(AccessCog(bot))
