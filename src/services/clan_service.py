"""Read-only clan-wide queries behind /leaderboard, /achievements, /history."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from database.models.achievement import Achievement
from database.models.brawlhalla_player import BrawlhallaPlayer
from database.models.ranking_snapshot import RankingSnapshot
from database.models.shaheen_member import ShaheenMember
from database.repositories.member_achievement_repository import MemberAchievementRepository
from database.repositories.member_player_link_repository import MemberPlayerLinkRepository
from database.repositories.ranking_snapshot_repository import RankingSnapshotRepository


class ClanService:
    def __init__(self, session: AsyncSession) -> None:
        self._links = MemberPlayerLinkRepository(session)
        self._ranking = RankingSnapshotRepository(session)
        self._awards = MemberAchievementRepository(session)

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
