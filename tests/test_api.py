"""FastAPI integration tests — routing, dependency wiring, serialization.

Dependencies are overridden to use the sqlite test session instead of a
real Postgres connection; no live server or Discord/Brawlhalla access
is involved.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime

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
    assert response.json() == {"status": "ok"}


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
        catalog: dict[str, Achievement] = {}
        for definition in CATALOG:
            row = Achievement(
                key=definition.key, name=definition.name, description=definition.description
            )
            session.add(row)
            catalog[definition.key] = row
        await session.flush()

        users = DiscordUserRepository(session)
        members = ShaheenMemberRepository(session)
        user = await users.get_or_create(1)
        member = await members.get_or_create(discord_user_id=user.id, guild_id=GUILD_ID)
        await MemberAchievementRepository(session).award(
            shaheen_member_id=member.id, achievement_id=catalog["games_100"].id
        )
        await session.commit()

    response = client.get("/achievements")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == len(CATALOG)  # every catalog entry, not just earned ones
    by_key = {entry["key"]: entry for entry in body}
    assert by_key["games_100"]["holder_count"] == 1
    assert by_key["games_100"]["total_members"] == 1
    assert by_key["games_100"]["completion_pct"] == 100.0
    assert by_key["games_500"]["holder_count"] == 0
