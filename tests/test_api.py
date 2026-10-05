"""FastAPI integration tests — routing, dependency wiring, serialization.

Dependencies are overridden to use the sqlite test session instead of a
real Postgres connection; no live server or Discord/Brawlhalla access
is involved.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.app import app
from api.dependencies import get_session, get_settings
from core.config import Settings
from database.models.achievement import Achievement
from database.models.match import MatchKind, MatchSide
from database.models.ranking_snapshot import RankingSnapshot
from database.repositories.brawlhalla_player_repository import BrawlhallaPlayerRepository
from database.repositories.discord_user_repository import DiscordUserRepository
from database.repositories.match_repository import MatchRepository
from database.repositories.member_achievement_repository import MemberAchievementRepository
from database.repositories.member_player_link_repository import MemberPlayerLinkRepository
from database.repositories.ranking_snapshot_repository import RankingSnapshotRepository
from database.repositories.shaheen_member_repository import ShaheenMemberRepository
from database.repositories.tournament_repository import (
    TournamentEntrantRepository,
    TournamentRepository,
)
from services.achievements import CATALOG
from services.guild_snapshot_service import GuildSnapshotService

GUILD_ID = 1

_TEST_SETTINGS = Settings(
    discord_token=SecretStr("test-token"),
    guild_id=GUILD_ID,
    database_url="sqlite+aiosqlite:///:memory:",
    brawlhalla_api_key=SecretStr("test-key"),
)


@pytest.fixture
def client(
    session_factory: async_sessionmaker[AsyncSession], monkeypatch: pytest.MonkeyPatch
) -> TestClient:
    # The app's lifespan calls core.config.load_settings() directly (it must
    # run before any Depends() override applies), so it needs *some* valid
    # env — these values are never actually used since get_session/
    # get_settings are overridden for every route below.
    monkeypatch.setenv("DISCORD_TOKEN", "test-token")
    monkeypatch.setenv("GUILD_ID", str(GUILD_ID))
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    monkeypatch.setenv("BRAWLHALLA_API_KEY", "test-key")

    async def override_get_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    def override_get_settings() -> Settings:
        return _TEST_SETTINGS

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_settings] = override_get_settings
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "brawlistan"}


def test_cors_allows_any_origin(client: TestClient) -> None:
    # ADR-043: every endpoint is public/read-only, so the frontend (hosted
    # on a separate origin, e.g. GitHub Pages) must be able to call it.
    response = client.get("/health", headers={"Origin": "https://example.github.io"})
    assert response.headers["access-control-allow-origin"] == "*"


def test_clan_endpoint(client: TestClient) -> None:
    response = client.get("/clan")
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Shaheen"
    assert body["member_count"] == 0
    # No GuildSnapshot recorded yet on a fresh deploy -> null, not 0/misleading.
    assert body["discord_member_count"] is None
    assert body["discord_boost_tier"] is None
    assert body["discord_boost_count"] is None


async def test_clan_endpoint_reflects_latest_guild_snapshot(
    session_factory: async_sessionmaker[AsyncSession], client: TestClient
) -> None:
    async with session_factory() as session:
        service = GuildSnapshotService(session)
        await service.record(GUILD_ID, member_count=120, boost_tier=1, boost_count=3)
        await service.record(GUILD_ID, member_count=125, boost_tier=2, boost_count=8)
        await session.commit()

    response = client.get("/clan")
    assert response.status_code == 200
    body = response.json()
    assert body["discord_member_count"] == 125
    assert body["discord_boost_tier"] == 2
    assert body["discord_boost_count"] == 8


def test_leaderboard_empty(client: TestClient) -> None:
    response = client.get("/leaderboard")
    assert response.status_code == 200
    assert response.json() == []


def test_roster_empty(client: TestClient) -> None:
    response = client.get("/roster")
    assert response.status_code == 200
    assert response.json() == []


def test_achievements_empty_catalog(client: TestClient) -> None:
    # No achievements seeded — the catalog itself is empty in a fresh test DB.
    response = client.get("/achievements")
    assert response.status_code == 200
    assert response.json() == []


def test_player_profile_not_found(client: TestClient) -> None:
    response = client.get("/players/99999")
    assert response.status_code == 404


def test_player_history_not_found(client: TestClient) -> None:
    response = client.get("/players/99999/history")
    assert response.status_code == 404


def test_player_legends_not_found(client: TestClient) -> None:
    response = client.get("/players/99999/legends")
    assert response.status_code == 404


def test_player_matches_not_found(client: TestClient) -> None:
    response = client.get("/players/99999/matches")
    assert response.status_code == 404


def test_tournaments_empty(client: TestClient) -> None:
    response = client.get("/tournaments")
    assert response.status_code == 200
    assert response.json() == []


def test_tournament_bracket_not_found(client: TestClient) -> None:
    response = client.get("/tournaments/99999")
    assert response.status_code == 404


async def _seed_linked_player(session: AsyncSession) -> None:
    users = DiscordUserRepository(session)
    members = ShaheenMemberRepository(session)
    players = BrawlhallaPlayerRepository(session)
    links = MemberPlayerLinkRepository(session)

    user = await users.get_or_create(1)
    member = await members.get_or_create(discord_user_id=user.id, guild_id=GUILD_ID)
    player = await players.upsert(brawlhalla_player_id=10, player_name="Foo", region="us-e")
    await links.link(shaheen_member_id=member.id, brawlhalla_player_id=player.id)
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
    await session.commit()


async def test_player_profile_and_leaderboard_reflect_seeded_data(
    session_factory: async_sessionmaker[AsyncSession], client: TestClient
) -> None:
    async with session_factory() as session:
        await _seed_linked_player(session)

    profile_response = client.get("/players/10")
    assert profile_response.status_code == 200
    profile = profile_response.json()
    assert profile["player_name"] == "Foo"
    assert profile["tier"] == "Platinum I"
    assert "discord_id" not in profile  # ADR-040: never expose Discord identity
    assert profile["playstyle_tags"] == ["Well-Rounded"]  # no legend snapshots seeded

    leaderboard_response = client.get("/leaderboard")
    assert leaderboard_response.status_code == 200
    (entry,) = leaderboard_response.json()
    assert entry["player_name"] == "Foo"
    assert entry["brawlhalla_id"] == 10

    history_response = client.get("/players/10/history")
    assert history_response.status_code == 200
    (snapshot,) = history_response.json()
    assert snapshot["rating"] == 1500


async def test_player_matches_and_tournament_bracket_reflect_seeded_data(
    session_factory: async_sessionmaker[AsyncSession], client: TestClient
) -> None:
    async with session_factory() as session:
        await _seed_linked_player(session)  # discord_id=1, brawlhalla_id=10, "Foo"

        users = DiscordUserRepository(session)
        members = ShaheenMemberRepository(session)
        players = BrawlhallaPlayerRepository(session)
        links = MemberPlayerLinkRepository(session)

        user_a = await users.get_or_create(
            1
        )  # idempotent — same DiscordUser _seed_linked_player made
        user_b = await users.get_or_create(2)
        member_a = await members.get_or_create(discord_user_id=user_a.id, guild_id=GUILD_ID)
        member_b = await members.get_or_create(discord_user_id=user_b.id, guild_id=GUILD_ID)
        player_b = await players.upsert(brawlhalla_player_id=20, player_name="Bar", region="eu")
        await links.link(shaheen_member_id=member_b.id, brawlhalla_player_id=player_b.id)

        matches = MatchRepository(session)
        match = await matches.create(
            guild_id=GUILD_ID,
            kind=MatchKind.ONE_V_ONE,
            participants=[(member_a.id, MatchSide.A), (member_b.id, MatchSide.B)],
        )
        await matches.report(match, reported_by_member_id=member_a.id, winning_side=MatchSide.A)
        await matches.confirm(match)

        tournaments = TournamentRepository(session)
        entrants = TournamentEntrantRepository(session)
        tournament = await tournaments.create(
            guild_id=GUILD_ID,
            name="Winter Cup",
            kind=MatchKind.ONE_V_ONE,
            created_by_member_id=member_a.id,
        )
        await entrants.register(tournament_id=tournament.id, shaheen_member_ids=[member_a.id])
        await session.commit()
        tournament_id = tournament.id

    matches_response = client.get("/players/10/matches")
    assert matches_response.status_code == 200
    (result,) = matches_response.json()
    assert result["won"] is True
    assert result["opponents"] == ["Bar"]

    tournaments_response = client.get("/tournaments")
    assert tournaments_response.status_code == 200
    (summary,) = tournaments_response.json()
    assert summary["name"] == "Winter Cup"
    assert summary["id"] == tournament_id

    bracket_response = client.get(f"/tournaments/{tournament_id}")
    assert bracket_response.status_code == 200
    bracket = bracket_response.json()
    assert bracket["tournament"]["name"] == "Winter Cup"
    (entrant,) = bracket["entrants"]
    assert entrant["names"] == ["Foo"]


async def test_roster_includes_unranked_member_unlike_leaderboard(
    session_factory: async_sessionmaker[AsyncSession], client: TestClient
) -> None:
    async with session_factory() as session:
        # Ranked member (via the shared helper) plus a second, never-snapshotted one.
        await _seed_linked_player(session)
        users = DiscordUserRepository(session)
        members = ShaheenMemberRepository(session)
        players = BrawlhallaPlayerRepository(session)
        links = MemberPlayerLinkRepository(session)
        user = await users.get_or_create(2)
        member = await members.get_or_create(discord_user_id=user.id, guild_id=GUILD_ID)
        player = await players.upsert(brawlhalla_player_id=20, player_name="Bar", region=None)
        await links.link(shaheen_member_id=member.id, brawlhalla_player_id=player.id)
        await session.commit()

    response = client.get("/roster")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2  # /leaderboard would have dropped the unranked one
    names = {entry["player_name"] for entry in body}
    assert names == {"Foo", "Bar"}
    unranked = next(entry for entry in body if entry["player_name"] == "Bar")
    assert unranked["rating"] is None
    assert unranked["tier"] is None
    assert "discord_id" not in unranked  # ADR-040


async def test_achievement_gallery_reflects_seeded_catalog_and_awards(
    session_factory: async_sessionmaker[AsyncSession], client: TestClient
) -> None:
    async with session_factory() as session:
        await _seed_linked_player(session)  # member with games_100
        await _seed_catalog_and_award(session, key="games_100")

    response = client.get("/achievements")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == len(CATALOG)  # every catalog entry, not just earned ones
    by_key = {entry["key"]: entry for entry in body}
    assert by_key["games_100"]["holder_count"] == 1
    assert by_key["games_100"]["total_members"] == 1
    assert by_key["games_100"]["completion_pct"] == 100.0
    assert by_key["games_500"]["holder_count"] == 0
    # ADR-081: category and rarity band, so the gallery can group and label.
    assert by_key["games_100"]["category"] == "milestone"
    assert by_key["games_100"]["rarity"] == "Common"
    assert by_key["games_500"]["rarity"] == "Unclaimed"
    # ADR-100: who earned it — Brawlhalla identity only, no Discord ids.
    holders = by_key["games_100"]["holders"]
    assert [(h["brawlhalla_id"], h["player_name"]) for h in holders] == [(10, "Foo")]
    assert set(holders[0]) == {"brawlhalla_id", "player_name", "earned_at"}
    assert by_key["games_500"]["holders"] == []


async def _seed_catalog_and_award(session: AsyncSession, *, key: str) -> None:
    """Seeds the full catalog and awards one achievement to discord_id=1."""
    catalog: dict[str, Achievement] = {}
    for definition in CATALOG:
        row = Achievement(
            key=definition.key,
            name=definition.name,
            description=definition.description,
            category=definition.category,
        )
        session.add(row)
        catalog[definition.key] = row
    await session.flush()

    users = DiscordUserRepository(session)
    members = ShaheenMemberRepository(session)
    user = await users.get_or_create(1)
    member = await members.get_or_create(discord_user_id=user.id, guild_id=GUILD_ID)
    await MemberAchievementRepository(session).award(
        shaheen_member_id=member.id, achievement_id=catalog[key].id
    )
    await session.commit()


async def test_player_achievement_checklist_marks_earned_and_unearned(
    session_factory: async_sessionmaker[AsyncSession], client: TestClient
) -> None:
    """The per-member view the clan-wide gallery can't give (ADR-081) — this
    is why every member's achievements looked identical before.
    """
    async with session_factory() as session:
        await _seed_linked_player(session)
        await _seed_catalog_and_award(session, key="games_100")

    response = client.get("/players/10/achievements")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == len(CATALOG)  # the whole catalog, not just what's earned
    by_key = {entry["key"]: entry for entry in body}
    assert by_key["games_100"]["earned"] is True
    assert by_key["games_100"]["awarded_at"] is not None
    assert by_key["games_500"]["earned"] is False
    assert by_key["games_500"]["awarded_at"] is None
    assert by_key["first_link"]["category"] == "onboarding"


def test_player_achievement_checklist_not_found(client: TestClient) -> None:
    assert client.get("/players/99999/achievements").status_code == 404


# ---------- ADR-088: season, region rank, award context, match feed ----------


async def test_clan_endpoint_reports_the_current_season(
    session_factory: async_sessionmaker[AsyncSession], client: TestClient
) -> None:
    async with session_factory() as session:
        await _seed_linked_player(session)

    body = client.get("/clan").json()
    # _seed_linked_player writes an unstamped snapshot, so there is no
    # current season until a stamped one exists.
    assert body["season"] is None
    assert body["pakistan_season"] is None


async def test_clan_endpoint_names_the_pakistan_season(
    session_factory: async_sessionmaker[AsyncSession], client: TestClient
) -> None:
    """ADR-102: S42 is Pakistan Season 1, with its badge key and window."""
    async with session_factory() as session:
        player = await BrawlhallaPlayerRepository(session).upsert(
            brawlhalla_player_id=10, player_name="Foo", region=None
        )
        await RankingSnapshotRepository(session).add(
            RankingSnapshot(
                brawlhalla_player_id=player.id,
                captured_at=datetime.now(UTC),
                rating=1500,
                peak_rating=1500,
                tier="Gold",
                wins=1,
                games=2,
                season=42,
            )
        )
        await session.commit()

    body = client.get("/clan").json()
    assert body["season"] == 42
    season = body["pakistan_season"]
    assert {k: season[k] for k in ("number", "brawlhalla_season", "name", "badge")} == {
        "number": 1,
        "brawlhalla_season": 42,
        "name": "Markhor",
        "badge": "01",
    }
    assert season["name_urdu"] == "مارخور"
    assert season["starts_at"].startswith("2026-09-23")
    assert season["ends_at"].startswith("2026-12-23")


async def test_player_profile_exposes_region_rank_and_season(
    session_factory: async_sessionmaker[AsyncSession], client: TestClient
) -> None:
    async with session_factory() as session:
        users = DiscordUserRepository(session)
        members = ShaheenMemberRepository(session)
        players = BrawlhallaPlayerRepository(session)
        links = MemberPlayerLinkRepository(session)
        user = await users.get_or_create(1)
        member = await members.get_or_create(discord_user_id=user.id, guild_id=GUILD_ID)
        player = await players.upsert(brawlhalla_player_id=10, player_name="Foo", region="us-e")
        await links.link(shaheen_member_id=member.id, brawlhalla_player_id=player.id)
        await RankingSnapshotRepository(session).add(
            RankingSnapshot(
                brawlhalla_player_id=player.id,
                captured_at=datetime.now(UTC),
                rating=1500,
                peak_rating=1600,
                tier="Platinum I",
                wins=5,
                games=10,
                region_rank=12,
                season=3,
            )
        )
        await session.commit()

    body = client.get("/players/10").json()
    assert body["region_rank"] == 12
    assert body["season"] == 3
    assert body["pakistan_season"] is None  # before S42 (ADR-102)

    (entry,) = client.get("/players/10/history").json()
    assert entry["season"] == 3


async def test_player_achievement_checklist_includes_award_context(
    session_factory: async_sessionmaker[AsyncSession], client: TestClient
) -> None:
    async with session_factory() as session:
        await _seed_linked_player(session)
        await _seed_catalog_and_award(session, key="games_100")

    body = client.get("/players/10/achievements").json()
    by_key = {entry["key"]: entry for entry in body}
    # _seed_catalog_and_award writes no extra, so the field is present and null
    # rather than missing — the frontend renders nothing for it.
    assert "context" in by_key["games_100"]
    assert by_key["games_500"]["context"] is None


def test_clan_matches_endpoint_is_empty_without_confirmed_matches(
    client: TestClient,
) -> None:
    response = client.get("/community/matches")
    assert response.status_code == 200
    assert response.json() == []


async def test_pakistan_leaderboard_endpoint(
    session_factory: async_sessionmaker[AsyncSession], client: TestClient
) -> None:
    from database.repositories.pakistan_board_repository import PakistanBoardRepository

    async with session_factory() as session:
        await _seed_linked_player(session)  # clan member, brawlhalla_id=10
        players = BrawlhallaPlayerRepository(session)
        board = PakistanBoardRepository(session)
        member_player = await players.get_by_brawlhalla_id(10)
        outsider = await players.upsert(
            brawlhalla_player_id=77, player_name="Outsider", region=None
        )
        assert member_player is not None
        for player, owner in ((member_player, 5), (outsider, None)):
            await board.add(
                guild_id=GUILD_ID,
                player_id=player.id,
                added_by_discord_id=1,
                owner_discord_id=owner,
            )
        await RankingSnapshotRepository(session).add(
            RankingSnapshot(
                brawlhalla_player_id=outsider.id,
                captured_at=datetime.now(UTC),
                rating=1800,
                peak_rating=1800,
                tier="Diamond",
                wins=1,
                games=2,
                region="SEA",
            )
        )
        await session.commit()

    response = client.get("/pakistan/leaderboard")
    assert response.status_code == 200
    body = response.json()
    assert [(e["player_name"], e["is_clan_member"]) for e in body] == [
        ("Outsider", False),
        ("Foo", True),
    ]
    assert body[0]["region"] == "SEA"
    # claim status is a boolean only — never the owner's Discord id (ADR-040/ADR-100)
    assert [e["is_claimed"] for e in body] == [False, True]
    assert "discord_id" not in body[0]
    assert "owner_discord_id" not in body[0]


# ---------- BRAWLISTAN home data (ADR-104) ----------


async def test_pakistan_rising_ranks_rating_gains(
    session_factory: async_sessionmaker[AsyncSession], client: TestClient
) -> None:
    from database.repositories.pakistan_board_repository import PakistanBoardRepository

    async with session_factory() as session:
        players = BrawlhallaPlayerRepository(session)
        board = PakistanBoardRepository(session)
        now = datetime.now(UTC)
        for bid, owner, before, after in ((10, 5, 1400, 1460), (20, None, 1500, 1620)):
            player = await players.upsert(
                brawlhalla_player_id=bid, player_name=f"P{bid}", region=None
            )
            await board.add(
                guild_id=GUILD_ID,
                player_id=player.id,
                added_by_discord_id=1,
                owner_discord_id=owner,
            )
            for days_ago, rating in ((5, before), (1, after)):
                await RankingSnapshotRepository(session).add(
                    RankingSnapshot(
                        brawlhalla_player_id=player.id,
                        captured_at=now - timedelta(days=days_ago),
                        rating=rating,
                        peak_rating=rating,
                        tier="Gold",
                        wins=1,
                        games=2,
                    )
                )
        await session.commit()

    body = client.get("/pakistan/rising?days=7").json()
    assert [(e["brawlhalla_id"], e["rating_gain"], e["rating"], e["is_claimed"]) for e in body] == [
        (20, 120, 1620, False),
        (10, 60, 1460, True),
    ]
    assert client.get("/pakistan/rising?days=0").status_code == 422


async def test_legend_meta_counts_board_and_linked_players_once(
    session_factory: async_sessionmaker[AsyncSession], client: TestClient
) -> None:
    from database.models.legend_snapshot import LegendSnapshot
    from database.repositories.legend_snapshot_repository import LegendSnapshotRepository
    from database.repositories.pakistan_board_repository import PakistanBoardRepository

    async with session_factory() as session:
        await _seed_linked_player(session)  # linked member, brawlhalla_id=10
        players = BrawlhallaPlayerRepository(session)
        linked = await players.get_by_brawlhalla_id(10)
        outsider = await players.upsert(brawlhalla_player_id=77, player_name="O", region=None)
        assert linked is not None
        board = PakistanBoardRepository(session)
        # the linked member is ALSO on the board: must still count once
        for player in (linked, outsider):
            await board.add(
                guild_id=GUILD_ID, player_id=player.id, added_by_discord_id=1, owner_discord_id=None
            )
            await LegendSnapshotRepository(session).add_all(
                [
                    LegendSnapshot(
                        brawlhalla_player_id=player.id,
                        captured_at=datetime.now(UTC),
                        legend_id=2,
                        legend_name_key="cassidy",
                        games=30,
                        wins=15,
                    )
                ]
            )
        await session.commit()

    (entry,) = client.get("/legends/meta").json()
    assert entry == {
        "legend_name_key": "cassidy",
        "player_count": 2,
        "total_games": 60,
        "win_rate": 50.0,
    }


async def test_rankings_endpoint_shape_and_no_discord_identity(
    session_factory: async_sessionmaker[AsyncSession], client: TestClient
) -> None:
    """ADR-105: one payload for every bracket tab, Brawlhalla identity only."""
    from database.repositories.pakistan_board_repository import PakistanBoardRepository

    async with session_factory() as session:
        player = await BrawlhallaPlayerRepository(session).upsert(
            brawlhalla_player_id=77, player_name="Outsider", region="SEA"
        )
        await PakistanBoardRepository(session).add(
            guild_id=GUILD_ID, player_id=player.id, added_by_discord_id=1, owner_discord_id=8
        )
        await RankingSnapshotRepository(session).add(
            RankingSnapshot(
                brawlhalla_player_id=player.id,
                captured_at=datetime.now(UTC),
                rating=1800,
                peak_rating=1850,
                tier="Diamond",
                wins=30,
                games=50,
                global_rank=4321,
                season=42,
                rating_2v2=1650,
                tier_2v2="Platinum 2",
                partner_2v2="Mate",
            )
        )
        await session.commit()

    body = client.get("/rankings/pakistan").json()
    assert (body["season"], body["seasons"]) == (42, [42])
    assert body["pakistan_season"]["name"] == "Markhor"
    (row,) = body["rows"]
    assert {k: row[k] for k in ("player_name", "country", "is_claimed", "global_rank")} == {
        "player_name": "Outsider",
        "country": "PK",
        "is_claimed": True,
        "global_rank": 4321,
    }
    assert (row["rating_2v2"], row["tier_2v2"], row["partner_2v2"]) == (1650, "Platinum 2", "Mate")
    assert "owner_discord_id" not in row and "discord_id" not in row
    assert client.get("/rankings/pakistan?season=0").status_code == 422


async def test_players_directory_and_seasons_endpoints(
    session_factory: async_sessionmaker[AsyncSession], client: TestClient
) -> None:
    """ADR-106: the directory and per-season summary, Brawlhalla identity only."""
    async with session_factory() as session:
        await _seed_linked_player(session)  # linked member, brawlhalla_id=10, "Foo"
        await session.commit()

    (entry,) = client.get("/players").json()
    assert (entry["brawlhalla_id"], entry["slug"], entry["team"], entry["is_claimed"]) == (
        10,
        "foo-10",
        None,  # linked, but on no team roster yet (ADR-114)
        True,
    )
    assert "discord_id" not in entry
    assert client.get("/players/10/seasons").status_code == 200
    assert client.get("/players/99999/seasons").status_code == 404


async def test_link_claim_endpoint(
    session_factory: async_sessionmaker[AsyncSession], client: TestClient
) -> None:
    """ADR-107: claim with a /link code; bad codes are 400, conflicts 409."""
    from api.routers.link import claim_limiter
    from services.link_code_service import LinkCodeService

    claim_limiter.reset()
    async with session_factory() as session:
        await BrawlhallaPlayerRepository(session).upsert(
            brawlhalla_player_id=77, player_name="Outsider", region=None
        )
        issued = await LinkCodeService(session).issue(guild_id=GUILD_ID, discord_id=555)
        await session.commit()

    bad = client.post("/link/claim", json={"brawlhalla_id": 77, "code": "ABCD-EFGH"})
    assert bad.status_code == 400
    ok = client.post("/link/claim", json={"brawlhalla_id": 77, "code": issued.code})
    assert ok.status_code == 200 and ok.json() == {"status": "linked", "player_name": "Outsider"}
    again = client.post("/link/claim", json={"brawlhalla_id": 77, "code": issued.code})
    assert again.status_code == 400  # single use
    assert client.post("/link/claim", json={"brawlhalla_id": 77, "code": ""}).status_code == 422

    # the directory now shows the claim, still without any Discord id
    (entry,) = client.get("/players").json()
    assert entry["is_claimed"] is True and "555" not in str(entry)


def test_link_claim_is_rate_limited(client: TestClient) -> None:
    from api.routers.link import claim_limiter

    claim_limiter.reset()
    statuses = [
        client.post("/link/claim", json={"brawlhalla_id": 1, "code": "ABCD-EFGH"}).status_code
        for _ in range(11)
    ]
    assert statuses[:10] == [400] * 10
    assert statuses[10] == 429
    claim_limiter.reset()


async def test_featured_player_is_404_until_staff_pick_one(
    session_factory: async_sessionmaker[AsyncSession], client: TestClient
) -> None:
    assert client.get("/featured").status_code == 404

    from services.featured_service import FeaturedService

    async with session_factory() as session:
        await BrawlhallaPlayerRepository(session).upsert(
            brawlhalla_player_id=77, player_name="Star", region=None
        )
        await FeaturedService(session).set(
            guild_id=GUILD_ID, brawlhalla_id=77, note="MVP", staff_discord_id=1
        )
        await session.commit()

    body = client.get("/featured").json()
    assert body["brawlhalla_id"] == 77
    assert body["player_name"] == "Star"
    assert body["note"] == "MVP"
    assert body["rating"] is None  # no snapshot yet: no number invented
    assert "discord_id" not in str(body)  # ADR-040


def test_seasons_list_and_details(client: TestClient) -> None:
    cards = client.get("/seasons").json()
    assert len(cards) >= 13
    assert cards[0]["season"]["number"] == 1 and cards[0]["season"]["name"] == "Markhor"
    assert {c["status"] for c in cards} <= {"past", "current", "upcoming"}

    current = client.get("/seasons/current")
    assert current.status_code == 200
    body = current.json()
    assert body["top"] == [] and body["rising"] is None  # empty DB: nothing invented
    assert body["has_data"] is False

    assert client.get("/seasons/42").status_code == 200
    assert client.get("/seasons/41").status_code == 422  # before Pakistan Season 1
    assert client.get("/seasons/abc").status_code == 422
    assert "discord" not in str(client.get("/seasons/42").json()).lower()


async def test_teams_endpoints(
    session_factory: async_sessionmaker[AsyncSession], client: TestClient
) -> None:
    from database.models.team import Team
    from database.repositories.team_repository import TeamRepository

    assert client.get("/teams").json() == []
    async with session_factory() as session:
        await _seed_linked_player(session)  # brawlhalla_id=10, "Foo"
        team = await TeamRepository(session).add(
            Team(
                guild_id=GUILD_ID,
                slug="delight-esports",
                name="Delight Esports",
                tag="DE",
                logo="delight-esports",
            )
        )
        foo = await BrawlhallaPlayerRepository(session).get_by_brawlhalla_id(10)
        assert foo is not None
        await TeamRepository(session).add_member(
            team_id=team.id, player_id=foo.id, role="captain", joined_at=datetime.now(UTC)
        )
        await session.commit()

    (summary,) = client.get("/teams").json()
    assert (summary["slug"], summary["members"], summary["logo"]) == (
        "delight-esports",
        1,
        "delight-esports",
    )
    detail = client.get("/teams/delight-esports").json()
    assert [(p["player_name"], p["role"], p["slug"]) for p in detail["roster"]] == [
        ("Foo", "captain", "foo-10")
    ]
    assert "discord" not in str(detail).lower()
    assert client.get("/teams/nope").status_code == 404
    assert client.get("/players").json()[0]["team_slug"] == "delight-esports"
