"""Scheduled snapshot orchestration — Discord-agnostic (docs/ARCHITECTURE.md).

Fetches live Brawlhalla data for every actively-linked member of a guild,
persists RankingSnapshot/LegendSnapshot rows, awards newly-earned
achievements, and returns anything worth announcing (a new achievement or
a new career-peak rating). bot/cogs/clan.py decides where/how to post that
(docs/DECISIONS.md ADR-032) — this module never touches Discord.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from database.models.brawlhalla_player import BrawlhallaPlayer
from database.models.legend_snapshot import LegendSnapshot
from database.models.ranking_snapshot import RankingSnapshot
from database.models.shaheen_member import ShaheenMember
from database.repositories.achievement_repository import AchievementRepository
from database.repositories.legend_snapshot_repository import LegendSnapshotRepository
from database.repositories.member_achievement_repository import MemberAchievementRepository
from database.repositories.member_player_link_repository import MemberPlayerLinkRepository
from database.repositories.ranking_snapshot_repository import RankingSnapshotRepository
from integrations.brawlhalla.errors import BrawlhallaAPIError
from integrations.brawlhalla.service import BrawlhallaService
from services.achievements import AchievementDef, evaluate_snapshot_achievements

logger = logging.getLogger(__name__)


@dataclass
class Announcement:
    member: ShaheenMember
    player: BrawlhallaPlayer
    discord_id: int
    achievement: AchievementDef | None = None
    new_peak_rating: int | None = None


@dataclass
class SnapshotRunResult:
    members_processed: int = 0
    errors: list[str] = field(default_factory=list)
    announcements: list[Announcement] = field(default_factory=list)


class SnapshotService:
    def __init__(self, session: AsyncSession, brawlhalla: BrawlhallaService) -> None:
        self._session = session
        self._brawlhalla = brawlhalla
        self._links = MemberPlayerLinkRepository(session)
        self._ranking = RankingSnapshotRepository(session)
        self._legends = LegendSnapshotRepository(session)
        self._achievements = AchievementRepository(session)
        self._awards = MemberAchievementRepository(session)

    async def run_for_guild(self, guild_id: int) -> SnapshotRunResult:
        result = SnapshotRunResult()
        for member, player, discord_id in await self._links.list_active_for_guild(guild_id):
            try:
                await self._snapshot_one(member, player, discord_id, result)
                result.members_processed += 1
            except BrawlhallaAPIError as exc:
                logger.warning(
                    "Snapshot failed for player %s: %s", player.brawlhalla_player_id, exc
                )
                result.errors.append(f"{player.player_name}: Brawlhalla API error")
        return result

    async def _snapshot_one(
        self,
        member: ShaheenMember,
        player: BrawlhallaPlayer,
        discord_id: int,
        result: SnapshotRunResult,
    ) -> None:
        stats = await self._brawlhalla.get_stats(player.brawlhalla_player_id)
        ranked = await self._brawlhalla.get_ranked(player.brawlhalla_player_id)
        captured_at = datetime.now(UTC)

        previous = await self._ranking.get_latest(player.id)

        await self._ranking.add(
            RankingSnapshot(
                brawlhalla_player_id=player.id,
                captured_at=captured_at,
                rating=ranked.rating if ranked else None,
                peak_rating=ranked.peak_rating if ranked else None,
                tier=ranked.tier if ranked else None,
                wins=ranked.wins if ranked else 0,
                games=ranked.games if ranked else 0,
                region=(ranked.region if ranked else None) or player.region,
                global_rank=ranked.global_rank if ranked else None,
            )
        )

        if stats.legends:
            await self._legends.add_all(
                [
                    LegendSnapshot(
                        brawlhalla_player_id=player.id,
                        captured_at=captured_at,
                        legend_id=legend.legend_id,
                        legend_name_key=legend.legend_name_key,
                        games=legend.games,
                        wins=legend.wins,
                        kos=legend.kos,
                        damagedealt=legend.damagedealt,
                        falls=legend.falls,
                    )
                    for legend in stats.legends
                ]
            )

        if (
            ranked is not None
            and ranked.peak_rating is not None
            and previous is not None
            and previous.peak_rating is not None
            and ranked.peak_rating > previous.peak_rating
        ):
            result.announcements.append(
                Announcement(
                    member=member,
                    player=player,
                    discord_id=discord_id,
                    new_peak_rating=ranked.peak_rating,
                )
            )

        await self._award_achievements(
            member, player, discord_id, stats.games, ranked.tier if ranked else None, result
        )

    async def _award_achievements(
        self,
        member: ShaheenMember,
        player: BrawlhallaPlayer,
        discord_id: int,
        games: int,
        tier: str | None,
        result: SnapshotRunResult,
    ) -> None:
        already_earned = await self._awards.list_earned_keys(member.id)
        newly_earned = evaluate_snapshot_achievements(
            games=games, ranked_tier=tier, already_earned=already_earned
        )
        for achievement_def in newly_earned:
            catalog_row = await self._achievements.get_by_key(achievement_def.key)
            if catalog_row is None:
                logger.warning(
                    "Achievement %r earned but missing from catalog — run migrations?",
                    achievement_def.key,
                )
                continue
            awarded = await self._awards.award(
                shaheen_member_id=member.id, achievement_id=catalog_row.id
            )
            if awarded is not None:
                result.announcements.append(
                    Announcement(
                        member=member,
                        player=player,
                        discord_id=discord_id,
                        achievement=achievement_def,
                    )
                )
