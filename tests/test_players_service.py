"""Players directory, slugs and season history (docs/DECISIONS.md ADR-106)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from database.models.ranking_snapshot import RankingSnapshot
from database.models.team import Team
from database.repositories.brawlhalla_player_repository import BrawlhallaPlayerRepository
from database.repositories.discord_user_repository import DiscordUserRepository
from database.repositories.member_player_link_repository import MemberPlayerLinkRepository
from database.repositories.pakistan_board_repository import PakistanBoardRepository
from database.repositories.ranking_snapshot_repository import RankingSnapshotRepository
from database.repositories.shaheen_member_repository import ShaheenMemberRepository
from database.repositories.team_repository import TeamRepository
from services.players_service import PlayersService, brawlhalla_id_from_slug, player_slug

GUILD_ID = 1
NOW = datetime(2026, 10, 4, tzinfo=UTC)


def test_slugs_are_readable_ascii_and_end_in_the_id() -> None:
    assert player_slug("Khan Bhai!", 123) == "khan-bhai-123"
    assert player_slug("kaero.", 5734378) == "kaero-5734378"
    assert player_slug("Bödvar_Main", 9) == "bodvar-main-9"
    assert player_slug("شاہین", 7) == "7"  # no ASCII left: the id alone
    assert brawlhalla_id_from_slug("khan-bhai-123") == 123
    assert brawlhalla_id_from_slug("7") == 7
    assert brawlhalla_id_from_slug("khan") is None


async def _player(session: AsyncSession, bid: int, name: str) -> int:
    player = await BrawlhallaPlayerRepository(session).upsert(
        brawlhalla_player_id=bid, player_name=name, region=None
    )
    return player.id


async def _reading(
    session: AsyncSession, pid: int, rating: int | None, *, season: int = 42, days_ago: int = 0
) -> None:
    await RankingSnapshotRepository(session).add(
        RankingSnapshot(
            brawlhalla_player_id=pid,
            captured_at=NOW - timedelta(days=days_ago),
            rating=rating,
            peak_rating=rating,
            tier="Gold" if rating else None,
            wins=1,
            games=2,
            season=season,
        )
    )


async def test_directory_merges_board_and_linked_players_once(session: AsyncSession) -> None:
    board = PakistanBoardRepository(session)
    both = await _player(session, 10, "Both")
    board_only = await _player(session, 20, "Board")
    linked_only = await _player(session, 30, "Linked")
    await board.add(guild_id=GUILD_ID, player_id=both, added_by_discord_id=1, owner_discord_id=None)
    await board.add(
        guild_id=GUILD_ID, player_id=board_only, added_by_discord_id=1, owner_discord_id=None
    )
    for discord_id, pid in ((5, both), (6, linked_only)):
        user = await DiscordUserRepository(session).get_or_create(discord_id)
        member = await ShaheenMemberRepository(session).get_or_create(
            discord_user_id=user.id, guild_id=GUILD_ID
        )
        await MemberPlayerLinkRepository(session).link(
            shaheen_member_id=member.id, brawlhalla_player_id=pid
        )
    await _reading(session, board_only, 1900)
    await _reading(session, both, 1500)
    # Teams come from rosters (ADR-114): only "Both" is on SHAHEEN.
    shaheen = await TeamRepository(session).add(
        Team(guild_id=GUILD_ID, slug="shaheen", name="SHAHEEN", tag="SHN", is_founding=True)
    )
    await TeamRepository(session).add_member(
        team_id=shaheen.id, player_id=both, role="player", joined_at=datetime.now(UTC)
    )

    entries = await PlayersService(session).directory(GUILD_ID)

    assert [e.player.player_name for e in entries] == ["Board", "Both", "Linked"]
    by_name = {e.player.player_name: e for e in entries}
    assert (by_name["Both"].country, by_name["Both"].team, by_name["Both"].is_claimed) == (
        "PK",
        "SHAHEEN",
        True,  # linked counts as claimed even with no board owner
    )
    assert by_name["Both"].team_slug == "shaheen"
    assert (by_name["Board"].is_claimed, by_name["Board"].team) == (False, None)
    assert by_name["Linked"].team is None  # linked but on no roster
    assert (by_name["Linked"].country, by_name["Linked"].on_pakistan_board) == (None, False)
    assert by_name["Linked"].snapshot is None
    assert by_name["Board"].slug == "board-20"


async def test_season_history_summarises_each_season(session: AsyncSession) -> None:
    pid = await _player(session, 10, "P")
    await _reading(session, pid, 1800, season=41, days_ago=30)
    await _reading(session, pid, 2050, season=41, days_ago=20)
    await _reading(session, pid, 1990, season=41, days_ago=12)  # final S41 reading
    await _reading(session, pid, 1500, season=42, days_ago=3)
    await _reading(session, pid, None, season=42, days_ago=1)  # unplaced since

    history = await PlayersService(session).season_history(10)

    assert history is not None
    assert [(s.season, s.final_rating, s.peak_rating, s.readings) for s in history] == [
        (42, None, 1500, 2),
        (41, 1990, 2050, 3),
    ]
    assert (history[0].pakistan_season_number, history[0].pakistan_season_name) == (
        1,
        "Markhor",
    )
    assert history[1].pakistan_season_number is None
    assert await PlayersService(session).season_history(999) is None
