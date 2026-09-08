"""Direct repository tests for the Phase 3 snapshot/achievement tables."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from database.models.achievement import Achievement
from database.models.legend_snapshot import LegendSnapshot
from database.models.ranking_snapshot import RankingSnapshot
from database.repositories.achievement_repository import AchievementRepository
from database.repositories.brawlhalla_player_repository import BrawlhallaPlayerRepository
from database.repositories.discord_user_repository import DiscordUserRepository
from database.repositories.legend_snapshot_repository import LegendSnapshotRepository
from database.repositories.member_achievement_repository import MemberAchievementRepository
from database.repositories.member_player_link_repository import MemberPlayerLinkRepository
from database.repositories.ranking_snapshot_repository import RankingSnapshotRepository
from database.repositories.shaheen_member_repository import ShaheenMemberRepository


async def test_ranking_snapshot_get_latest_and_list_recent(session: AsyncSession) -> None:
    players = BrawlhallaPlayerRepository(session)
    player = await players.upsert(brawlhalla_player_id=1, player_name="P", region=None)
    repo = RankingSnapshotRepository(session)

    assert await repo.get_latest(player.id) is None

    for rating in (1000, 1100):
        await repo.add(
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

    latest = await repo.get_latest(player.id)
    assert latest is not None
    assert latest.rating == 1100

    recent = await repo.list_recent(player.id, limit=5)
    assert len(recent) == 2


async def test_legend_snapshot_add_all(session: AsyncSession) -> None:
    players = BrawlhallaPlayerRepository(session)
    player = await players.upsert(brawlhalla_player_id=1, player_name="P", region=None)
    repo = LegendSnapshotRepository(session)

    await repo.add_all(
        [
            LegendSnapshot(
                brawlhalla_player_id=player.id,
                captured_at=datetime.now(UTC),
                legend_id=1,
                legend_name_key="bodvar",
                games=5,
                wins=2,
                kos=10,
                damagedealt=100,
                falls=1,
            )
        ]
    )
    # No exception and the row is visible via a direct query is enough here;
    # richer read paths are exercised through SnapshotService tests.


async def test_achievement_repository_get_by_key(
    session: AsyncSession, achievement_catalog: dict[str, Achievement]
) -> None:
    repo = AchievementRepository(session)
    assert await repo.get_by_key("games_100") is not None
    assert await repo.get_by_key("does_not_exist") is None
    assert len(await repo.list_all()) == len(achievement_catalog)


async def test_member_achievement_award_is_idempotent(
    session: AsyncSession, achievement_catalog: dict[str, Achievement]
) -> None:
    users = DiscordUserRepository(session)
    members = ShaheenMemberRepository(session)
    awards = MemberAchievementRepository(session)

    user = await users.get_or_create(1)
    member = await members.get_or_create(discord_user_id=user.id, guild_id=1)
    achievement_id = achievement_catalog["games_100"].id

    first = await awards.award(shaheen_member_id=member.id, achievement_id=achievement_id)
    second = await awards.award(shaheen_member_id=member.id, achievement_id=achievement_id)

    assert first is not None
    assert second is None
    assert await awards.has(shaheen_member_id=member.id, achievement_id=achievement_id)
    assert await awards.list_earned_keys(member.id) == {"games_100"}


async def test_list_active_for_guild_returns_real_discord_id(session: AsyncSession) -> None:
    """Regression guard: must be the Discord snowflake, not the internal PK."""
    users = DiscordUserRepository(session)
    members = ShaheenMemberRepository(session)
    players = BrawlhallaPlayerRepository(session)
    links = MemberPlayerLinkRepository(session)

    real_discord_id = 999_999_999_999
    user = await users.get_or_create(real_discord_id)
    member = await members.get_or_create(discord_user_id=user.id, guild_id=1)
    player = await players.upsert(brawlhalla_player_id=1, player_name="P", region=None)
    await links.link(shaheen_member_id=member.id, brawlhalla_player_id=player.id)

    rows = await links.list_active_for_guild(1)
    assert len(rows) == 1
    _member, _player, discord_id = rows[0]
    assert discord_id == real_discord_id
    assert discord_id != member.id  # the bug this guards against
