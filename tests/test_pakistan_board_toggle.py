"""Who is on the Pakistan rankings (docs/DECISIONS.md ADR-125): /link puts you
on, /pakistan join|leave is your toggle, Pakistani team rosters fill it, and
an opt-out or staff removal sticks."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import ShaheenError
from database.models.pakistan_board_entry import SOURCE_SELF, SOURCE_TEAM
from database.repositories.brawlhalla_player_repository import BrawlhallaPlayerRepository
from database.repositories.pakistan_board_repository import PakistanBoardRepository
from integrations.brawlhalla.models import PlayerRankedResponse, SearchResult
from services.link_service import LinkService
from services.pakistan_board_service import PakistanBoardService
from services.team_service import TeamService

GUILD = 1
ME = 100
STAFF = 9


class _FakeBrawlhalla:
    async def get_ranked(self, brawlhalla_id: int) -> PlayerRankedResponse | None:
        return PlayerRankedResponse(brawlhalla_id=brawlhalla_id, name="x", region="ME")


async def _link(session: AsyncSession, brawlhalla_id: int, discord_id: int = ME):
    service = LinkService(session, _FakeBrawlhalla())  # type: ignore[arg-type]
    return await service.link(
        guild_id=GUILD,
        discord_id=discord_id,
        joined_at=None,
        candidate=SearchResult(brawlhalla_id=brawlhalla_id, name=f"P{brawlhalla_id}"),
    )


async def _on_board(session: AsyncSession) -> dict[int, str]:
    """Brawlhalla id -> source, for every active entry."""
    rows = await PakistanBoardRepository(session).list_active(GUILD)
    return {player.brawlhalla_player_id: entry.source for entry, player in rows}


async def _team(session: AsyncSession, name: str, tag: str, *ids: int, country: str = "PK"):
    service = TeamService(session)
    team = await service.create(guild_id=GUILD, name=name, tag=tag, actor_discord_id=STAFF)
    team.country = country
    for brawlhalla_id in ids:
        await BrawlhallaPlayerRepository(session).upsert(
            brawlhalla_player_id=brawlhalla_id, player_name=f"P{brawlhalla_id}", region=None
        )
        await service.add_member(
            team, brawlhalla_id=brawlhalla_id, actor_discord_id=STAFF, is_staff=True
        )
    return team


async def test_link_puts_you_on_and_leave_is_remembered(session: AsyncSession) -> None:
    outcome = await _link(session, 111)
    assert outcome.on_pakistan_board
    assert await _on_board(session) == {111: SOURCE_SELF}

    board = PakistanBoardService(session)
    left = await board.leave(guild_id=GUILD, discord_id=ME)
    assert left is not None and await _on_board(session) == {}

    # Linking again doesn't override the opt-out...
    assert not (await _link(session, 111)).on_pakistan_board
    assert await _on_board(session) == {}
    # ...but /pakistan join with no ID (the linked account) does.
    joined = await board.join_linked(guild_id=GUILD, discord_id=ME)
    assert joined.player.brawlhalla_player_id == 111
    assert await _on_board(session) == {111: SOURCE_SELF}


async def test_join_without_an_id_needs_a_link(session: AsyncSession) -> None:
    with pytest.raises(ShaheenError, match="/link"):
        await PakistanBoardService(session).join_linked(guild_id=GUILD, discord_id=ME)


async def test_relinking_another_account_moves_your_spot(session: AsyncSession) -> None:
    await _link(session, 111)
    await _link(session, 222)
    assert await _on_board(session) == {222: SOURCE_SELF}


async def test_pakistani_team_rosters_fill_the_board(session: AsyncSession) -> None:
    pk = await _team(session, "Delight Esports", "DE", 1, 2, 3)
    await _team(session, "Abroad", "AB", 4, country="AE")
    board = PakistanBoardService(session)

    first = await board.sync_team_rosters(GUILD)
    assert (first.added, first.removed) == (3, 0)
    assert await _on_board(session) == {1: SOURCE_TEAM, 2: SOURCE_TEAM, 3: SOURCE_TEAM}
    assert (await board.sync_team_rosters(GUILD)).added == 0  # idempotent

    # Leaving the team takes off what the sync added...
    await TeamService(session).remove_member(
        pk, brawlhalla_id=3, actor_discord_id=STAFF, is_staff=True
    )
    assert (await board.sync_team_rosters(GUILD)).removed == 1
    assert set(await _on_board(session)) == {1, 2}


async def test_opt_outs_and_staff_removals_stick(session: AsyncSession) -> None:
    await _team(session, "Delight Esports", "DE", 1, 2)
    board = PakistanBoardService(session)
    await board.sync_team_rosters(GUILD)

    # A linked team player opts out: their entry came from the roster, not them.
    await _link(session, 1)
    await board.leave(guild_id=GUILD, discord_id=ME)
    await board.remove(guild_id=GUILD, brawlhalla_id=2)  # staff
    assert await _on_board(session) == {}

    assert (await board.sync_team_rosters(GUILD)).added == 0
    assert await _on_board(session) == {}


async def test_a_claimed_entry_stays_when_the_player_leaves_the_team(
    session: AsyncSession,
) -> None:
    team = await _team(session, "Delight Esports", "DE", 1)
    board = PakistanBoardService(session)
    await board.sync_team_rosters(GUILD)
    await _link(session, 1)  # claims the team's entry

    await TeamService(session).remove_member(
        team, brawlhalla_id=1, actor_discord_id=STAFF, is_staff=True
    )
    assert (await board.sync_team_rosters(GUILD)).removed == 0
    assert set(await _on_board(session)) == {1}


async def test_team_entries_dont_count_towards_the_cap(session: AsyncSession) -> None:
    await _team(session, "Delight Esports", "DE", 1, 2, 3)
    board = PakistanBoardService(session)
    await board.sync_team_rosters(GUILD)
    assert await PakistanBoardRepository(session).count_active(GUILD) == 0
