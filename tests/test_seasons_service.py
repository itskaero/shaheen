"""The Seasons page service (docs/DECISIONS.md ADR-113)."""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from database.models.legend_snapshot import LegendSnapshot
from database.models.match import MatchKind
from database.models.ranking_snapshot import RankingSnapshot
from database.repositories.brawlhalla_player_repository import BrawlhallaPlayerRepository
from database.repositories.discord_user_repository import DiscordUserRepository
from database.repositories.legend_snapshot_repository import LegendSnapshotRepository
from database.repositories.ranking_snapshot_repository import RankingSnapshotRepository
from database.repositories.shaheen_member_repository import ShaheenMemberRepository
from database.repositories.tournament_repository import TournamentRepository
from integrations.brawlhalla.models import SearchResult
from services.pakistan_board_service import PakistanBoardService
from services.seasons import pakistan_season
from services.seasons_service import SeasonsService, legend_of_season, season_status

GUILD = 1
S42 = pakistan_season(42)
S43 = pakistan_season(43)
assert S42 is not None and S43 is not None
# Ten days into S43, so S42 is a finished season.
NOW = S43.starts_at + timedelta(days=10)


def _legend(key: str, games: int, wins: int, at: datetime, player_id: int = 1) -> LegendSnapshot:
    return LegendSnapshot(
        brawlhalla_player_id=player_id,
        captured_at=at,
        legend_id=1,
        legend_name_key=key,
        games=games,
        wins=wins,
    )


def test_status_follows_the_calendar() -> None:
    assert season_status(S42, NOW) == "past"
    assert season_status(S43, NOW) == "current"
    s44 = pakistan_season(44)
    assert s44 is not None and season_status(s44, NOW) == "upcoming"


def test_legend_of_the_season_counts_games_played_inside_the_window() -> None:
    t0, t1 = S42.starts_at, S42.starts_at + timedelta(days=30)
    best = legend_of_season(
        [
            # Lifetime 500 games of Bodvar but only 10 this season...
            [_legend("bodvar", 500, 250, t0), _legend("bodvar", 510, 256, t1)],
            # ...against 30 games of Orion across two players.
            [_legend("orion", 5, 1, t0), _legend("orion", 25, 11, t1)],
            [_legend("orion", 0, 0, t0), _legend("orion", 10, 4, t1)],
        ]
    )
    assert best is not None
    assert (best.legend_name_key, best.games, best.players) == ("orion", 30, 2)
    assert round(best.win_rate, 1) == 46.7


def test_no_legend_of_the_season_without_play_in_the_window() -> None:
    t0 = S42.starts_at
    assert legend_of_season([]) is None
    assert legend_of_season([[_legend("orion", 40, 20, t0)]]) is None


async def _board_player(session: AsyncSession, bid: int, discord_id: int | None = None) -> int:
    candidate = SearchResult(brawlhalla_id=bid, name=f"P{bid}")
    service = PakistanBoardService(session)
    if discord_id is None:
        await service.add(guild_id=GUILD, added_by_discord_id=1, candidate=candidate)
    else:
        await service.join(guild_id=GUILD, discord_id=discord_id, candidate=candidate)
    player = await BrawlhallaPlayerRepository(session).get_by_brawlhalla_id(bid)
    assert player is not None
    return player.id


async def _rate(
    session: AsyncSession, player_id: int, rating: int, season: int, at: datetime
) -> None:
    await RankingSnapshotRepository(session).add(
        RankingSnapshot(
            brawlhalla_player_id=player_id,
            captured_at=at,
            rating=rating,
            peak_rating=rating,
            tier="Gold",
            wins=1,
            games=2,
            season=season,
        )
    )


async def test_overview_lists_thirteen_cards_with_status_data_and_champions(
    session: AsyncSession,
) -> None:
    a = await _board_player(session, 10)
    b = await _board_player(session, 20)
    await _rate(session, a, 1900, 42, S42.starts_at + timedelta(days=5))
    await _rate(session, b, 2100, 42, S42.starts_at + timedelta(days=6))

    cards = await SeasonsService(session).overview(GUILD, now=NOW)

    assert [c.season.number for c in cards] == list(range(1, 14))
    assert [c.status for c in cards[:3]] == ["past", "current", "upcoming"]
    assert cards[0].has_data and cards[0].champion == "P20"
    assert not cards[1].has_data and cards[1].champion is None
    assert all(c.champion is None for c in cards[1:])


async def test_detail_of_a_past_season(session: AsyncSession) -> None:
    a = await _board_player(session, 10)
    b = await _board_player(session, 20)
    early, late = S42.starts_at + timedelta(days=3), S42.starts_at + timedelta(days=60)
    await _rate(session, a, 1500, 42, early)
    await _rate(session, a, 1800, 42, late)  # +300 in S42
    await _rate(session, b, 2000, 42, early)
    await _rate(session, b, 2050, 42, late)  # +50
    await _rate(session, a, 900, 43, NOW - timedelta(days=1))  # a different season
    await LegendSnapshotRepository(session).add_all(
        [_legend("ada", 10, 5, early, a), _legend("ada", 40, 20, late, a)]
    )
    user = await DiscordUserRepository(session).get_or_create(5)
    member = await ShaheenMemberRepository(session).get_or_create(
        discord_user_id=user.id, guild_id=GUILD
    )
    cup = await TournamentRepository(session).create(
        guild_id=GUILD, name="Markhor Cup", kind=MatchKind.ONE_V_ONE, created_by_member_id=member.id
    )
    cup.started_at = early + timedelta(days=1)
    later = await TournamentRepository(session).create(
        guild_id=GUILD, name="S43 Cup", kind=MatchKind.ONE_V_ONE, created_by_member_id=member.id
    )
    later.started_at = NOW - timedelta(days=2)
    await session.flush()

    detail = await SeasonsService(session).detail(GUILD, 42, now=NOW)

    assert detail is not None and detail.card.status == "past"
    assert [r.player.player_name for r in detail.top] == ["P20", "P10"]
    assert detail.champion is not None and detail.champion.snapshot.rating == 2050
    assert detail.rising is not None
    assert (detail.rising.player.player_name, detail.rising.rating_gain) == ("P10", 300)
    assert detail.legend is not None and detail.legend.legend_name_key == "ada"
    assert [t.name for t in detail.tournaments] == ["Markhor Cup"]


async def test_upcoming_and_pre_brawlistan_seasons(session: AsyncSession) -> None:
    service = SeasonsService(session)
    upcoming = await service.detail(GUILD, 50, now=NOW)
    assert upcoming is not None and upcoming.card.status == "upcoming"
    assert upcoming.top == [] and upcoming.rising is None and upcoming.legend is None
    assert await service.detail(GUILD, 41, now=NOW) is None


async def test_current_season_without_data_is_empty_not_invented(session: AsyncSession) -> None:
    await _board_player(session, 10)
    detail = await SeasonsService(session).detail(GUILD, 43, now=NOW)
    assert detail is not None and detail.card.status == "current"
    assert not detail.card.has_data
    assert detail.top == [] and detail.rising is None and detail.legend is None
