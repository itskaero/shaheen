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

# leaderboard() takes a limit; /clanstats needs every member, and the linked
# set is tens, not thousands.
_ALL_MEMBERS = 10_000


def _median(sorted_values: list[int]) -> int | None:
    """Median of an already-sorted list, or None if empty.

    Reported alongside the mean because one Diamond player drags an average
    far more than the clan's typical standing actually moved.
    """
    count = len(sorted_values)
    if count == 0:
        return None
    middle = count // 2
    if count % 2 == 1:
        return sorted_values[middle]
    return round((sorted_values[middle - 1] + sorted_values[middle]) / 2)


@dataclass
class LegendMetaEntry:
    legend_name_key: str
    total_games: int
    total_wins: int
    player_count: int

    @property
    def win_rate(self) -> float:
        return (self.total_wins / self.total_games * 100) if self.total_games else 0.0


@dataclass
class ClanRankContext:
    """Where an arbitrary rating would slot into the clan's ladder.

    `above`/`below` are (player_name, rating) pairs for the nearest ranked
    member on either side, or None at the ends of the ladder.
    """

    would_be_rank: int
    total_ranked: int
    above: tuple[str, int] | None
    below: tuple[str, int] | None


@dataclass
class ClanStats:
    """Clan-wide aggregate over every actively-linked member's latest snapshot."""

    members_ranked: int
    total_games: int
    total_wins: int
    average_rating: int | None
    median_rating: int | None
    highest: tuple[str, int] | None
    tier_counts: list[tuple[str, int]]
    region_counts: list[tuple[str, int]]
    top_legends: list[LegendMetaEntry]

    @property
    def win_rate(self) -> float:
        return (self.total_wins / self.total_games * 100) if self.total_games else 0.0


class ClanService:
    def __init__(self, session: AsyncSession) -> None:
        self._links = MemberPlayerLinkRepository(session)
        self._ranking = RankingSnapshotRepository(session)
        self._awards = MemberAchievementRepository(session)
        self._legends = LegendSnapshotRepository(session)

    async def current_season(self) -> int | None:
        """The Brawlhalla season every ranking view here is scoped to."""
        return await self._ranking.current_season()

    async def leaderboard(
        self, guild_id: int, *, limit: int = 10
    ) -> list[tuple[ShaheenMember, BrawlhallaPlayer, int, RankingSnapshot]]:
        """Actively-linked members with a current-season snapshot, by rating.

        Scoped to the current season (docs/DECISIONS.md ADR-088): Brawlhalla
        wipes ratings at each reset, so a member who has not re-placed yet
        has no current rating and correctly does not appear, rather than
        sitting at the top on last season's number.
        """
        season = await self._ranking.current_season()
        rows: list[tuple[ShaheenMember, BrawlhallaPlayer, int, RankingSnapshot]] = []
        for member, player, discord_id in await self._links.list_active_for_guild(guild_id):
            latest = await self._ranking.get_latest(player.id, season=season)
            if latest is not None:
                rows.append((member, player, discord_id, latest))
        rows.sort(key=lambda row: row[3].rating if row[3].rating is not None else -1, reverse=True)
        return rows[:limit]

    async def rank_context(self, guild_id: int, rating: int) -> ClanRankContext:
        """Where `rating` would slot into the clan's ranked ladder.

        Powers /lookup (docs/DECISIONS.md ADR-083): someone can check any
        Brawlhalla player's standing without linking, and the number is only
        meaningful next to the clan's own — "1720" means little, "would be
        3rd of 11, 40 below Kaero" means something.

        Nothing is written and no link is created; this is a read-only
        comparison against the latest snapshot of every ranked member.
        """
        season = await self._ranking.current_season()
        rated: list[tuple[str, int]] = []
        for _member, player, _discord_id in await self._links.list_active_for_guild(guild_id):
            latest = await self._ranking.get_latest(player.id, season=season)
            if latest is not None and latest.rating is not None:
                rated.append((player.player_name, latest.rating))
        rated.sort(key=lambda row: row[1], reverse=True)

        above: tuple[str, int] | None = None
        below: tuple[str, int] | None = None
        position = len(rated) + 1
        for index, (name, member_rating) in enumerate(rated):
            if member_rating <= rating:
                position = index + 1
                below = (name, member_rating)
                above = rated[index - 1] if index > 0 else None
                break
        else:
            above = rated[-1] if rated else None

        return ClanRankContext(
            would_be_rank=position, total_ranked=len(rated), above=above, below=below
        )

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

    async def clan_stats(self, guild_id: int, *, legend_limit: int = 5) -> ClanStats:
        """Aggregate of the clan's current standing, for /clanstats.

        Same "loop the small set of linked members in Python" shape
        leaderboard() and legend_meta() already use (ADR-068) rather than a
        large SQL aggregate — the member set is tens, not thousands, and
        each member's numbers come from their own latest snapshot row.
        """
        ratings: list[int] = []
        total_games = 0
        total_wins = 0
        highest: tuple[str, int] | None = None
        tier_counts: dict[str, int] = {}
        region_counts: dict[str, int] = {}

        rows = await self.leaderboard(guild_id, limit=_ALL_MEMBERS)
        for _member, player, _discord_id, latest in rows:
            total_games += latest.games
            total_wins += latest.wins
            if latest.tier:
                tier_counts[latest.tier] = tier_counts.get(latest.tier, 0) + 1
            region = latest.region or player.region
            if region:
                region_counts[region] = region_counts.get(region, 0) + 1
            if latest.rating is not None:
                ratings.append(latest.rating)
                if highest is None or latest.rating > highest[1]:
                    highest = (player.player_name, latest.rating)

        ratings.sort()
        average = round(sum(ratings) / len(ratings)) if ratings else None
        median = _median(ratings)

        return ClanStats(
            members_ranked=len(rows),
            total_games=total_games,
            total_wins=total_wins,
            average_rating=average,
            median_rating=median,
            highest=highest,
            tier_counts=sorted(tier_counts.items(), key=lambda item: item[1], reverse=True),
            region_counts=sorted(region_counts.items(), key=lambda item: item[1], reverse=True),
            top_legends=await self.legend_meta(guild_id, limit=legend_limit),
        )
