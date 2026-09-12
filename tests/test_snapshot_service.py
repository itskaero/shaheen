"""SnapshotService: persistence, achievement awarding, milestone detection."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.achievement import Achievement
from database.models.brawlhalla_player import BrawlhallaPlayer
from database.models.legend_snapshot import LegendSnapshot
from database.models.ranking_snapshot import RankingSnapshot
from database.models.shaheen_member import ShaheenMember
from database.repositories.brawlhalla_player_repository import BrawlhallaPlayerRepository
from database.repositories.discord_user_repository import DiscordUserRepository
from database.repositories.member_player_link_repository import MemberPlayerLinkRepository
from database.repositories.shaheen_member_repository import ShaheenMemberRepository
from integrations.brawlhalla.models import (
    LegendStat,
    PlayerRankedResponse,
    PlayerStatsResponse,
    RankedLegendStat,
)
from services.snapshot_service import SnapshotRunResult, SnapshotService

GUILD_ID = 1


class _FakeBrawlhalla:
    def __init__(
        self,
        *,
        games: int = 150,
        tier: str | None = "Platinum II",
        rating: int = 1500,
        peak_rating: int = 1600,
    ) -> None:
        self.games = games
        self.tier = tier
        self.rating = rating
        self.peak_rating = peak_rating

    async def get_stats(self, brawlhalla_id: int) -> PlayerStatsResponse:
        return PlayerStatsResponse(
            brawlhalla_id=brawlhalla_id,
            name="Foo",
            games=self.games,
            wins=self.games // 2,
            legends=[LegendStat(legend_id=1, legend_name_key="bodvar", games=10, wins=5, kos=20)],
        )

    async def get_ranked(self, brawlhalla_id: int) -> PlayerRankedResponse | None:
        if self.tier is None:
            return None
        return PlayerRankedResponse(
            brawlhalla_id=brawlhalla_id,
            name="Foo",
            tier=self.tier,
            rating=self.rating,
            peak_rating=self.peak_rating,
            wins=self.games // 2,
            games=self.games,
            region="us-e",
            legends=[
                RankedLegendStat(
                    legend_id=1,
                    legend_name_key="bodvar",
                    rating=1500,
                    peak_rating=1600,
                    tier=self.tier,
                    wins=5,
                    games=10,
                )
            ],
        )


async def _setup_linked_member(
    session: AsyncSession,
) -> tuple[ShaheenMember, BrawlhallaPlayer, int]:
    users = DiscordUserRepository(session)
    members = ShaheenMemberRepository(session)
    players = BrawlhallaPlayerRepository(session)
    links = MemberPlayerLinkRepository(session)

    user = await users.get_or_create(999)
    member = await members.get_or_create(discord_user_id=user.id, guild_id=GUILD_ID)
    player = await players.upsert(brawlhalla_player_id=42, player_name="Foo", region=None)
    await links.link(shaheen_member_id=member.id, brawlhalla_player_id=player.id)
    return member, player, user.discord_id


async def test_run_for_guild_persists_snapshots(
    session: AsyncSession, achievement_catalog: dict[str, Achievement]
) -> None:
    await _setup_linked_member(session)
    service = SnapshotService(session, _FakeBrawlhalla())  # type: ignore[arg-type]

    result = await service.run_for_guild(GUILD_ID)

    assert result.members_processed == 1
    assert result.errors == []

    ranking_rows = (await session.execute(select(RankingSnapshot))).scalars().all()
    assert len(ranking_rows) == 1
    assert ranking_rows[0].tier == "Platinum II"

    legend_rows = (await session.execute(select(LegendSnapshot))).scalars().all()
    assert len(legend_rows) == 1
    assert legend_rows[0].legend_name_key == "bodvar"


async def test_run_for_guild_awards_achievements(
    session: AsyncSession, achievement_catalog: dict[str, Achievement]
) -> None:
    await _setup_linked_member(session)
    service = SnapshotService(session, _FakeBrawlhalla(games=150, tier="Platinum II"))  # type: ignore[arg-type]

    result = await service.run_for_guild(GUILD_ID)

    earned_keys = {a.achievement.key for a in result.announcements if a.achievement}
    assert "games_100" in earned_keys
    assert "tier_platinum" in earned_keys
    assert "games_500" not in earned_keys
    assert "tier_diamond_plus" not in earned_keys


async def test_run_for_guild_does_not_reaward_on_second_run(
    session: AsyncSession, achievement_catalog: dict[str, Achievement]
) -> None:
    await _setup_linked_member(session)
    service = SnapshotService(session, _FakeBrawlhalla(games=150, tier="Platinum II"))  # type: ignore[arg-type]

    await service.run_for_guild(GUILD_ID)
    second = await service.run_for_guild(GUILD_ID)

    earned_keys = {a.achievement.key for a in second.announcements if a.achievement}
    assert earned_keys == set()


async def test_run_for_guild_detects_new_peak_rating(
    session: AsyncSession, achievement_catalog: dict[str, Achievement]
) -> None:
    await _setup_linked_member(session)

    first_service = SnapshotService(session, _FakeBrawlhalla(peak_rating=1600))  # type: ignore[arg-type]
    await first_service.run_for_guild(GUILD_ID)

    second_service = SnapshotService(session, _FakeBrawlhalla(peak_rating=1700))  # type: ignore[arg-type]
    result = await second_service.run_for_guild(GUILD_ID)

    milestones = [a for a in result.announcements if a.new_peak_rating is not None]
    assert len(milestones) == 1
    assert milestones[0].new_peak_rating == 1700


async def test_run_for_guild_no_milestone_on_first_ever_snapshot(
    session: AsyncSession, achievement_catalog: dict[str, Achievement]
) -> None:
    await _setup_linked_member(session)
    service = SnapshotService(session, _FakeBrawlhalla(peak_rating=1600))  # type: ignore[arg-type]

    result = await service.run_for_guild(GUILD_ID)

    milestones = [a for a in result.announcements if a.new_peak_rating is not None]
    assert milestones == []


async def test_run_for_guild_detects_tier_promotion(
    session: AsyncSession, achievement_catalog: dict[str, Achievement]
) -> None:
    await _setup_linked_member(session)

    first_service = SnapshotService(session, _FakeBrawlhalla(tier="Gold I"))  # type: ignore[arg-type]
    await first_service.run_for_guild(GUILD_ID)

    second_service = SnapshotService(session, _FakeBrawlhalla(tier="Platinum III"))  # type: ignore[arg-type]
    result = await second_service.run_for_guild(GUILD_ID)

    changes = [a.tier_change for a in result.announcements if a.tier_change is not None]
    assert len(changes) == 1
    assert changes[0].old_tier == "Gold I"
    assert changes[0].new_tier == "Platinum III"
    assert changes[0].promoted is True


async def test_run_for_guild_detects_tier_demotion(
    session: AsyncSession, achievement_catalog: dict[str, Achievement]
) -> None:
    await _setup_linked_member(session)

    first_service = SnapshotService(session, _FakeBrawlhalla(tier="Diamond I"))  # type: ignore[arg-type]
    await first_service.run_for_guild(GUILD_ID)

    second_service = SnapshotService(session, _FakeBrawlhalla(tier="Platinum III"))  # type: ignore[arg-type]
    result = await second_service.run_for_guild(GUILD_ID)

    changes = [a.tier_change for a in result.announcements if a.tier_change is not None]
    assert len(changes) == 1
    assert changes[0].promoted is False


async def test_run_for_guild_no_tier_change_within_same_family(
    session: AsyncSession, achievement_catalog: dict[str, Achievement]
) -> None:
    """Gold I -> Gold III is a sub-rank move, not a family-level tier
    change — should stay silent (docs/DECISIONS.md ADR-068).
    """
    await _setup_linked_member(session)

    first_service = SnapshotService(session, _FakeBrawlhalla(tier="Gold I"))  # type: ignore[arg-type]
    await first_service.run_for_guild(GUILD_ID)

    second_service = SnapshotService(session, _FakeBrawlhalla(tier="Gold III"))  # type: ignore[arg-type]
    result = await second_service.run_for_guild(GUILD_ID)

    changes = [a.tier_change for a in result.announcements if a.tier_change is not None]
    assert changes == []


async def test_run_for_guild_no_tier_change_on_first_ever_snapshot(
    session: AsyncSession, achievement_catalog: dict[str, Achievement]
) -> None:
    await _setup_linked_member(session)
    service = SnapshotService(session, _FakeBrawlhalla(tier="Platinum II"))  # type: ignore[arg-type]

    result = await service.run_for_guild(GUILD_ID)

    changes = [a.tier_change for a in result.announcements if a.tier_change is not None]
    assert changes == []


async def test_snapshot_member_persists_a_single_snapshot(
    session: AsyncSession, achievement_catalog: dict[str, Achievement]
) -> None:
    """snapshot_member is public (docs/DECISIONS.md ADR-059) so
    bot/cogs/link.py can take an initial snapshot right after /link,
    constructing its own SnapshotRunResult rather than going through
    run_for_guild's per-guild loop — confirm that call shape works.
    """
    member, player, discord_id = await _setup_linked_member(session)
    service = SnapshotService(session, _FakeBrawlhalla())  # type: ignore[arg-type]
    result = SnapshotRunResult()

    await service.snapshot_member(member, player, discord_id, result)

    ranking_rows = (await session.execute(select(RankingSnapshot))).scalars().all()
    assert len(ranking_rows) == 1
    assert ranking_rows[0].tier == "Platinum II"
