"""Which members should hold the Player and Verified roles (docs/DECISIONS.md
ADR-109).

The only roles the bot assigns since BRAWLISTAN. Both mirror the database:
Player = an active Brawlhalla link (/link or a website claim), Verified =
that link was confirmed by staff (/verify). Pure, so the rule is testable
without Discord and reusable by the website API.
"""

from __future__ import annotations

from collections.abc import Mapping, Set
from dataclasses import dataclass, field


@dataclass(frozen=True)
class RoleDiff:
    grant: frozenset[int] = field(default_factory=frozenset)
    revoke: frozenset[int] = field(default_factory=frozenset)

    @property
    def is_noop(self) -> bool:
        return not self.grant and not self.revoke


@dataclass(frozen=True)
class AccountRolesPlan:
    player: RoleDiff
    verified: RoleDiff


def _diff(should_hold: Set[int], holders: Set[int], present: Set[int]) -> RoleDiff:
    # Only members actually in the guild can be granted; anyone holding the
    # role without qualifying loses it.
    return RoleDiff(
        grant=frozenset((should_hold & present) - holders),
        revoke=frozenset(holders - should_hold),
    )


def plan_account_roles(
    *,
    accounts: Mapping[int, bool],
    player_holders: Set[int],
    verified_holders: Set[int],
    present: Set[int],
) -> AccountRolesPlan:
    """`accounts` maps Discord id -> verified? for every active link."""
    linked = set(accounts)
    verified = {discord_id for discord_id, is_verified in accounts.items() if is_verified}
    return AccountRolesPlan(
        player=_diff(linked, player_holders, present),
        verified=_diff(verified, verified_holders, present),
    )
