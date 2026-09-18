"""ClanService: leaderboard ordering, history, and achievements listing."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from database.models.achievement import Achievement
from database.models.legend_snapshot import LegendSnapshot
from database.models.ranking_snapshot import RankingSnapshot
from database.repositories.brawlhalla_player_repository import BrawlhallaPlayerRepository
from database.repositories.discord_user_repository import DiscordUserRepository
from database.repositories.legend_snapshot_repository import LegendSnapshotRepository
from database.repositories.member_achievement_repository import MemberAchievementRepository
from database.repositories.member_player_link_repository import MemberPlayerLinkRepository
from database.repositories.ranking_snapshot_repository import RankingSnapshotRepository
from database.repositories.shaheen_member_repository import ShaheenMemberRepository
from services.clan_service import ClanService

GUILD_ID = 1


async def _make_linked_member(session: AsyncSession, *, discord_id: int, brawlhalla_id: int):
    users = DiscordUserRepository(session)
    members = ShaheenMemberRepository(session)
    players = BrawlhallaPlayerRepository(session)
    links = MemberPlayerLinkRepository(session)

    user = await users.get_or_create(discord_id)
    member = await members.get_or_create(discord_user_id=user.id, guild_id=GUILD_ID)
    player = await players.upsert(
        brawlhalla_player_id=brawlhalla_id, player_name=f"P{brawlhalla_id}", region=None
    )
    await links.link(shaheen_member_id=member.id, brawlhalla_player_id=player.id)
    return member, player


async def test_leaderboard_orders_by_rating_descending(session: AsyncSession) -> None:
    _member_a, player_a = await _make_linked_member(session, discord_id=1, brawlhalla_id=10)
    _member_b, player_b = await _make_linked_member(session, discord_id=2, brawlhalla_id=20)

    ranking = RankingSnapshotRepository(session)
    await ranking.add(
        RankingSnapshot(
            brawlhalla_player_id=player_a.id,
            captured_at=datetime.now(UTC),
            rating=1000,
            peak_rating=1000,
            tier="Gold",
            wins=1,
            games=2,
        )
    )
    await ranking.add(
        RankingSnapshot(
            brawlhalla_player_id=player_b.id,
            captured_at=datetime.now(UTC),
            rating=2000,
            peak_rating=2000,
            tier="Diamond",
            wins=1,
            games=2,
        )
    )

    rows = await ClanService(session).leaderboard(GUILD_ID)
    assert [row[1].brawlhalla_player_id for row in rows] == [20, 10]


async def test_leaderboard_excludes_players_without_a_snapshot(session: AsyncSession) -> None:
    await _make_linked_member(session, discord_id=1, brawlhalla_id=10)
    rows = await ClanService(session).leaderboard(GUILD_ID)
    assert rows == []


async def test_history_returns_recent_snapshots_newest_first(session: AsyncSession) -> None:
    _member, player = await _make_linked_member(session, discord_id=1, brawlhalla_id=10)
    ranking = RankingSnapshotRepository(session)
    for rating in (1000, 1100, 1200):
        await ranking.add(
            RankingSnapshot(
                brawlhalla_player_id=player.id,
                captured_at=datetime.now(UTC),
                rating=rating,
                peak_rating=rating,
                tier="Gold",
                wins=1,
                games=2,
            )
        )

    history = await ClanService(session).history(player.id, limit=2)
    assert len(history) == 2
    assert history[0].rating == 1200


async def test_achievements_for_member_orders_oldest_first(
    session: AsyncSession, achievement_catalog: dict[str, Achievement]
) -> None:
    member, _player = await _make_linked_member(session, discord_id=1, brawlhalla_id=10)
    awards = MemberAchievementRepository(session)
    await awards.award(
        shaheen_member_id=member.id, achievement_id=achievement_catalog["games_100"].id
    )
    await awards.award(
        shaheen_member_id=member.id, achievement_id=achievement_catalog["tier_platinum"].id
    )

    entries = await ClanService(session).achievements_for_member(member.id)
    assert [achievement.key for achievement, _awarded_at in entries] == [
        "games_100",
        "tier_platinum",
    ]


async def test_legend_meta_aggregates_across_linked_members(session: AsyncSession) -> None:
    _member_a, player_a = await _make_linked_member(session, discord_id=1, brawlhalla_id=10)
    _member_b, player_b = await _make_linked_member(session, discord_id=2, brawlhalla_id=20)
    legends = LegendSnapshotRepository(session)
    await legends.add_all(
        [
            LegendSnapshot(
                brawlhalla_player_id=player_a.id,
                captured_at=datetime.now(UTC),
                legend_id=1,
                legend_name_key="bodvar",
                games=30,
                wins=20,
                kos=0,
                damagedealt=0,
                falls=0,
            ),
            LegendSnapshot(
                brawlhalla_player_id=player_b.id,
                captured_at=datetime.now(UTC),
                legend_id=1,
                legend_name_key="bodvar",
                games=10,
                wins=5,
                kos=0,
                damagedealt=0,
                falls=0,
            ),
            # Below the min-games-for-meta threshold — should be excluded.
            LegendSnapshot(
                brawlhalla_player_id=player_a.id,
                captured_at=datetime.now(UTC),
                legend_id=2,
                legend_name_key="hattori",
                games=3,
                wins=1,
                kos=0,
                damagedealt=0,
                falls=0,
            ),
        ]
    )
    await session.commit()

    entries = await ClanService(session).legend_meta(GUILD_ID)
    assert [e.legend_name_key for e in entries] == ["bodvar"]
    bodvar = entries[0]
    assert bodvar.total_games == 40
    assert bodvar.total_wins == 25
    assert bodvar.player_count == 2
    assert bodvar.win_rate == 62.5


async def test_legend_meta_empty_when_no_data(session: AsyncSession) -> None:
    await _make_linked_member(session, discord_id=1, brawlhalla_id=10)
    entries = await ClanService(session).legend_meta(GUILD_ID)
    assert entries == []


async def test_rank_context_places_a_rating_between_clan_members(session: AsyncSession) -> None:
    """/lookup's clan comparison: a bare rating means nothing without neighbours."""
    _member_a, player_a = await _make_linked_member(session, discord_id=1, brawlhalla_id=10)
    _member_b, player_b = await _make_linked_member(session, discord_id=2, brawlhalla_id=20)

    ranking = RankingSnapshotRepository(session)
    for player, rating in ((player_a, 1800), (player_b, 1400)):
        await ranking.add(
            RankingSnapshot(
                brawlhalla_player_id=player.id,
                captured_at=datetime.now(UTC),
                rating=rating,
                peak_rating=rating,
                tier="Gold",
                wins=1,
                games=2,
            )
        )

    context = await ClanService(session).rank_context(GUILD_ID, 1600)
    assert context.total_ranked == 2
    assert context.would_be_rank == 2
    assert context.above == ("P10", 1800)
    assert context.below == ("P20", 1400)


async def test_rank_context_at_the_top_has_nobody_above(session: AsyncSession) -> None:
    _member, player = await _make_linked_member(session, discord_id=1, brawlhalla_id=10)
    await RankingSnapshotRepository(session).add(
        RankingSnapshot(
            brawlhalla_player_id=player.id,
            captured_at=datetime.now(UTC),
            rating=1400,
            peak_rating=1400,
            tier="Silver",
            wins=1,
            games=2,
        )
    )

    context = await ClanService(session).rank_context(GUILD_ID, 2000)
    assert context.would_be_rank == 1
    assert context.above is None
    assert context.below == ("P10", 1400)


async def test_rank_context_below_everyone_lands_last(session: AsyncSession) -> None:
    _member, player = await _make_linked_member(session, discord_id=1, brawlhalla_id=10)
    await RankingSnapshotRepository(session).add(
        RankingSnapshot(
            brawlhalla_player_id=player.id,
            captured_at=datetime.now(UTC),
            rating=1900,
            peak_rating=1900,
            tier="Diamond",
            wins=1,
            games=2,
        )
    )

    context = await ClanService(session).rank_context(GUILD_ID, 900)
    assert context.would_be_rank == 2
    assert context.above == ("P10", 1900)
    assert context.below is None


async def test_rank_context_with_no_ranked_members_is_empty(session: AsyncSession) -> None:
    context = await ClanService(session).rank_context(GUILD_ID, 1500)
    assert context.total_ranked == 0
    assert context.above is None and context.below is None


async def test_clan_stats_aggregates_totals_and_spread(session: AsyncSession) -> None:
    _member_a, player_a = await _make_linked_member(session, discord_id=1, brawlhalla_id=10)
    _member_b, player_b = await _make_linked_member(session, discord_id=2, brawlhalla_id=20)

    ranking = RankingSnapshotRepository(session)
    await ranking.add(
        RankingSnapshot(
            brawlhalla_player_id=player_a.id,
            captured_at=datetime.now(UTC),
            rating=1800,
            peak_rating=1900,
            tier="Diamond",
            wins=60,
            games=100,
            region="SEA",
        )
    )
    await ranking.add(
        RankingSnapshot(
            brawlhalla_player_id=player_b.id,
            captured_at=datetime.now(UTC),
            rating=1200,
            peak_rating=1250,
            tier="Silver",
            wins=40,
            games=100,
            region="SEA",
        )
    )

    stats = await ClanService(session).clan_stats(GUILD_ID)
    assert stats.members_ranked == 2
    assert stats.total_games == 200
    assert stats.total_wins == 100
    assert stats.win_rate == 50.0
    assert stats.average_rating == 1500
    assert stats.median_rating == 1500
    assert stats.highest == ("P10", 1800)
    assert dict(stats.tier_counts) == {"Diamond": 1, "Silver": 1}
    assert stats.region_counts == [("SEA", 2)]


async def test_clan_stats_with_no_snapshots_is_empty(session: AsyncSession) -> None:
    stats = await ClanService(session).clan_stats(GUILD_ID)
    assert stats.members_ranked == 0
    assert stats.average_rating is None
    assert stats.median_rating is None
    assert stats.highest is None
