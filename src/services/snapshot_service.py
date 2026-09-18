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
from database.repositories.legend_snapshot_repository import LegendSnapshotRepository
from database.repositories.member_player_link_repository import MemberPlayerLinkRepository
from database.repositories.ranking_snapshot_repository import RankingSnapshotRepository
from integrations.brawlhalla.errors import BrawlhallaAPIError
from integrations.brawlhalla.models import PlayerRankedResponse, PlayerStatsResponse
from integrations.brawlhalla.service import BrawlhallaService
from services.achievement_service import AchievementService
from services.achievements import (
    AchievementDef,
    evaluate_snapshot_achievements,
    evaluate_tenure_achievements,
    tier_index,
)

logger = logging.getLogger(__name__)

# /refresh is a member-triggered snapshot, so it hits the Brawlhalla API
# outside the scheduled loop. This floor keeps a member spamming the command
# from turning into upstream request volume (docs/DECISIONS.md ADR-084);
# it's enforced off the last stored snapshot, so it survives a bot restart
# the way an in-process cooldown wouldn't.
REFRESH_COOLDOWN_SECONDS = 15 * 60


def _days_since(moment: datetime | None) -> int | None:
    """Whole days between `moment` and now, or None if unknown.

    ShaheenMember.joined_at is nullable (a member can exist before Discord
    ever told us when they joined), so tenure simply doesn't evaluate in
    that case rather than guessing.
    """
    if moment is None:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return max(0, (datetime.now(UTC) - moment).days)


@dataclass
class TierChange:
    old_tier: str
    new_tier: str
    promoted: bool


@dataclass
class Announcement:
    member: ShaheenMember
    player: BrawlhallaPlayer
    discord_id: int
    achievement: AchievementDef | None = None
    new_peak_rating: int | None = None
    tier_change: TierChange | None = None


@dataclass
class SnapshotRunResult:
    members_processed: int = 0
    errors: list[str] = field(default_factory=list)
    announcements: list[Announcement] = field(default_factory=list)
    # discord_id -> the tier this run saw, None when unranked. Recorded so
    # bot/cogs/clan.py can sync rank roles off the same pass rather than
    # re-reading every snapshot (docs/DECISIONS.md ADR-087). The service
    # itself stays Discord-agnostic: it reports tiers, it does not assign
    # anything.
    tiers: dict[int, str | None] = field(default_factory=dict)


@dataclass
class RefreshOutcome:
    """Result of an on-demand /refresh.

    `refreshed` is False when the cooldown blocked it, in which case
    `retry_after_seconds` says how long is left and nothing was fetched.
    """

    refreshed: bool
    retry_after_seconds: int = 0
    result: SnapshotRunResult | None = None


class SnapshotService:
    def __init__(
        self,
        session: AsyncSession,
        brawlhalla: BrawlhallaService,
        *,
        season: int | None = None,
    ) -> None:
        """`season` is the Brawlhalla ranked season every row written by this
        service is stamped with (docs/DECISIONS.md ADR-088). Callers pass
        `Settings.brawlhalla_season`; None leaves the stamp empty, which
        keeps the row off every current-season leaderboard rather than
        letting an unlabelled rating rank against labelled ones.
        """
        self._session = session
        self._brawlhalla = brawlhalla
        self._season = season
        self._links = MemberPlayerLinkRepository(session)
        self._ranking = RankingSnapshotRepository(session)
        self._legends = LegendSnapshotRepository(session)
        self._achievement_service = AchievementService(session)

    async def run_for_guild(self, guild_id: int) -> SnapshotRunResult:
        result = SnapshotRunResult()
        for member, player, discord_id in await self._links.list_active_for_guild(guild_id):
            try:
                await self.snapshot_member(member, player, discord_id, result)
                result.members_processed += 1
            except BrawlhallaAPIError as exc:
                logger.warning(
                    "Snapshot failed for player %s: %s", player.brawlhalla_player_id, exc
                )
                result.errors.append(f"{player.player_name}: Brawlhalla API error")
        return result

    async def snapshot_member(
        self,
        member: ShaheenMember,
        player: BrawlhallaPlayer,
        discord_id: int,
        result: SnapshotRunResult,
    ) -> None:
        """Snapshot one member's current rating/legend stats.

        Public (not `_`-prefixed) so bot/cogs/link.py can take an initial
        snapshot synchronously right after /link, instead of the member
        waiting for the next scheduled run_for_guild tick to appear on any
        leaderboard (docs/DECISIONS.md ADR-059). run_for_guild uses this
        the same way it always has — no behavior change there.
        """
        stats = await self._brawlhalla.get_stats(player.brawlhalla_player_id)
        ranked = await self._brawlhalla.get_ranked(player.brawlhalla_player_id)
        captured_at = datetime.now(UTC)

        result.tiers[discord_id] = ranked.tier if ranked else None

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
                # Fetched and shown in Discord since Phase 2 but never
                # stored until ADR-081; backs the region_top_100 achievement.
                region_rank=ranked.region_rank if ranked else None,
                season=self._season,
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

        if (
            ranked is not None
            and ranked.tier is not None
            and previous is not None
            and previous.tier is not None
        ):
            old_index = tier_index(previous.tier)
            new_index = tier_index(ranked.tier)
            # Family-level only (Gold/Platinum/...), not sub-ranks (I/II/
            # III) — same granularity achievements.py's tier_at_least
            # already uses, and fails open (no announcement) on either
            # tier string being unrecognized rather than guessing a
            # direction.
            if old_index is not None and new_index is not None and old_index != new_index:
                result.announcements.append(
                    Announcement(
                        member=member,
                        player=player,
                        discord_id=discord_id,
                        tier_change=TierChange(
                            old_tier=previous.tier,
                            new_tier=ranked.tier,
                            promoted=new_index > old_index,
                        ),
                    )
                )

        await self._award_achievements(member, player, discord_id, stats, ranked, result)

    async def refresh_member(
        self, member: ShaheenMember, player: BrawlhallaPlayer, discord_id: int
    ) -> RefreshOutcome:
        """Snapshot one member now, on their own request, subject to a cooldown.

        The same work run_for_guild does for everyone, for one member —
        including achievement awards, so a member who just crossed a
        threshold doesn't wait for the next scheduled tick.
        """
        latest = await self._ranking.get_latest(player.id)
        if latest is not None:
            captured_at = latest.captured_at
            if captured_at.tzinfo is None:
                captured_at = captured_at.replace(tzinfo=UTC)
            elapsed = (datetime.now(UTC) - captured_at).total_seconds()
            if elapsed < REFRESH_COOLDOWN_SECONDS:
                return RefreshOutcome(
                    refreshed=False,
                    retry_after_seconds=int(REFRESH_COOLDOWN_SECONDS - elapsed),
                )

        result = SnapshotRunResult()
        await self.snapshot_member(member, player, discord_id, result)
        result.members_processed = 1
        return RefreshOutcome(refreshed=True, result=result)

    async def _award_achievements(
        self,
        member: ShaheenMember,
        player: BrawlhallaPlayer,
        discord_id: int,
        stats: PlayerStatsResponse,
        ranked: PlayerRankedResponse | None,
        result: SnapshotRunResult,
    ) -> None:
        already_earned = await self._achievement_service.earned_keys(member.id)
        # ADR-081: peak rating, global/region standing and ranked win rate
        # all come from data this snapshot already fetched — they used to be
        # thrown away after the embed was built.
        newly_earned = evaluate_snapshot_achievements(
            games=stats.games,
            ranked_tier=ranked.tier if ranked else None,
            already_earned=already_earned,
            peak_rating=ranked.peak_rating if ranked else None,
            global_rank=ranked.global_rank if ranked else None,
            region_rank=ranked.region_rank if ranked else None,
            ranked_wins=ranked.wins if ranked else None,
            ranked_games=ranked.games if ranked else None,
        )
        # Tenure rides along on the same loop: it's the one recurring pass
        # over every linked member, so time-served milestones need no job of
        # their own (ADR-081).
        newly_earned += evaluate_tenure_achievements(
            days_in_clan=_days_since(member.joined_at), already_earned=already_earned
        )
        extra: dict[str, object] = {"games": stats.games}
        if ranked is not None:
            extra.update(
                tier=ranked.tier,
                rating=ranked.rating,
                peak_rating=ranked.peak_rating,
                global_rank=ranked.global_rank,
            )
        for achievement_def in newly_earned:
            awarded = await self._achievement_service.award(
                shaheen_member_id=member.id, definition=achievement_def, extra=extra
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
