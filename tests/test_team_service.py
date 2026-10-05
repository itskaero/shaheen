"""Teams (docs/DECISIONS.md ADR-114): rules, permissions and the numbers."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import ConflictError, NotFoundError, PermissionDeniedError, ShaheenError
from database.models.audit_log import AuditLogEntry
from database.models.ranking_snapshot import RankingSnapshot
from database.models.team import Team, TeamMember
from database.repositories.brawlhalla_player_repository import BrawlhallaPlayerRepository
from database.repositories.discord_user_repository import DiscordUserRepository
from database.repositories.member_player_link_repository import MemberPlayerLinkRepository
from database.repositories.ranking_snapshot_repository import RankingSnapshotRepository
from database.repositories.shaheen_member_repository import ShaheenMemberRepository
from services.team_service import TeamService, team_rating, team_slug

GUILD = 1
STAFF = 999


async def _player(
    session: AsyncSession, bid: int, rating: int | None = None, season: int = 42
) -> int:
    player = await BrawlhallaPlayerRepository(session).upsert(
        brawlhalla_player_id=bid, player_name=f"P{bid}", region=None
    )
    if rating is not None:
        await RankingSnapshotRepository(session).add(
            RankingSnapshot(
                brawlhalla_player_id=player.id,
                captured_at=datetime.now(UTC),
                rating=rating,
                peak_rating=rating,
                tier="Gold",
                wins=1,
                games=2,
                season=season,
            )
        )
    return player.id


async def _link(session: AsyncSession, discord_id: int, player_id: int) -> None:
    user = await DiscordUserRepository(session).get_or_create(discord_id)
    member = await ShaheenMemberRepository(session).get_or_create(
        discord_user_id=user.id, guild_id=GUILD
    )
    await MemberPlayerLinkRepository(session).link(
        shaheen_member_id=member.id, brawlhalla_player_id=player_id
    )


async def _team(service: TeamService, name: str = "Delight Esports", tag: str = "DE") -> Team:
    return await service.create(guild_id=GUILD, name=name, tag=tag, actor_discord_id=STAFF)


def test_slug_and_team_rating() -> None:
    assert team_slug("Delight Esports!") == "delight-esports"
    assert team_slug("Ünïcode  Kings") == "unicode-kings"
    assert team_rating([2000, None, 1800, 1600, 1000]) == 1800  # best three
    assert team_rating([None, None]) is None
    assert team_rating([]) is None


async def test_create_validates_and_rejects_duplicates(session: AsyncSession) -> None:
    service = TeamService(session)
    team = await _team(service)
    assert (team.slug, team.tag, team.is_founding) == ("delight-esports", "DE", False)
    with pytest.raises(ConflictError):
        await service.create(guild_id=GUILD, name="delight esports", tag="DX", actor_discord_id=1)
    with pytest.raises(ConflictError):
        await service.create(guild_id=GUILD, name="Other", tag="de", actor_discord_id=1)
    with pytest.raises(ShaheenError):
        await service.create(guild_id=GUILD, name="X", tag="XX", actor_discord_id=1)
    with pytest.raises(ShaheenError):
        await service.create(guild_id=GUILD, name="Valid", tag="toolong!", actor_discord_id=1)


async def test_one_team_at_a_time_and_history_is_kept(session: AsyncSession) -> None:
    service = TeamService(session)
    delight = await _team(service)
    other = await _team(service, "Karachi Kings", "KK")
    await _player(session, 10)
    await service.add_member(delight, brawlhalla_id=10, actor_discord_id=STAFF, is_staff=True)
    with pytest.raises(ConflictError):
        await service.add_member(delight, brawlhalla_id=10, actor_discord_id=STAFF, is_staff=True)
    with pytest.raises(ConflictError):
        await service.add_member(other, brawlhalla_id=10, actor_discord_id=STAFF, is_staff=True)
    with pytest.raises(NotFoundError):
        await service.add_member(delight, brawlhalla_id=404, actor_discord_id=STAFF, is_staff=True)

    await service.remove_member(delight, brawlhalla_id=10, actor_discord_id=STAFF, is_staff=True)
    await service.add_member(other, brawlhalla_id=10, actor_discord_id=STAFF, is_staff=True)
    rows = (await session.execute(select(TeamMember))).scalars().all()
    assert [(r.team_id, r.left_at is None) for r in rows] == [(delight.id, False), (other.id, True)]
    actions = [a.action for a in (await session.execute(select(AuditLogEntry))).scalars()]
    assert actions.count("team.add") == 2 and "team.remove" in actions


async def test_captains_manage_only_their_own_team(session: AsyncSession) -> None:
    service = TeamService(session)
    delight = await _team(service)
    other = await _team(service, "Karachi Kings", "KK")
    captain = await _player(session, 10)
    await _player(session, 20)
    await _link(session, 7, captain)
    await service.add_member(delight, brawlhalla_id=10, actor_discord_id=STAFF, is_staff=True)
    await service.set_captain(delight, brawlhalla_id=10, actor_discord_id=STAFF)

    assert await service.can_manage(delight, discord_id=7, is_staff=False)
    assert not await service.can_manage(other, discord_id=7, is_staff=False)
    assert not await service.can_manage(delight, discord_id=8, is_staff=False)
    assert await service.can_manage(other, discord_id=8, is_staff=True)

    await service.add_member(delight, brawlhalla_id=20, actor_discord_id=7, is_staff=False)
    with pytest.raises(PermissionDeniedError):
        await service.remove_member(delight, brawlhalla_id=20, actor_discord_id=8, is_staff=False)

    # Only one captain: naming another demotes the first.
    await service.set_captain(delight, brawlhalla_id=20, actor_discord_id=STAFF)
    roles = {
        m.brawlhalla_player_id: m.role
        for m in (await session.execute(select(TeamMember))).scalars()
    }
    assert sorted(roles.values()) == ["captain", "player"]
    with pytest.raises(NotFoundError):
        await service.set_captain(other, brawlhalla_id=20, actor_discord_id=STAFF)


async def test_leave(session: AsyncSession) -> None:
    service = TeamService(session)
    delight = await _team(service)
    pid = await _player(session, 10)
    await service.add_member(delight, brawlhalla_id=10, actor_discord_id=STAFF, is_staff=True)
    player = await BrawlhallaPlayerRepository(session).get_by_id(pid)
    assert player is not None
    left = await service.leave(guild_id=GUILD, player=player, actor_discord_id=7)
    assert left.id == delight.id
    with pytest.raises(NotFoundError):
        await service.leave(guild_id=GUILD, player=player, actor_discord_id=7)


async def test_overview_puts_the_founding_team_first_then_rating(session: AsyncSession) -> None:
    service = TeamService(session)
    session.add(Team(guild_id=GUILD, slug="shaheen", name="SHAHEEN", tag="SHN", is_founding=True))
    await session.flush()
    delight = await _team(service)
    empty = await _team(service, "Empty Squad", "ES")
    shaheen = await service.get(GUILD, "shaheen")
    await _player(session, 10, 1500)
    await _player(session, 20, 2200)
    await _player(session, 30, 2000)
    await _player(session, 40)  # unplaced
    await service.add_member(shaheen, brawlhalla_id=10, actor_discord_id=STAFF, is_staff=True)
    for bid in (20, 30, 40):
        await service.add_member(delight, brawlhalla_id=bid, actor_discord_id=STAFF, is_staff=True)

    overview = await service.overview(GUILD)

    assert [s.team.slug for s in overview] == ["shaheen", "delight-esports", "empty-squad"]
    by_slug = {s.team.slug: s for s in overview}
    assert (by_slug["delight-esports"].members, by_slug["delight-esports"].rating) == (3, 2100)
    assert by_slug["delight-esports"].best is not None
    assert by_slug["delight-esports"].best.player.player_name == "P20"
    assert (by_slug["empty-squad"].rating, by_slug["empty-squad"].best) == (None, None)
    assert empty.id != delight.id


async def test_detail_roster_and_season_results(session: AsyncSession) -> None:
    service = TeamService(session)
    delight = await _team(service)
    await _player(session, 10, 1500)
    await _player(session, 20, 1900)
    await _player(session, 20, None)  # same player, no extra reading
    for bid in (10, 20):
        await service.add_member(delight, brawlhalla_id=bid, actor_discord_id=STAFF, is_staff=True)
    await service.set_captain(delight, brawlhalla_id=10, actor_discord_id=STAFF)

    detail = await service.detail(GUILD, "delight-esports")

    assert detail is not None
    assert [e.player.player_name for e in detail.roster] == ["P10", "P20"]  # captain first
    assert detail.captain is not None and detail.captain.player.player_name == "P10"
    (s42,) = detail.seasons
    assert (s42.season, s42.best, s42.average, s42.players) == (42, 1900, 1700, 2)
    assert await service.detail(GUILD, "nope") is None


async def test_players_choose_whether_to_wear_their_tag(session: AsyncSession) -> None:
    from database.models.pakistan_board_entry import PakistanBoardEntry  # noqa: F401
    from database.repositories.pakistan_board_repository import PakistanBoardRepository
    from services.rankings_service import RankingsService

    service = TeamService(session)
    delight = await _team(service)
    pid = await _player(session, 10, 1900)
    await PakistanBoardRepository(session).add(
        guild_id=GUILD, player_id=pid, added_by_discord_id=1, owner_discord_id=None
    )
    await service.add_member(delight, brawlhalla_id=10, actor_discord_id=STAFF, is_staff=True)

    async def tag() -> str | None:
        (row,) = (await RankingsService(session).pakistan(GUILD)).rows
        return row.team_tag

    assert await tag() == "DE"  # on by default
    player = await BrawlhallaPlayerRepository(session).get_by_id(pid)
    assert player is not None
    await service.set_show_tag(guild_id=GUILD, player=player, show=False, actor_discord_id=7)
    assert await tag() is None
    (row,) = (await RankingsService(session).pakistan(GUILD)).rows
    assert row.team == "Delight Esports"  # still on the team, just not wearing the tag
    await service.set_show_tag(guild_id=GUILD, player=player, show=True, actor_discord_id=7)
    assert await tag() == "DE"

    other = await BrawlhallaPlayerRepository(session).upsert(
        brawlhalla_player_id=20, player_name="Solo", region=None
    )
    with pytest.raises(NotFoundError):
        await service.set_show_tag(guild_id=GUILD, player=other, show=True, actor_discord_id=8)
