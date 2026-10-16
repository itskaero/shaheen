"""Founders and Admins on the website's Founding Team page (docs/DECISIONS.md ADR-135).

Mirrors the holders of the provisioned Founder and Admin roles (ADR-109) into
the staff directory every 30 minutes and whenever a holder's roles, server
nickname or avatar change. The bot only reads roles here; it never edits them.
Avatars are downloaded small (128 px) and stored, so the public page never
links a Discord CDN URL (which carries the user id). Rules live in
services/staff_service.py.
"""

from __future__ import annotations

import logging

import discord
from discord.ext import commands, tasks

from bot.client import ShaheenBot
from bot.constants import ROLE_ADMIN, ROLE_FOUNDER, RoleSpec
from database.models.provisioned_resource import ResourceType
from database.repositories.provisioned_resource_repository import ProvisionedResourceRepository
from database.session import session_scope
from services.staff_service import StaffHolder, StaffService

logger = logging.getLogger(__name__)

SYNC_MINUTES = 30
# Highest first: a member holding both is listed once, as a Founder.
ROLES: tuple[tuple[str, RoleSpec], ...] = (("founder", ROLE_FOUNDER), ("admin", ROLE_ADMIN))


class StaffDirectoryCog(commands.Cog):
    def __init__(self, bot: ShaheenBot) -> None:
        self.bot = bot
        self.sync_loop = tasks.loop(minutes=SYNC_MINUTES)(self._sync_tick)

    async def cog_load(self) -> None:
        self.sync_loop.before_loop(self.bot.wait_until_ready)
        self.sync_loop.start()

    async def cog_unload(self) -> None:
        self.sync_loop.cancel()

    async def _roles(self, guild: discord.Guild) -> list[tuple[str, discord.Role]]:
        """The provisioned Founder/Admin roles, falling back to their names."""
        found: list[tuple[str, discord.Role]] = []
        async with session_scope(self.bot.session_factory) as session:
            repo = ProvisionedResourceRepository(session)
            for key, spec in ROLES:
                resource = await repo.get(
                    guild_id=guild.id, resource_type=ResourceType.ROLE, logical_key=spec.logical_key
                )
                role = guild.get_role(resource.discord_id) if resource is not None else None
                role = role or discord.utils.get(guild.roles, name=spec.name)
                if role is not None:
                    found.append((key, role))
        return found

    @staticmethod
    def _avatar_key(member: discord.Member) -> str | None:
        """Discord's hash of the avatar shown in the server; None for a default one."""
        if member.guild_avatar is None and member.avatar is None:
            return None
        return member.display_avatar.key

    async def _sync(self, guild: discord.Guild) -> None:
        roles = await self._roles(guild)
        holders: dict[int, StaffHolder] = {}
        members: dict[int, discord.Member] = {}
        for key, role in roles:
            ordered = sorted(
                (m for m in role.members if not m.bot),
                key=lambda m: m.joined_at or discord.utils.utcnow(),
            )
            for position, member in enumerate(ordered):
                if member.id in holders:  # already listed under a higher role
                    continue
                members[member.id] = member
                holders[member.id] = StaffHolder(
                    discord_id=member.id,
                    display_name=member.display_name,
                    role=key,
                    position=position,
                    avatar_key=self._avatar_key(member),
                )
        async with session_scope(self.bot.session_factory) as session:
            result = await StaffService(session).sync(guild.id, list(holders.values()))
        stored = 0
        for discord_id in result.avatars_needed:
            member = members[discord_id]
            avatar_key = holders[discord_id].avatar_key
            if avatar_key is None:
                continue
            try:
                data = await member.display_avatar.replace(size=128, format="webp").read()
            except (discord.HTTPException, ValueError) as exc:
                logger.warning("Staff avatar download failed: %s", type(exc).__name__)
                continue
            async with session_scope(self.bot.session_factory) as session:
                stored += await StaffService(session).set_avatar(
                    guild.id, discord_id, key=key, data=data
                )
        if result.changed or stored:
            logger.info(
                "Staff sync: %d added, %d updated, %d removed, %d avatars",
                result.added,
                result.updated,
                result.deactivated,
                stored,
            )

    async def _sync_tick(self) -> None:
        guild = self.bot.get_guild(self.bot.settings.guild_id)
        if guild is None:
            return
        try:
            await self._sync(guild)
        except Exception:
            logger.exception("Staff sync failed")

    async def _is_staff(self, member: discord.Member) -> bool:
        ids = {role.id for _key, role in await self._roles(member.guild)}
        return any(r.id in ids for r in member.roles)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member) -> None:
        if after.guild.id != self.bot.settings.guild_id:
            return
        if (before.roles, before.display_name, before.display_avatar) == (
            after.roles,
            after.display_name,
            after.display_avatar,
        ):
            return
        try:
            if await self._is_staff(before) or await self._is_staff(after):
                await self._sync(after.guild)
        except Exception:
            logger.exception("Staff sync after a member update failed")

    @commands.Cog.listener()
    async def on_user_update(self, before: discord.User, after: discord.User) -> None:
        """A global name or avatar change, which on_member_update doesn't report."""
        if (before.display_name, before.display_avatar) == (
            after.display_name,
            after.display_avatar,
        ):
            return
        guild = self.bot.get_guild(self.bot.settings.guild_id)
        member = guild.get_member(after.id) if guild is not None else None
        try:
            if member is not None and await self._is_staff(member):
                await self._sync(guild)  # type: ignore[arg-type]
        except Exception:
            logger.exception("Staff sync after a user update failed")


async def setup(bot: ShaheenBot) -> None:
    await bot.add_cog(StaffDirectoryCog(bot))
