"""Player/Verified role mirroring (docs/DECISIONS.md ADR-109)."""

from __future__ import annotations

from services.account_roles import plan_account_roles


def test_linked_members_get_player_and_verified_links_get_verified() -> None:
    plan = plan_account_roles(
        accounts={1: False, 2: True},
        player_holders=set(),
        verified_holders=set(),
        present={1, 2},
    )
    assert plan.player.grant == {1, 2}
    assert plan.verified.grant == {2}
    assert not plan.player.revoke and not plan.verified.revoke


def test_unlinked_or_unverified_holders_lose_the_role() -> None:
    plan = plan_account_roles(
        accounts={1: False},
        player_holders={1, 3},
        verified_holders={1},
        present={1, 3},
    )
    assert plan.player.revoke == {3}
    assert plan.verified.revoke == {1}


def test_members_not_in_the_guild_are_not_granted() -> None:
    plan = plan_account_roles(
        accounts={1: True, 9: True}, player_holders=set(), verified_holders=set(), present={1}
    )
    assert plan.player.grant == {1}
    assert plan.verified.grant == {1}


def test_nothing_to_do_when_roles_already_match() -> None:
    plan = plan_account_roles(
        accounts={1: True, 2: False},
        player_holders={1, 2},
        verified_holders={1},
        present={1, 2},
    )
    assert plan.player.is_noop
    assert plan.verified.is_noop
