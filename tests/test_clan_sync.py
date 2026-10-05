"""Teams mirror in-game Brawlhalla clans (docs/DECISIONS.md ADR-120): the
rate limiter, name repair, the sync rules and the snapshot tick."""

from __future__ import annotations

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.ranking_snapshot import RankingSnapshot
from database.models.team import Team, TeamMember
from database.repositories.brawlhalla_player_repository import BrawlhallaPlayerRepository
from database.repositories.pakistan_board_repository import PakistanBoardRepository
from database.repositories.team_repository import TeamRepository
from integrations.brawlhalla.client import RateLimiter
from integrations.brawlhalla.models import ClanResponse, PlayerRankedResponse, PlayerStatsResponse
from services.snapshot_service import SnapshotService
from services.team_service import TeamService

GUILD = 1
STAFF = 999


def _clan(clan_id: int, *members: tuple[int, str, str]) -> ClanResponse:
    return ClanResponse.model_validate(
        {
            "clan_id": clan_id,
            "clan_name": f"Clan {clan_id}",
            "clan": [{"brawlhalla_id": b, "name": n, "rank": r, "xp": 1} for b, n, r in members],
        }
    )


async def _team(session: AsyncSession, slug: str, clan_id: int | None = None) -> Team:
    return await TeamRepository(session).add(
        Team(
            guild_id=GUILD,
            slug=slug,
            name=slug.title(),
            tag=slug[:3].upper(),
            brawlhalla_clan_id=clan_id,
        )
    )


async def _active(session: AsyncSession, team: Team) -> dict[str, tuple[str, str, str | None]]:
    return {
        p.player_name: (m.role, m.source, m.clan_rank)
        for m, p in await TeamRepository(session).active_members(team.id)
    }


# --- rate limiter -------------------------------------------------------------


def test_rate_limiter_waits_for_the_window_and_the_spacing() -> None:
    clock = [0.0]
    slept: list[float] = []

    async def sleep(seconds: float) -> None:
        slept.append(round(seconds, 3))
        clock[0] += seconds

    limiter = RateLimiter(3, 10.0, 0.5, clock=lambda: clock[0], sleep=sleep)

    async def run() -> None:
        for _ in range(4):
            await limiter.acquire()

    asyncio.run(run())
    # Two 0.5 s spacings, then the 4th call waits until the 1st leaves the window.
    assert slept == [0.5, 0.5, 9.0]


# --- name repair ----------------------------------------------------------------


def test_clan_names_are_repaired() -> None:
    clan = ClanResponse.model_validate(
        {
            "clan_id": 1,
            "clan_name": "revenantwolf",
            "clan": [
                {"brawlhalla_id": 5, "name": "WÃ\u0098LF", "rank": "Leader"},
                {"brawlhalla_id": 6, "name": "plain", "rank": "Member"},
            ],
        }
    )
    assert [m.name for m in clan.members] == ["WØLF", "plain"]
    stats = PlayerStatsResponse(brawlhalla_id=5, name="WÃ\u0098LF")
    assert stats.name == "WØLF"


# --- sync rules -------------------------------------------------------------------


async def test_sync_adds_members_and_makes_the_leader_captain(session: AsyncSession) -> None:
    team = await _team(session, "monke", 77)
    service = TeamService(session)
    result = await service.sync_clan(
        team, _clan(77, (1, "Boss", "Leader"), (2, "Officer1", "Officer"), (3, "Rookie", "Recruit"))
    )
    assert sorted(result.added) == ["Boss", "Officer1", "Rookie"]
    assert await _active(session, team) == {
        "Boss": ("captain", "clan", "Leader"),
        "Officer1": ("player", "clan", "Officer"),
        "Rookie": ("player", "clan", "Recruit"),
    }


async def test_resync_removes_leavers_keeps_manual_adds_and_updates_ranks(
    session: AsyncSession,
) -> None:
    team = await _team(session, "wolf", 88)
    service = TeamService(session)
    await service.sync_clan(team, _clan(88, (1, "Alpha", "Leader"), (2, "Beta", "Recruit")))
    await BrawlhallaPlayerRepository(session).upsert(
        brawlhalla_player_id=50, player_name="Guest", region=None
    )
    await service.add_member(team, brawlhalla_id=50, actor_discord_id=STAFF, is_staff=True)

    result = await service.sync_clan(
        team, _clan(88, (1, "Alpha", "Leader"), (3, "Gamma", "Member"), (2, "Beta", "Officer"))
    )
    assert result.kept == 2 and result.added == ["Gamma"] and result.removed == []

    result = await service.sync_clan(
        team, _clan(88, (1, "Alpha", "Leader"), (3, "Gamma", "Member"))
    )
    assert result.removed == ["Beta"]
    active = await _active(session, team)
    assert set(active) == {"Alpha", "Gamma", "Guest"}  # the manual add stays
    assert active["Guest"][1] == "manual"
    history = (
        (await session.execute(select(TeamMember).where(TeamMember.left_at.is_not(None))))
        .scalars()
        .all()
    )
    assert len(history) == 1  # Beta's membership is closed, not deleted


async def test_a_player_who_switched_clans_moves_but_manual_picks_stay(
    session: AsyncSession,
) -> None:
    red = await _team(session, "red", 1)
    blue = await _team(session, "blue", 2)
    hand = await _team(session, "hand")
    service = TeamService(session)
    await service.sync_clan(red, _clan(1, (10, "Switcher", "Member")))
    await BrawlhallaPlayerRepository(session).upsert(
        brawlhalla_player_id=20, player_name="Picked", region=None
    )
    await service.add_member(hand, brawlhalla_id=20, actor_discord_id=STAFF, is_staff=True)

    result = await service.sync_clan(
        blue, _clan(2, (10, "Switcher", "Member"), (20, "Picked", "Member"))
    )

    assert result.moved == ["Switcher"] and result.added == []
    assert result.skipped == ["Picked (Hand)"]
    assert set(await _active(session, blue)) == {"Switcher"}
    assert set(await _active(session, red)) == set()
    assert set(await _active(session, hand)) == {"Picked"}


async def test_sync_renames_players_without_touching_their_region(session: AsyncSession) -> None:
    await BrawlhallaPlayerRepository(session).upsert(
        brawlhalla_player_id=7, player_name="Old", region="ASIA"
    )
    team = await _team(session, "renamers", 3)
    await TeamService(session).sync_clan(team, _clan(3, (7, "New", "Member")))
    player = await BrawlhallaPlayerRepository(session).get_by_brawlhalla_id(7)
    assert player is not None and (player.player_name, player.region) == ("New", "ASIA")


# --- the snapshot tick --------------------------------------------------------------


class _FakeBrawlhalla:
    def __init__(self, clans: dict[int, ClanResponse]) -> None:
        self.clans = clans
        self.snapshotted: list[int] = []

    async def get_clan(self, clan_id: int) -> ClanResponse:
        return self.clans[clan_id]

    async def get_stats(self, brawlhalla_id: int) -> PlayerStatsResponse:
        self.snapshotted.append(brawlhalla_id)
        return PlayerStatsResponse(brawlhalla_id=brawlhalla_id, name=f"P{brawlhalla_id}")

    async def get_ranked(self, brawlhalla_id: int) -> PlayerRankedResponse | None:
        return PlayerRankedResponse(
            brawlhalla_id=brawlhalla_id,
            name=f"P{brawlhalla_id}",
            tier="Gold 3",
            rating=1500 + brawlhalla_id,
            peak_rating=1600,
            wins=5,
            games=10,
            region="ASIA",
        )


async def test_snapshot_tick_syncs_clans_and_rates_their_players(session: AsyncSession) -> None:
    team = await _team(session, "sigma", 1777529)
    fake = _FakeBrawlhalla({1777529: _clan(1777529, (31, "Sig", "Leader"), (32, "Ma", "Recruit"))})

    result = await SnapshotService(session, fake, season=42).run_for_guild(GUILD)  # type: ignore[arg-type]

    assert [s.team.slug for s in result.clan_syncs] == ["sigma"]
    assert sorted(fake.snapshotted) == [31, 32]
    assert result.players_processed == 2
    ratings = (await session.execute(select(RankingSnapshot.rating))).scalars().all()
    assert sorted(ratings) == [1531, 1532]
    summary = next(s for s in await TeamService(session).overview(GUILD) if s.team.id == team.id)
    assert (summary.members, summary.rating) == (2, 1532)
    # A Pakistani team's roster lands on the Pakistan rankings (ADR-125),
    # snapshotted once (not again as board players).
    assert result.board_sync.added == 2
    board = await PakistanBoardRepository(session).list_active(GUILD)
    assert sorted(player.brawlhalla_player_id for _e, player in board) == [31, 32]
