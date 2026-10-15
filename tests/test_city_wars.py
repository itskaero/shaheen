"""City Wars (docs/DECISIONS.md ADR-128)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from bot.content.network_embeds import build_city_board_embed
from core.exceptions import ShaheenError
from database.models.ranking_snapshot import RankingSnapshot
from database.repositories.brawlhalla_player_repository import BrawlhallaPlayerRepository
from database.repositories.pakistan_board_repository import PakistanBoardRepository
from database.repositories.ranking_snapshot_repository import RankingSnapshotRepository
from services.cities import CITIES, CITY_TOP_N, city_label, city_standings
from services.city_service import CityService
from services.rankings_service import RankingsService

GUILD = 1


def test_a_city_scores_the_average_of_its_best_players() -> None:
    placed = [("lahore", f"L{i}", 1000 + 100 * i) for i in range(7)]  # best five: 1200..1600
    placed += [("karachi", "K1", 1500), (None, "Nobody", 2500), ("atlantis", "X", 3000)]
    karachi, lahore = city_standings(placed)  # 1500 beats 1400
    assert (lahore.key, lahore.rating, lahore.players) == ("lahore", 1400, 7)
    assert len(lahore.top) == CITY_TOP_N and lahore.top[0] == ("L6", 1600)
    assert (karachi.rating, karachi.players) == (1500, 1)
    assert city_label("islamabad") == "Islamabad / Rawalpindi" and city_label(None) is None


async def test_city_board_uses_placed_players_with_a_city(session: AsyncSession) -> None:
    players = BrawlhallaPlayerRepository(session)
    for bid, city, rating in (
        (1, "lahore", 1800),
        (2, "lahore", 1600),
        (3, "karachi", 1900),
        (4, "karachi", None),
        (5, None, 2400),
    ):
        player = await players.upsert(brawlhalla_player_id=bid, player_name=f"P{bid}", region=None)
        await CityService(session).set_city(
            guild_id=GUILD, player=player, city=city, actor_discord_id=9
        )
        await PakistanBoardRepository(session).add(
            guild_id=GUILD, player_id=player.id, added_by_discord_id=1, owner_discord_id=None
        )
        await RankingSnapshotRepository(session).add(
            RankingSnapshot(
                brawlhalla_player_id=player.id,
                captured_at=datetime.now(UTC),
                rating=rating,
                peak_rating=rating,
                wins=0,
                games=0,
                season=42,
            )
        )
    season, standings = await RankingsService(session).cities(GUILD)
    assert season == 42
    assert [(c.key, c.rating, c.players) for c in standings] == [
        ("karachi", 1900, 1),  # the unplaced Karachi player doesn't count
        ("lahore", 1700, 2),
    ]
    board = await RankingsService(session).pakistan(GUILD)
    assert {row.player.brawlhalla_player_id: row.city for row in board.rows}[1] == "lahore"
    embed = build_city_board_embed(standings=standings, season=season, site_url="https://x.org")
    assert "Karachi" in (embed.description or "")


async def test_only_listed_cities(session: AsyncSession) -> None:
    player = await BrawlhallaPlayerRepository(session).upsert(
        brawlhalla_player_id=1, player_name="P1", region=None
    )
    with pytest.raises(ShaheenError):
        await CityService(session).set_city(
            guild_id=GUILD, player=player, city="atlantis", actor_discord_id=9
        )
    await CityService(session).set_city(
        guild_id=GUILD, player=player, city="quetta", actor_discord_id=9
    )
    assert player.city == "quetta" and "quetta" in CITIES
    await CityService(session).set_city(
        guild_id=GUILD, player=player, city=None, actor_discord_id=9
    )
    assert player.city is None


def test_empty_city_board_explains_itself() -> None:
    embed = build_city_board_embed(standings=[], season=None, site_url="https://x.org")
    assert "/city set" in (embed.description or "")
