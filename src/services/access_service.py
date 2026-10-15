"""Join access (docs/DECISIONS.md ADR-123): which role a new member gets,
and approval.

Staff pick two roles and flip one switch:
- approval **off**: a new member gets the approved role on join, so they're
  straight in;
- approval **on**: a new member gets the join role (the "not approved yet"
  role), and staff run /approval to swap it for the approved role.

What each role can see is the owner's channel setup, never the bot's
(ADR-109). The rules here are Discord-agnostic: role ids in, decisions out.
"""

from __future__ import annotations

from collections.abc import Iterable, Set
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import ConflictError
from database.repositories.audit_log_repository import AuditLogRepository
from database.repositories.guild_settings_repository import GuildSettingsRepository


@dataclass(frozen=True)
class AccessConfig:
    join_role_id: int | None = None
    approved_role_id: int | None = None
    approval_enabled: bool = False

    def role_on_join(self) -> int | None:
        """The role a member gets when they join (or finish Discord's rules
        screening), if any."""
        return self.join_role_id if self.approval_enabled else self.approved_role_id

    def warnings(self) -> list[str]:
        """What's missing for the current mode to work."""
        if self.approval_enabled:
            missing = []
            if self.join_role_id is None:
                missing.append("Approval is on but no join role is set: new members get no role.")
            if self.approved_role_id is None:
                missing.append("No approved role is set: /approval has nothing to give.")
            return missing
        if self.approved_role_id is None:
            return ["No approved role is set: new members get no role on join."]
        return []


@dataclass(frozen=True)
class ApprovalChange:
    """The role swap /approval makes for one member."""

    add: int | None
    remove: int | None

    @property
    def is_noop(self) -> bool:
        return self.add is None and self.remove is None


@dataclass(frozen=True)
class MemberRoles:
    """What the access sync needs to know about one member (ADR-126)."""

    discord_id: int
    role_ids: frozenset[int]
    is_bot: bool = False
    pending: bool = False


def members_missing_access(
    config: AccessConfig,
    members: Iterable[MemberRoles],
    *,
    ignored_role_ids: Set[int] = frozenset(),
    everyone: bool = False,
) -> list[int]:
    """Members who should hold `config.role_on_join()` but hold neither
    access role (ADR-126): someone who joined while the bot was offline, or
    whose join-time role edit failed.

    By default only members with no other roles count (besides
    `ignored_role_ids`, the bot's own Player/Verified mirrors), so the
    automatic sync never touches staff or anyone given roles by hand.
    `everyone=True` (/access sync) includes them too. Bots and members
    still in Discord's rules screening are always skipped.
    """
    role_id = config.role_on_join()
    if role_id is None:
        return []
    access = {r for r in (config.join_role_id, config.approved_role_id) if r is not None}
    missing = []
    for member in members:
        if member.is_bot or member.pending or member.role_ids & access:
            continue
        if not everyone and member.role_ids - ignored_role_ids:
            continue
        missing.append(member.discord_id)
    return missing


def plan_approval(config: AccessConfig, held_role_ids: set[int]) -> ApprovalChange:
    """Give the approved role and take the join role, skipping what's
    already done. Requires an approved role."""
    if config.approved_role_id is None:
        raise ConflictError("No approved role is set. Staff can set one with /access roles.")
    add = None if config.approved_role_id in held_role_ids else config.approved_role_id
    remove = config.join_role_id if config.join_role_id in held_role_ids else None
    return ApprovalChange(add=add, remove=remove)


class AccessService:
    def __init__(self, session: AsyncSession) -> None:
        self._settings = GuildSettingsRepository(session)
        self._audit = AuditLogRepository(session)

    async def config(self, guild_id: int) -> AccessConfig:
        settings = await self._settings.get(guild_id)
        if settings is None:
            return AccessConfig()
        return AccessConfig(
            join_role_id=settings.join_role_id,
            approved_role_id=settings.approved_role_id,
            approval_enabled=settings.approval_enabled,
        )

    async def set_roles(
        self,
        guild_id: int,
        *,
        join_role_id: int | None,
        approved_role_id: int | None,
        staff_discord_id: int,
    ) -> AccessConfig:
        """Set both roles (None clears one)."""
        current = await self.config(guild_id)
        if join_role_id is not None and join_role_id == approved_role_id:
            raise ConflictError("The join role and the approved role must be different roles.")
        if current.approval_enabled and (join_role_id is None or approved_role_id is None):
            raise ConflictError(
                "Approval is on, so both roles are needed. Turn it off first with "
                "/access approval enabled:False."
            )
        updated = AccessConfig(join_role_id, approved_role_id, current.approval_enabled)
        await self._save(guild_id, updated)
        await self._audit.add(
            guild_id=guild_id,
            action="access.roles",
            source="discord",
            actor_discord_id=staff_discord_id,
            subject="join and approved roles",
            detail={"join_role_id": join_role_id, "approved_role_id": approved_role_id},
        )
        return updated

    async def set_enabled(
        self, guild_id: int, *, enabled: bool, staff_discord_id: int
    ) -> AccessConfig:
        current = await self.config(guild_id)
        if enabled and (current.join_role_id is None or current.approved_role_id is None):
            raise ConflictError(
                "Set both roles first with /access roles: the join role new members wait "
                "in, and the approved role that lets them in."
            )
        updated = AccessConfig(current.join_role_id, current.approved_role_id, enabled)
        await self._save(guild_id, updated)
        await self._audit.add(
            guild_id=guild_id,
            action="access.approval_on" if enabled else "access.approval_off",
            source="discord",
            actor_discord_id=staff_discord_id,
            subject="approval " + ("on" if enabled else "off"),
        )
        return updated

    async def record_sync(self, guild_id: int, *, given: int, staff_discord_id: int | None) -> None:
        """Audit a catch-up pass that handed out the join-time role (ADR-126)."""
        await self._audit.add(
            guild_id=guild_id,
            action="access.sync",
            source="discord",
            actor_discord_id=staff_discord_id,
            subject=f"join-time role given to {given} member(s)",
            detail={"given": given},
        )

    async def record_approval(
        self, guild_id: int, *, member_discord_id: int, staff_discord_id: int
    ) -> None:
        await self._audit.add(
            guild_id=guild_id,
            action="access.approve",
            source="discord",
            actor_discord_id=staff_discord_id,
            subject="member approved",
            detail={"member_discord_id": member_discord_id},
        )

    async def _save(self, guild_id: int, config: AccessConfig) -> None:
        await self._settings.set_access(
            guild_id,
            join_role_id=config.join_role_id,
            approved_role_id=config.approved_role_id,
            approval_enabled=config.approval_enabled,
        )
