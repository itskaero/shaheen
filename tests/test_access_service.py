"""Join access: join role, approved role, approval (docs/DECISIONS.md ADR-123)."""

from __future__ import annotations

from dataclasses import dataclass, field

import discord
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from bot.cogs.access import role_problem
from core.exceptions import ConflictError
from database.repositories.audit_log_repository import AuditLogRepository
from services.access_service import (
    AccessConfig,
    AccessService,
    MemberRoles,
    members_missing_access,
    plan_approval,
)

GUILD = 1
JOIN, APPROVED = 100, 200


def test_the_role_given_on_join_follows_the_switch() -> None:
    assert AccessConfig(JOIN, APPROVED, approval_enabled=True).role_on_join() == JOIN
    assert AccessConfig(JOIN, APPROVED, approval_enabled=False).role_on_join() == APPROVED
    assert AccessConfig(JOIN, None, approval_enabled=False).role_on_join() is None
    assert AccessConfig().role_on_join() is None


def test_warnings_say_what_the_mode_is_missing() -> None:
    assert AccessConfig(JOIN, APPROVED, approval_enabled=True).warnings() == []
    assert AccessConfig(None, APPROVED).warnings() == []
    assert len(AccessConfig(None, None, approval_enabled=True).warnings()) == 2
    assert len(AccessConfig(JOIN, None).warnings()) == 1


def test_approval_swaps_the_join_role_for_the_approved_role() -> None:
    config = AccessConfig(JOIN, APPROVED, approval_enabled=True)
    change = plan_approval(config, {JOIN, 5})
    assert (change.add, change.remove) == (APPROVED, JOIN)
    # Already approved: nothing to do. Approved but still waiting: just tidy up.
    assert plan_approval(config, {APPROVED}).is_noop
    assert (
        plan_approval(config, {APPROVED, JOIN}).add,
        plan_approval(config, {APPROVED, JOIN}).remove,
    ) == (
        None,
        JOIN,
    )
    with pytest.raises(ConflictError):
        plan_approval(AccessConfig(JOIN, None, True), {JOIN})


async def test_set_roles_then_turn_approval_on_and_off(session: AsyncSession) -> None:
    service = AccessService(session)
    assert await service.config(GUILD) == AccessConfig()

    with pytest.raises(ConflictError):  # no roles yet
        await service.set_enabled(GUILD, enabled=True, staff_discord_id=9)
    with pytest.raises(ConflictError):  # one role can't be both
        await service.set_roles(GUILD, join_role_id=JOIN, approved_role_id=JOIN, staff_discord_id=9)

    await service.set_roles(GUILD, join_role_id=JOIN, approved_role_id=APPROVED, staff_discord_id=9)
    on = await service.set_enabled(GUILD, enabled=True, staff_discord_id=9)
    assert on == AccessConfig(JOIN, APPROVED, approval_enabled=True)
    assert await service.config(GUILD) == on

    with pytest.raises(ConflictError):  # can't clear a role while approval needs it
        await service.set_roles(
            GUILD, join_role_id=None, approved_role_id=APPROVED, staff_discord_id=9
        )

    off = await service.set_enabled(GUILD, enabled=False, staff_discord_id=9)
    assert off.role_on_join() == APPROVED
    cleared = await service.set_roles(
        GUILD, join_role_id=None, approved_role_id=None, staff_discord_id=9
    )
    assert cleared == AccessConfig()

    actions = [entry.action for entry in await AuditLogRepository(session).list_recent(GUILD)]
    assert {"access.roles", "access.approval_on", "access.approval_off"} <= set(actions)


# --- which roles may be handed out -------------------------------------------


@dataclass
class _Role:
    id: int
    position: int
    managed: bool = False
    default: bool = False
    permissions: discord.Permissions = field(default_factory=discord.Permissions.none)

    @property
    def mention(self) -> str:
        return f"<@&{self.id}>"

    def is_default(self) -> bool:
        return self.default

    def __ge__(self, other: _Role) -> bool:
        return self.position >= other.position


@dataclass
class _Guild:
    owner_id: int = 1


@dataclass
class _Member:
    id: int
    top_role: _Role
    guild: _Guild = field(default_factory=_Guild)


BOT_TOP = _Role(id=1, position=10)
MOD = _Member(id=7, top_role=_Role(id=2, position=8))


def _problem(
    role: _Role, actor: _Member = MOD, managed: frozenset[int] = frozenset()
) -> str | None:
    return role_problem(role, bot_top=BOT_TOP, actor=actor, bot_managed=managed)  # type: ignore[arg-type]


def test_an_ordinary_member_role_is_allowed() -> None:
    assert (
        _problem(_Role(id=50, position=3, permissions=discord.Permissions(send_messages=True)))
        is None
    )


def test_roles_that_must_never_be_handed_out() -> None:
    assert "everyone" in (_problem(_Role(id=GUILD, position=0, default=True)) or "")
    assert "integration" in (_problem(_Role(id=51, position=3, managed=True)) or "")
    bot_managed = _problem(_Role(id=52, position=3), managed=frozenset({52}))
    assert "linked Brawlhalla account" in (bot_managed or "")
    admin = _Role(id=53, position=3, permissions=discord.Permissions(administrator=True))
    assert "staff permissions" in (_problem(admin) or "")
    kick = _Role(id=54, position=3, permissions=discord.Permissions(kick_members=True))
    assert "kick members" in (_problem(kick) or "")


def test_role_hierarchy_is_respected() -> None:
    assert "bot's role" in (_problem(_Role(id=55, position=10)) or "")
    # A moderator can't hand out a role at or above their own...
    assert "below your own" in (_problem(_Role(id=56, position=8)) or "")
    # ...but the server owner can, as long as the bot can.
    owner = _Member(id=1, top_role=_Role(id=3, position=5))
    assert _problem(_Role(id=56, position=8), actor=owner) is None


# --- catching up members the join handler missed (ADR-126) ------------------


PLAYER, STAFF_ROLE = 300, 400


def _m(discord_id: int, *roles: int, bot: bool = False, pending: bool = False) -> MemberRoles:
    return MemberRoles(discord_id, frozenset(roles), is_bot=bot, pending=pending)


def test_sync_gives_the_join_time_role_to_roleless_members_only() -> None:
    off = AccessConfig(JOIN, APPROVED, approval_enabled=False)
    members = [
        _m(1),  # missed on join
        _m(2, APPROVED),  # fine
        _m(3, PLAYER),  # only the bot's own mirror role: still missed
        _m(4, STAFF_ROLE),  # hand-picked role: left alone automatically
        _m(5, bot=True),
        _m(6, pending=True),  # still in rules screening
        _m(7, JOIN),  # waiting for approval from earlier
    ]
    assert members_missing_access(off, members, ignored_role_ids={PLAYER}) == [1, 3]
    # /access sync includes members with other roles.
    assert members_missing_access(off, members, ignored_role_ids={PLAYER}, everyone=True) == [
        1,
        3,
        4,
    ]


def test_sync_follows_the_switch_and_does_nothing_unconfigured() -> None:
    on = AccessConfig(JOIN, APPROVED, approval_enabled=True)
    assert members_missing_access(on, [_m(1), _m(2, APPROVED)]) == [1]
    assert members_missing_access(AccessConfig(), [_m(1)]) == []


async def test_sync_is_audited(session: AsyncSession) -> None:
    await AccessService(session).record_sync(GUILD, given=3, staff_discord_id=None)
    entries = await AuditLogRepository(session).list_recent(GUILD)
    assert entries[0].action == "access.sync"
