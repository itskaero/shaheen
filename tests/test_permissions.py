"""Setup permission decisions — docs/DECISIONS.md ADR-010."""

from bot.checks.permissions import check_setup_authorized, is_setup_authorized
from bot.constants import ROLE_LEADER


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


def test_shaheen_leader_role_is_authorized() -> None:
    assert is_setup_authorized(
        is_owner=False, is_administrator=False, role_names=[ROLE_LEADER.name]
    )


def test_ordinary_member_is_not_authorized() -> None:
    assert not is_setup_authorized(
        is_owner=False, is_administrator=False, role_names=["🦅 SHAHEEN"]
    )


def test_check_setup_authorized_wraps_a_discord_member() -> None:
    guild = _FakeGuild(owner_id=1)
    owner = _FakeMember(id=1, guild=guild, administrator=False, roles=[])
    leader = _FakeMember(id=2, guild=guild, administrator=False, roles=[ROLE_LEADER.name])
    regular = _FakeMember(id=3, guild=guild, administrator=False, roles=["🦅 SHAHEEN"])

    assert check_setup_authorized(owner)  # type: ignore[arg-type]
    assert check_setup_authorized(leader)  # type: ignore[arg-type]
    assert not check_setup_authorized(regular)  # type: ignore[arg-type]
