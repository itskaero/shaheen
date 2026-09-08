"""WebsiteService: clan info, leaderboard, player profile/history.

Regression guard for ADR-040: nothing here should expose Discord identity.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from database.models.achievement import Achievement
from database.models.ranking_snapshot import RankingSnapshot
from database.repositories.brawlhalla_player_repository import BrawlhallaPlayerRepository
from database.repositories.discord_user_repository import DiscordUserRepository
from database.repositories.member_achievement_repository import MemberAchievementRepository
from database.repositories.member_player_link_repository import MemberPlayerLinkRepository
from database.repositories.ranking_snapshot_repository import RankingSnapshotRepository
from database.repositories.shaheen_member_repository import ShaheenMemberRepository
from services.website_service import WebsiteService

GUILD_ID = 1


async def _linked_player(session: AsyncSession, *, discord_id: int, brawlhalla_id: int):
    users = DiscordUserRepository(session)
    members = ShaheenMemberRepository(session)
    players = BrawlhallaPlayerRepository(session)
    links = MemberPlayerLinkRepository(session)

    user = await users.get_or_create(discord_id)
    member = await members.get_or_create(discord_user_id=user.id, guild_id=GUILD_ID)
    player = await players.upsert(
        brawlhalla_player_id=brawlhalla_id, player_name=f"P{brawlhalla_id}", region="us-e"
    )
    await links.link(shaheen_member_id=member.id, brawlhalla_player_id=player.id)
    return member, player


async def test_get_clan_info_reflects_member_count(session: AsyncSession) -> None:
    await _linked_player(session, discord_id=1, brawlhalla_id=10)
    await _linked_player(session, discord_id=2, brawlhalla_id=20)

    info = await WebsiteService(session).get_clan_info(GUILD_ID)
    assert info.member_count == 2
    assert info.name == "Shaheen"


async def test_get_player_profile_returns_none_for_unknown_player(session: AsyncSession) -> None:
    profile = await WebsiteService(session).get_player_profile(99999)
    assert profile is None


async def test_get_player_profile_includes_ranking_and_achievements(
    session: AsyncSession, achievement_catalog: dict[str, Achievement]
) -> None:
    member, player = await _linked_player(session, discord_id=1, brawlhalla_id=10)
    await RankingSnapshotRepository(session).add(
        RankingSnapshot(
            brawlhalla_player_id=player.id,
            captured_at=datetime.now(UTC),
            rating=1500,
            peak_rating=1600,
            tier="Platinum I",
            wins=5,
            games=10,
        )
    )
    await MemberAchievementRepository(session).award(
        shaheen_member_id=member.id, achievement_id=achievement_catalog["games_100"].id
    )

    profile = await WebsiteService(session).get_player_profile(10)
    assert profile is not None
    assert profile.player.player_name == "P10"
    assert profile.latest_ranking is not None
    assert profile.latest_ranking.tier == "Platinum I"
    assert [a.key for a, _ in profile.achievements] == ["games_100"]


async def test_get_player_profile_has_no_achievements_when_unlinked(session: AsyncSession) -> None:
    players = BrawlhallaPlayerRepository(session)
    await players.upsert(brawlhalla_player_id=30, player_name="Solo", region=None)

    profile = await WebsiteService(session).get_player_profile(30)
    assert profile is not None
    assert profile.achievements == []
    assert profile.latest_ranking is None


async def test_get_leaderboard_orders_by_rating_and_excludes_no_snapshot(
    session: AsyncSession,
) -> None:
    _member_a, player_a = await _linked_player(session, discord_id=1, brawlhalla_id=10)
    _member_b, player_b = await _linked_player(session, discord_id=2, brawlhalla_id=20)
    await _linked_player(session, discord_id=3, brawlhalla_id=30)  # never snapshotted

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

    entries = await WebsiteService(session).get_leaderboard(GUILD_ID)
    assert [e.player.brawlhalla_player_id for e in entries] == [20, 10]


async def test_get_player_history_returns_none_for_unknown_player(session: AsyncSession) -> None:
    history = await WebsiteService(session).get_player_history(99999)
    assert history is None


async def test_get_player_history_returns_recent_snapshots(session: AsyncSession) -> None:
    _member, player = await _linked_player(session, discord_id=1, brawlhalla_id=10)
    ranking = RankingSnapshotRepository(session)
    for rating in (1000, 1100):
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

    history = await WebsiteService(session).get_player_history(10)
    assert history is not None
    assert len(history) == 2
    assert history[0].rating == 1100
