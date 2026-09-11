"""WebsiteService: clan info, leaderboard, player profile/history.

Regression guard for ADR-040: nothing here should expose Discord identity.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from database.models.achievement import Achievement
from database.models.legend_snapshot import LegendSnapshot
from database.models.match import MatchKind, MatchSide
from database.models.ranking_snapshot import RankingSnapshot
from database.models.tournament import TournamentMatchStatus
from database.repositories.brawlhalla_player_repository import BrawlhallaPlayerRepository
from database.repositories.chat_activity_repository import ChatActivityRepository
from database.repositories.discord_user_repository import DiscordUserRepository
from database.repositories.legend_snapshot_repository import LegendSnapshotRepository
from database.repositories.match_repository import MatchRepository
from database.repositories.member_achievement_repository import MemberAchievementRepository
from database.repositories.member_player_link_repository import MemberPlayerLinkRepository
from database.repositories.ranking_snapshot_repository import RankingSnapshotRepository
from database.repositories.shaheen_member_repository import ShaheenMemberRepository
from database.repositories.tournament_repository import (
    TournamentEntrantRepository,
    TournamentMatchRepository,
    TournamentRepository,
)
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


# ---------- legend mastery ----------


async def test_get_player_legends_returns_none_for_unknown_player(session: AsyncSession) -> None:
    legends = await WebsiteService(session).get_player_legends(99999)
    assert legends is None


async def test_get_player_legends_returns_latest_snapshot_per_legend_sorted_by_games(
    session: AsyncSession,
) -> None:
    _member, player = await _linked_player(session, discord_id=1, brawlhalla_id=10)
    legends = LegendSnapshotRepository(session)

    # two snapshots of the same legend at different times — only the later
    # (higher games) one should be returned, per ADR-029's append-only model
    await legends.add_all(
        [
            LegendSnapshot(
                brawlhalla_player_id=player.id,
                captured_at=datetime(2024, 1, 1, tzinfo=UTC),
                legend_id=1,
                legend_name_key="hattori",
                games=10,
                wins=5,
                kos=20,
                damagedealt=1000,
                falls=5,
            ),
            LegendSnapshot(
                brawlhalla_player_id=player.id,
                captured_at=datetime(2024, 2, 1, tzinfo=UTC),
                legend_id=1,
                legend_name_key="hattori",
                games=25,
                wins=12,
                kos=50,
                damagedealt=3000,
                falls=10,
            ),
            LegendSnapshot(
                brawlhalla_player_id=player.id,
                captured_at=datetime(2024, 2, 1, tzinfo=UTC),
                legend_id=2,
                legend_name_key="bodvar",
                games=5,
                wins=1,
                kos=8,
                damagedealt=400,
                falls=3,
            ),
        ]
    )
    await session.commit()

    result = await WebsiteService(session).get_player_legends(10)
    assert result is not None
    assert [entry.legend_name_key for entry in result] == ["hattori", "bodvar"]
    assert result[0].games == 25  # the later snapshot, not the first


# ---------- match history ----------


async def test_get_player_matches_returns_none_for_unknown_player(session: AsyncSession) -> None:
    matches = await WebsiteService(session).get_player_matches(99999)
    assert matches is None


async def test_get_player_matches_empty_for_unlinked_player(session: AsyncSession) -> None:
    players = BrawlhallaPlayerRepository(session)
    await players.upsert(brawlhalla_player_id=30, player_name="Solo", region=None)
    matches = await WebsiteService(session).get_player_matches(30)
    assert matches == []


async def test_get_player_matches_shows_confirmed_result_with_opponent_name(
    session: AsyncSession,
) -> None:
    member_a, _player_a = await _linked_player(session, discord_id=1, brawlhalla_id=10)
    member_b, _player_b = await _linked_player(session, discord_id=2, brawlhalla_id=20)
    matches = MatchRepository(session)

    match = await matches.create(
        guild_id=GUILD_ID,
        kind=MatchKind.ONE_V_ONE,
        participants=[(member_a.id, MatchSide.A), (member_b.id, MatchSide.B)],
    )
    await matches.report(match, reported_by_member_id=member_a.id, winning_side=MatchSide.A)
    await matches.confirm(match)
    await session.commit()

    results = await WebsiteService(session).get_player_matches(10)
    assert results is not None
    (result,) = results
    assert result.won is True
    assert result.opponents == ["P20"]
    assert result.kind == "1v1"

    # from the loser's side, it should show as a loss against P10
    opponent_results = await WebsiteService(session).get_player_matches(20)
    assert opponent_results is not None
    (opponent_result,) = opponent_results
    assert opponent_result.won is False
    assert opponent_result.opponents == ["P10"]


async def test_get_player_matches_excludes_unconfirmed_matches(session: AsyncSession) -> None:
    member_a, _player_a = await _linked_player(session, discord_id=1, brawlhalla_id=10)
    member_b, _player_b = await _linked_player(session, discord_id=2, brawlhalla_id=20)
    matches = MatchRepository(session)

    match = await matches.create(
        guild_id=GUILD_ID,
        kind=MatchKind.ONE_V_ONE,
        participants=[(member_a.id, MatchSide.A), (member_b.id, MatchSide.B)],
    )
    await matches.report(match, reported_by_member_id=member_a.id, winning_side=MatchSide.A)
    # never confirmed
    await session.commit()

    results = await WebsiteService(session).get_player_matches(10)
    assert results == []


# ---------- tournaments ----------


async def test_list_tournaments_returns_tournaments_for_guild(session: AsyncSession) -> None:
    member, _player = await _linked_player(session, discord_id=1, brawlhalla_id=10)
    tournaments = TournamentRepository(session)
    await tournaments.create(
        guild_id=GUILD_ID,
        name="Winter Cup",
        kind=MatchKind.ONE_V_ONE,
        created_by_member_id=member.id,
    )
    await session.commit()

    result = await WebsiteService(session).list_tournaments(GUILD_ID)
    assert [t.name for t in result] == ["Winter Cup"]
    assert result[0].kind == "1v1"
    assert result[0].status == "registration"


async def test_get_tournament_bracket_returns_none_for_unknown_id(session: AsyncSession) -> None:
    bracket = await WebsiteService(session).get_tournament_bracket(99999)
    assert bracket is None


async def test_get_tournament_bracket_resolves_entrant_names_and_matches(
    session: AsyncSession,
) -> None:
    member_a, _player_a = await _linked_player(session, discord_id=1, brawlhalla_id=10)
    member_b, _player_b = await _linked_player(session, discord_id=2, brawlhalla_id=20)

    tournaments = TournamentRepository(session)
    entrants = TournamentEntrantRepository(session)
    bracket_matches = TournamentMatchRepository(session)

    tournament = await tournaments.create(
        guild_id=GUILD_ID,
        name="Duel Cup",
        kind=MatchKind.ONE_V_ONE,
        created_by_member_id=member_a.id,
    )
    entrant_a = await entrants.register(
        tournament_id=tournament.id, shaheen_member_ids=[member_a.id]
    )
    entrant_b = await entrants.register(
        tournament_id=tournament.id, shaheen_member_ids=[member_b.id]
    )
    await bracket_matches.create(
        tournament_id=tournament.id,
        round_number=1,
        slot_index=0,
        entrant_a_id=entrant_a.id,
        entrant_b_id=entrant_b.id,
        status=TournamentMatchStatus.AWAITING_REPORT,
    )
    await session.commit()

    result = await WebsiteService(session).get_tournament_bracket(tournament.id)
    assert result is not None
    assert result.tournament.name == "Duel Cup"
    names = {frozenset(e.names) for e in result.entrants}
    assert names == {frozenset(["P10"]), frozenset(["P20"])}
    (bracket_match,) = result.matches
    assert bracket_match.entrant_a is not None
    assert bracket_match.entrant_b is not None
    assert bracket_match.status == "awaiting_report"


async def test_get_tournament_bracket_unlinked_entrant_shows_as_unknown(
    session: AsyncSession,
) -> None:
    users = DiscordUserRepository(session)
    members = ShaheenMemberRepository(session)
    tournaments = TournamentRepository(session)
    entrants = TournamentEntrantRepository(session)

    user = await users.get_or_create(999)
    member = await members.get_or_create(discord_user_id=user.id, guild_id=GUILD_ID)
    tournament = await tournaments.create(
        guild_id=GUILD_ID, name="Solo Cup", kind=MatchKind.ONE_V_ONE, created_by_member_id=member.id
    )
    await entrants.register(tournament_id=tournament.id, shaheen_member_ids=[member.id])
    await session.commit()

    result = await WebsiteService(session).get_tournament_bracket(tournament.id)
    assert result is not None
    assert result.entrants[0].names == ["Unknown"]


async def test_get_community_activity_shows_linked_member_by_player_name(
    session: AsyncSession,
) -> None:
    _member, player = await _linked_player(session, discord_id=1, brawlhalla_id=10)
    await ChatActivityRepository(session).record_message(
        guild_id=GUILD_ID, discord_id=1, xp_gain=150, now=datetime.now(UTC)
    )
    await session.commit()

    entries = await WebsiteService(session).get_community_activity(GUILD_ID)
    assert len(entries) == 1
    assert entries[0].player_name == player.player_name
    assert entries[0].xp == 150


async def test_get_community_activity_derives_level_live_from_xp(session: AsyncSession) -> None:
    """Regression guard: ChatActivityRepository.record_message deliberately
    never updates the stored `level` column (docs/DECISIONS.md ADR-065) —
    this must derive level from xp at read time, not trust the column.
    """
    await _linked_player(session, discord_id=1, brawlhalla_id=10)
    await ChatActivityRepository(session).record_message(
        guild_id=GUILD_ID, discord_id=1, xp_gain=150, now=datetime.now(UTC)
    )
    await session.commit()

    entries = await WebsiteService(session).get_community_activity(GUILD_ID)
    assert entries[0].level == 2  # level_for_xp(150) == 2, not the stale stored level == 1
    assert entries[0].rank_title == "Hatchling"


async def test_get_community_activity_excludes_unlinked_members(session: AsyncSession) -> None:
    """ADR-040's identity boundary: an unlinked-but-chatty member never
    appears on the public site, regardless of how much XP they have.
    """
    _member, player = await _linked_player(session, discord_id=1, brawlhalla_id=10)
    await ChatActivityRepository(session).record_message(
        guild_id=GUILD_ID, discord_id=1, xp_gain=10, now=datetime.now(UTC)
    )
    # Unlinked member — chats a lot, but has never run /link.
    await ChatActivityRepository(session).record_message(
        guild_id=GUILD_ID, discord_id=999, xp_gain=99_999, now=datetime.now(UTC)
    )
    await session.commit()

    entries = await WebsiteService(session).get_community_activity(GUILD_ID)
    assert len(entries) == 1
    assert entries[0].player_name == player.player_name


async def test_get_community_activity_excludes_linked_members_with_no_activity(
    session: AsyncSession,
) -> None:
    await _linked_player(session, discord_id=1, brawlhalla_id=10)
    await session.commit()

    entries = await WebsiteService(session).get_community_activity(GUILD_ID)
    assert entries == []


async def test_get_community_activity_orders_by_xp_descending(session: AsyncSession) -> None:
    await _linked_player(session, discord_id=1, brawlhalla_id=10)
    await _linked_player(session, discord_id=2, brawlhalla_id=20)
    activity = ChatActivityRepository(session)
    now = datetime.now(UTC)
    await activity.record_message(guild_id=GUILD_ID, discord_id=1, xp_gain=10, now=now)
    await activity.record_message(guild_id=GUILD_ID, discord_id=2, xp_gain=500, now=now)
    await session.commit()

    entries = await WebsiteService(session).get_community_activity(GUILD_ID)
    assert [e.xp for e in entries] == [500, 10]
