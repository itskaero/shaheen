"""Setup/staff permission decisions — docs/DECISIONS.md ADR-010, ADR-036,
ADR-109 (Founder/Admin lead; Moderator is staff; BOT_OWNER_ID always passes).
"""

from bot.checks.permissions import (
    check_setup_authorized,
    check_staff_authorized,
    is_setup_authorized,
    is_staff_authorized,
)
from bot.constants import ROLE_ADMIN, ROLE_FOUNDER, ROLE_MODERATOR, ROLE_PLAYER, ROLE_VERIFIED


class _FakeGuild:
    def __init__(self, owner_id: int) -> None:
        self.owner_id = owner_id


class _FakePermissions:
    def __init__(self, administrator: bool) -> None:
        self.administrator = administrator


class _FakeRole:
    def __init__(self, name: str) -> None:
        self.name = name


class _FakeMember:
    def __init__(
        self, *, id: int, guild: _FakeGuild, administrator: bool, roles: list[str]
    ) -> None:
        self.id = id
        self.guild = guild
        self.guild_permissions = _FakePermissions(administrator)
        self.roles = [_FakeRole(name) for name in roles]


def test_owner_is_authorized() -> None:
    assert is_setup_authorized(is_owner=True, is_administrator=False, role_names=[])


def test_administrator_is_authorized() -> None:
    assert is_setup_authorized(is_owner=False, is_administrator=True, role_names=[])


def test_founder_role_is_authorized() -> None:
    assert is_setup_authorized(
        is_owner=False, is_administrator=False, role_names=[ROLE_FOUNDER.name]
    )


def test_ordinary_member_is_not_authorized() -> None:
    assert not is_setup_authorized(
        is_owner=False, is_administrator=False, role_names=["🦅 SHAHEEN"]
    )


def test_check_setup_authorized_wraps_a_discord_member() -> None:
    guild = _FakeGuild(owner_id=1)
    owner = _FakeMember(id=1, guild=guild, administrator=False, roles=[])
    leader = _FakeMember(id=2, guild=guild, administrator=False, roles=[ROLE_FOUNDER.name])
    regular = _FakeMember(id=3, guild=guild, administrator=False, roles=["🦅 SHAHEEN"])

    assert check_setup_authorized(owner)  # type: ignore[arg-type]
    assert check_setup_authorized(leader)  # type: ignore[arg-type]
    assert not check_setup_authorized(regular)  # type: ignore[arg-type]


def test_admin_runs_setup_but_moderator_does_not() -> None:
    assert is_setup_authorized(is_owner=False, is_administrator=False, role_names=[ROLE_ADMIN.name])
    assert not is_setup_authorized(
        is_owner=False, is_administrator=False, role_names=[ROLE_MODERATOR.name]
    )


def test_every_staff_role_passes_staff_checks() -> None:
    for role in (ROLE_FOUNDER, ROLE_ADMIN, ROLE_MODERATOR):
        assert is_staff_authorized(is_owner=False, is_administrator=False, role_names=[role.name])


def test_player_and_verified_are_not_staff() -> None:
    assert not is_staff_authorized(
        is_owner=False,
        is_administrator=False,
        role_names=[ROLE_PLAYER.name, ROLE_VERIFIED.name],
    )


def test_bot_owner_id_passes_without_any_role() -> None:
    guild = _FakeGuild(owner_id=1)
    bot_owner = _FakeMember(id=42, guild=guild, administrator=False, roles=[])
    assert check_setup_authorized(bot_owner, bot_owner_id=42)  # type: ignore[arg-type]
    assert check_staff_authorized(bot_owner, bot_owner_id=42)  # type: ignore[arg-type]
    assert not check_staff_authorized(bot_owner)  # type: ignore[arg-type]
