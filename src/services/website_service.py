"""Read-only queries for the public website/API (docs/DECISIONS.md ADR-042).

Discord-agnostic, like every other service (docs/ARCHITECTURE.md). Never
reads or returns Discord identity — see ADR-040: only BrawlhallaPlayer
identity is public-facing here.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from core.brand import MOTTO, NAME, TAGLINE
from database.models.achievement import Achievement
from database.models.brawlhalla_player import BrawlhallaPlayer
from database.models.ranking_snapshot import RankingSnapshot
from database.repositories.brawlhalla_player_repository import BrawlhallaPlayerRepository
from database.repositories.member_achievement_repository import MemberAchievementRepository
from database.repositories.member_player_link_repository import MemberPlayerLinkRepository
from database.repositories.ranking_snapshot_repository import RankingSnapshotRepository
from database.repositories.shaheen_member_repository import ShaheenMemberRepository


@dataclass
class ClanInfo:
    name: str
    motto: str
    tagline: str
    member_count: int


@dataclass
class LeaderboardEntry:
    player: BrawlhallaPlayer
    snapshot: RankingSnapshot


@dataclass
class PlayerProfile:
    player: BrawlhallaPlayer
    latest_ranking: RankingSnapshot | None
    achievements: list[tuple[Achievement, datetime]]


class WebsiteService:
    def __init__(self, session: AsyncSession) -> None:
        self._links = MemberPlayerLinkRepository(session)
        self._members = ShaheenMemberRepository(session)
        self._players = BrawlhallaPlayerRepository(session)
        self._ranking = RankingSnapshotRepository(session)
        self._awards = MemberAchievementRepository(session)

    async def get_clan_info(self, guild_id: int) -> ClanInfo:
        member_count = await self._members.count_for_guild(guild_id)
        return ClanInfo(name=NAME, motto=MOTTO, tagline=TAGLINE, member_count=member_count)

    async def get_leaderboard(self, guild_id: int, *, limit: int = 10) -> list[LeaderboardEntry]:
        entries: list[LeaderboardEntry] = []
        for _member, player, _discord_id in await self._links.list_active_for_guild(guild_id):
            latest = await self._ranking.get_latest(player.id)
            if latest is not None:
                entries.append(LeaderboardEntry(player=player, snapshot=latest))
        entries.sort(
            key=lambda entry: entry.snapshot.rating if entry.snapshot.rating is not None else -1,
            reverse=True,
        )
        return entries[:limit]

    async def get_player_profile(self, brawlhalla_player_id: int) -> PlayerProfile | None:
        player = await self._players.get_by_brawlhalla_id(brawlhalla_player_id)
        if player is None:
            return None

        latest = await self._ranking.get_latest(player.id)

        achievements: list[tuple[Achievement, datetime]] = []
        active_link = await self._links.get_active_by_player(player.id)
        if active_link is not None:
            achievements = await self._awards.list_with_details(active_link.shaheen_member_id)

        return PlayerProfile(player=player, latest_ranking=latest, achievements=achievements)

    async def get_player_history(
        self, brawlhalla_player_id: int, *, limit: int = 10
    ) -> list[RankingSnapshot] | None:
        player = await self._players.get_by_brawlhalla_id(brawlhalla_player_id)
        if player is None:
            return None
        return await self._ranking.list_recent(player.id, limit=limit)
