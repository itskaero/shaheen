"""WeeklyDigestService: rating gains, top chatters, matches played, MVP
picking, and weekly-counter rotation (docs/DECISIONS.md ADR-070).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from database.models.match import MatchKind
from database.models.ranking_snapshot import RankingSnapshot
from database.repositories.brawlhalla_player_repository import BrawlhallaPlayerRepository
from database.repositories.chat_activity_repository import ChatActivityRepository
from database.repositories.discord_user_repository import DiscordUserRepository
from database.repositories.member_player_link_repository import MemberPlayerLinkRepository
from database.repositories.ranking_snapshot_repository import RankingSnapshotRepository
from database.repositories.shaheen_member_repository import ShaheenMemberRepository
from services.digest_service import WeeklyDigestService
from services.match_service import MatchService

GUILD_ID = 1
_NOW = datetime.now(UTC)
_SINCE = _NOW - timedelta(days=7)
_BEFORE_WINDOW = _SINCE - timedelta(days=1)


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


async def _snapshot(
    session: AsyncSession, *, player_id: int, rating: int, captured_at: datetime
) -> None:
    await RankingSnapshotRepository(session).add(
        RankingSnapshot(
            brawlhalla_player_id=player_id,
            captured_at=captured_at,
            rating=rating,
            peak_rating=rating,
            tier="Gold",
            wins=1,
            games=2,
        )
    )


async def test_rating_gains_ranked_biggest_first(session: AsyncSession) -> None:
    _member_a, player_a = await _make_linked_member(session, discord_id=1, brawlhalla_id=10)
    _member_b, player_b = await _make_linked_member(session, discord_id=2, brawlhalla_id=20)
    await _snapshot(session, player_id=player_a.id, rating=1000, captured_at=_SINCE)
    await _snapshot(session, player_id=player_a.id, rating=1100, captured_at=_NOW)  # +100
    await _snapshot(session, player_id=player_b.id, rating=1000, captured_at=_SINCE)
    await _snapshot(session, player_id=player_b.id, rating=1250, captured_at=_NOW)  # +250
    await session.commit()

    digest = await WeeklyDigestService(session).build_and_rotate(GUILD_ID, since=_SINCE)

    assert [g.discord_id for g in digest.rating_gains] == [2, 1]
    assert digest.rating_gains[0].rating_gain == 250


async def test_rating_gains_skip_members_with_only_one_snapshot_in_window(
    session: AsyncSession,
) -> None:
    _member, player = await _make_linked_member(session, discord_id=1, brawlhalla_id=10)
    await _snapshot(session, player_id=player.id, rating=1000, captured_at=_NOW)
    await session.commit()

    digest = await WeeklyDigestService(session).build_and_rotate(GUILD_ID, since=_SINCE)
    assert digest.rating_gains == ()


async def test_rating_gains_skip_negative_or_zero_change(session: AsyncSession) -> None:
    _member, player = await _make_linked_member(session, discord_id=1, brawlhalla_id=10)
    await _snapshot(session, player_id=player.id, rating=1200, captured_at=_SINCE)
    await _snapshot(session, player_id=player.id, rating=1100, captured_at=_NOW)  # dropped
    await session.commit()

    digest = await WeeklyDigestService(session).build_and_rotate(GUILD_ID, since=_SINCE)
    assert digest.rating_gains == ()


async def test_top_chatters_ranked_by_weekly_xp_not_all_time_xp(session: AsyncSession) -> None:
    chat = ChatActivityRepository(session)
    # discord_id=1 was very active before the last reset — weekly_xp only
    # reflects what's accumulated *since* the last digest reset, not the
    # all-time total, even though all-time xp stays higher.
    await chat.record_message(guild_id=GUILD_ID, discord_id=1, xp_gain=500, now=_BEFORE_WINDOW)
    await chat.reset_weekly(GUILD_ID)  # simulates last week's digest run
    await chat.record_message(guild_id=GUILD_ID, discord_id=1, xp_gain=10, now=_NOW)
    await chat.record_message(guild_id=GUILD_ID, discord_id=2, xp_gain=200, now=_NOW)
    await session.commit()

    digest = await WeeklyDigestService(session).build_and_rotate(GUILD_ID, since=_SINCE)

    assert digest.top_chatters[0].discord_id == 2
    assert digest.top_chatters[0].weekly_xp == 200
    discord_id_1_row = await chat.get(guild_id=GUILD_ID, discord_id=1)
    assert discord_id_1_row is not None
    assert discord_id_1_row.xp == 510  # all-time total unaffected by the reset


async def test_matches_played_counts_confirmed_matches(session: AsyncSession) -> None:
    match_service = MatchService(session)
    match = await match_service.create_match(
        guild_id=GUILD_ID, kind=MatchKind.ONE_V_ONE, side_a=[(1, None)], side_b=[(2, None)]
    )
    await match_service.report_result(
        match_id=match.id, guild_id=GUILD_ID, reporter_discord_id=1, reporter_won=True
    )
    await match_service.confirm_result(match_id=match.id, guild_id=GUILD_ID, confirmer_discord_id=2)

    digest = await WeeklyDigestService(session).build_and_rotate(GUILD_ID, since=_SINCE)
    assert digest.matches_played == 1


async def test_mvp_prefers_rating_gain_over_chat_xp(session: AsyncSession) -> None:
    _member, player = await _make_linked_member(session, discord_id=1, brawlhalla_id=10)
    await _snapshot(session, player_id=player.id, rating=1000, captured_at=_SINCE)
    await _snapshot(session, player_id=player.id, rating=1200, captured_at=_NOW)
    await ChatActivityRepository(session).record_message(
        guild_id=GUILD_ID, discord_id=2, xp_gain=9999, now=_NOW
    )
    await session.commit()

    digest = await WeeklyDigestService(session).build_and_rotate(GUILD_ID, since=_SINCE)
    assert digest.mvp_discord_id == 1
    assert digest.mvp_reason is not None
    assert "rating" in digest.mvp_reason


async def test_mvp_falls_back_to_top_chatter_when_no_rating_gains(session: AsyncSession) -> None:
    await ChatActivityRepository(session).record_message(
        guild_id=GUILD_ID, discord_id=3, xp_gain=150, now=_NOW
    )
    await session.commit()

    digest = await WeeklyDigestService(session).build_and_rotate(GUILD_ID, since=_SINCE)
    assert digest.mvp_discord_id == 3
    assert digest.mvp_reason is not None
    assert "XP" in digest.mvp_reason


async def test_mvp_none_on_a_completely_quiet_week(session: AsyncSession) -> None:
    digest = await WeeklyDigestService(session).build_and_rotate(GUILD_ID, since=_SINCE)
    assert digest.mvp_discord_id is None
    assert digest.mvp_reason is None


async def test_build_and_rotate_resets_weekly_xp_after_reading(session: AsyncSession) -> None:
    chat = ChatActivityRepository(session)
    await chat.record_message(guild_id=GUILD_ID, discord_id=1, xp_gain=100, now=_NOW)
    await session.commit()

    digest = await WeeklyDigestService(session).build_and_rotate(GUILD_ID, since=_SINCE)
    assert digest.top_chatters[0].weekly_xp == 100  # read before the reset

    row = await chat.get(guild_id=GUILD_ID, discord_id=1)
    assert row is not None
    assert row.weekly_xp == 0  # reset after
    assert row.xp == 100  # all-time total untouched
