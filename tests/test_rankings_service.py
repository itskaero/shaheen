"""The Rankings page's board (docs/DECISIONS.md ADR-105)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from database.models.legend_snapshot import LegendSnapshot
from database.models.ranking_snapshot import RankingSnapshot
from database.models.team import Team
from database.repositories.brawlhalla_player_repository import BrawlhallaPlayerRepository
from database.repositories.discord_user_repository import DiscordUserRepository
from database.repositories.legend_snapshot_repository import LegendSnapshotRepository
from database.repositories.member_player_link_repository import MemberPlayerLinkRepository
from database.repositories.pakistan_board_repository import PakistanBoardRepository
from database.repositories.ranking_snapshot_repository import RankingSnapshotRepository
from database.repositories.shaheen_member_repository import ShaheenMemberRepository
from database.repositories.team_repository import TeamRepository
from services.rankings_service import RankingsService

GUILD_ID = 1
NOW = datetime(2026, 10, 4, 12, tzinfo=UTC)


async def _board_player(session: AsyncSession, bid: int, *, owner: int | None = None) -> int:
    player = await BrawlhallaPlayerRepository(session).upsert(
        brawlhalla_player_id=bid, player_name=f"P{bid}", region=None
    )
    await PakistanBoardRepository(session).add(
        guild_id=GUILD_ID, player_id=player.id, added_by_discord_id=1, owner_discord_id=owner
    )
    return player.id


async def _reading(
    session: AsyncSession,
    player_id: int,
    *,
    rating: int | None,
    days_ago: float = 0,
    season: int = 42,
    rating_2v2: int | None = None,
) -> None:
    await RankingSnapshotRepository(session).add(
        RankingSnapshot(
            brawlhalla_player_id=player_id,
            captured_at=NOW - timedelta(days=days_ago),
            rating=rating,
            peak_rating=rating,
            tier="Gold" if rating else None,
            wins=1,
            games=2,
            season=season,
            rating_2v2=rating_2v2,
        )
    )


async def test_rows_are_season_scoped_sorted_and_include_unplaced(session: AsyncSession) -> None:
    a = await _board_player(session, 10)
    b = await _board_player(session, 20)
    c = await _board_player(session, 30)
    d = await _board_player(session, 40)
    await _reading(session, a, rating=1500)
    await _reading(session, b, rating=1900)
    await _reading(session, c, rating=None, rating_2v2=1600)  # 2v2 only: still listed
    await _reading(session, d, rating=2500, season=41)  # last season: not in S42

    board = await RankingsService(session).pakistan(GUILD_ID, now=NOW)

    assert board.season == 42
    assert board.seasons == [42, 41]
    assert [row.player.brawlhalla_player_id for row in board.rows] == [20, 10, 30]
    assert board.rows[2].snapshot.rating_2v2 == 1600
    assert all(row.country == "PK" for row in board.rows)


async def test_an_older_season_can_be_asked_for(session: AsyncSession) -> None:
    a = await _board_player(session, 10)
    await _reading(session, a, rating=1500, season=42)
    await _reading(session, a, rating=2100, season=41, days_ago=20)

    board = await RankingsService(session).pakistan(GUILD_ID, season=41, now=NOW)

    assert board.season == 41
    assert [row.snapshot.rating for row in board.rows] == [2100]


async def test_trend_is_the_7_day_change_within_the_season(session: AsyncSession) -> None:
    a = await _board_player(session, 10)
    b = await _board_player(session, 20)
    await _reading(session, a, rating=1400, days_ago=10)  # outside the window
    await _reading(session, a, rating=1450, days_ago=6)
    await _reading(session, a, rating=1520, days_ago=0)
    await _reading(session, b, rating=1700, days_ago=1)  # one reading: no trend yet

    rows = {
        row.player.brawlhalla_player_id: row
        for row in (await RankingsService(session).pakistan(GUILD_ID, now=NOW)).rows
    }
    assert rows[10].trend == 70
    assert rows[20].trend is None


async def test_team_claim_and_main_legend(session: AsyncSession) -> None:
    a = await _board_player(session, 10, owner=5)
    b = await _board_player(session, 20)
    await _reading(session, a, rating=1500)
    await _reading(session, b, rating=1400)
    # player 10 is also a linked member of the founding team
    user = await DiscordUserRepository(session).get_or_create(5)
    member = await ShaheenMemberRepository(session).get_or_create(
        discord_user_id=user.id, guild_id=GUILD_ID
    )
    await MemberPlayerLinkRepository(session).link(
        shaheen_member_id=member.id, brawlhalla_player_id=a
    )
    # Teams come from rosters now (ADR-114), not from being linked.
    shaheen = await TeamRepository(session).add(
        Team(guild_id=GUILD_ID, slug="shaheen", name="SHAHEEN", tag="SHN", is_founding=True)
    )
    await TeamRepository(session).add_member(
        team_id=shaheen.id, player_id=a, role="player", joined_at=NOW
    )
    await LegendSnapshotRepository(session).add_all(
        [
            LegendSnapshot(
                brawlhalla_player_id=a,
                captured_at=NOW,
                legend_id=i,
                legend_name_key=key,
                games=games,
                wins=1,
            )
            for i, (key, games) in enumerate((("orion", 40), ("hattori", 90)), start=1)
        ]
    )

    rows = {
        row.player.brawlhalla_player_id: row
        for row in (await RankingsService(session).pakistan(GUILD_ID, now=NOW)).rows
    }
    assert rows[10].team_slug == "shaheen"
    assert (rows[10].team, rows[10].is_claimed, rows[10].main_legend) == (
        "SHAHEEN",
        True,
        "hattori",
    )
    assert (rows[20].team, rows[20].is_claimed, rows[20].main_legend) == (None, False, None)


async def test_no_snapshots_means_no_season_and_no_rows(session: AsyncSession) -> None:
    await _board_player(session, 10)
    board = await RankingsService(session).pakistan(GUILD_ID, now=NOW)
    assert (board.season, board.seasons, board.rows) == (None, [], [])
