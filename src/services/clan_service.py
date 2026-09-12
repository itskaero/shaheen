"""Read-only clan-wide queries behind /leaderboard, /achievements, /history,
/legendmeta.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from database.models.achievement import Achievement
from database.models.brawlhalla_player import BrawlhallaPlayer
from database.models.ranking_snapshot import RankingSnapshot
from database.models.shaheen_member import ShaheenMember
from database.repositories.legend_snapshot_repository import LegendSnapshotRepository
from database.repositories.member_achievement_repository import MemberAchievementRepository
from database.repositories.member_player_link_repository import MemberPlayerLinkRepository
from database.repositories.ranking_snapshot_repository import RankingSnapshotRepository

# Below this many combined games clan-wide, a Legend's win rate is too
# noisy to be a meaningful "meta" signal (docs/DECISIONS.md ADR-068).
_MIN_GAMES_FOR_LEGEND_META = 20


@dataclass
class LegendMetaEntry:
    legend_name_key: str
    total_games: int
    total_wins: int
    player_count: int

    @property
    def win_rate(self) -> float:
        return (self.total_wins / self.total_games * 100) if self.total_games else 0.0


class ClanService:
    def __init__(self, session: AsyncSession) -> None:
        self._links = MemberPlayerLinkRepository(session)
        self._ranking = RankingSnapshotRepository(session)
        self._awards = MemberAchievementRepository(session)
        self._legends = LegendSnapshotRepository(session)

    async def leaderboard(
        self, guild_id: int, *, limit: int = 10
    ) -> list[tuple[ShaheenMember, BrawlhallaPlayer, int, RankingSnapshot]]:
        """Actively-linked members with a snapshot, ranked by current rating."""
        rows: list[tuple[ShaheenMember, BrawlhallaPlayer, int, RankingSnapshot]] = []
        for member, player, discord_id in await self._links.list_active_for_guild(guild_id):
            latest = await self._ranking.get_latest(player.id)
            if latest is not None:
                rows.append((member, player, discord_id, latest))
        rows.sort(key=lambda row: row[3].rating if row[3].rating is not None else -1, reverse=True)
        return rows[:limit]

    async def history(self, player_id: int, *, limit: int = 10) -> list[RankingSnapshot]:
        """`player_id` is BrawlhallaPlayer.id (internal PK), not the external Brawlhalla ID."""
        return await self._ranking.list_recent(player_id, limit=limit)

    async def achievements_for_member(
        self, shaheen_member_id: int
    ) -> list[tuple[Achievement, datetime]]:
        return await self._awards.list_with_details(shaheen_member_id)

    async def legend_meta(self, guild_id: int, *, limit: int = 10) -> list[LegendMetaEntry]:
        """Clan-wide Legend popularity/win-rate, aggregated from every
        actively-linked member's latest per-legend snapshot — same
        "loop the small set of linked members in Python" shape
        leaderboard() already uses rather than one large SQL aggregate
        (docs/DECISIONS.md ADR-068).
        """
        totals: dict[str, LegendMetaEntry] = {}
        for _member, player, _discord_id in await self._links.list_active_for_guild(guild_id):
            for snapshot in await self._legends.list_latest_per_legend(player.id):
                entry = totals.setdefault(
                    snapshot.legend_name_key,
                    LegendMetaEntry(
                        legend_name_key=snapshot.legend_name_key,
                        total_games=0,
                        total_wins=0,
                        player_count=0,
                    ),
                )
                entry.total_games += snapshot.games
                entry.total_wins += snapshot.wins
                entry.player_count += 1

        entries = [e for e in totals.values() if e.total_games >= _MIN_GAMES_FOR_LEGEND_META]
        entries.sort(key=lambda e: e.total_games, reverse=True)
        return entries[:limit]
