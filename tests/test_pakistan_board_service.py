"""The Pakistan leaderboard service (docs/DECISIONS.md ADR-099)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import ShaheenError
from database.models.ranking_snapshot import RankingSnapshot
from database.repositories.brawlhalla_player_repository import BrawlhallaPlayerRepository
from database.repositories.discord_user_repository import DiscordUserRepository
from database.repositories.member_player_link_repository import MemberPlayerLinkRepository
from database.repositories.pakistan_board_repository import PakistanBoardRepository
from database.repositories.ranking_snapshot_repository import RankingSnapshotRepository
from database.repositories.shaheen_member_repository import ShaheenMemberRepository
from integrations.brawlhalla.models import SearchResult
from services import pakistan_board_service
from services.pakistan_board_service import PakistanBoardService

GUILD_ID = 1


def _candidate(brawlhalla_id: int, name: str | None = None) -> SearchResult:
    return SearchResult(brawlhalla_id=brawlhalla_id, name=name or f"P{brawlhalla_id}")


async def _rate(
    session: AsyncSession,
    brawlhalla_id: int,
    rating: int,
    season: int = 5,
    captured_at: datetime | None = None,
) -> None:
    player = await BrawlhallaPlayerRepository(session).get_by_brawlhalla_id(brawlhalla_id)
    assert player is not None
    await RankingSnapshotRepository(session).add(
        RankingSnapshot(
            brawlhalla_player_id=player.id,
            captured_at=captured_at or datetime.now(UTC),
            rating=rating,
            peak_rating=rating,
            tier="Gold",
            wins=1,
            games=2,
            season=season,
        )
    )


async def test_join_adds_the_member_and_rejoining_the_same_account_is_rejected(
    session: AsyncSession,
) -> None:
    service = PakistanBoardService(session)
    outcome = await service.join(guild_id=GUILD_ID, discord_id=7, candidate=_candidate(10))
    assert outcome.player.brawlhalla_player_id == 10
    assert outcome.replaced_player_name is None
    with pytest.raises(ShaheenError):
        await service.join(guild_id=GUILD_ID, discord_id=7, candidate=_candidate(10))


async def test_joining_with_another_account_replaces_the_old_entry(session: AsyncSession) -> None:
    service = PakistanBoardService(session)
    await service.join(guild_id=GUILD_ID, discord_id=7, candidate=_candidate(10, "Old"))
    outcome = await service.join(guild_id=GUILD_ID, discord_id=7, candidate=_candidate(20))
    assert outcome.replaced_player_name == "Old"
    active = await PakistanBoardRepository(session).list_active(GUILD_ID)
    assert [player.brawlhalla_player_id for _e, player in active] == [20]


async def test_staff_add_needs_no_member_and_a_later_join_claims_it(
    session: AsyncSession,
) -> None:
    service = PakistanBoardService(session)
    await service.add(guild_id=GUILD_ID, added_by_discord_id=1, candidate=_candidate(30))
    with pytest.raises(ShaheenError):
        await service.add(guild_id=GUILD_ID, added_by_discord_id=1, candidate=_candidate(30))

    await service.join(guild_id=GUILD_ID, discord_id=8, candidate=_candidate(30))
    entry = await PakistanBoardRepository(session).get_active_for_owner(GUILD_ID, 8)
    assert entry is not None
    with pytest.raises(ShaheenError):  # now owned by member 8, not claimable by 9
        await service.join(guild_id=GUILD_ID, discord_id=9, candidate=_candidate(30))


async def test_leave_and_remove(session: AsyncSession) -> None:
    service = PakistanBoardService(session)
    await service.join(guild_id=GUILD_ID, discord_id=7, candidate=_candidate(10))
    await service.add(guild_id=GUILD_ID, added_by_discord_id=1, candidate=_candidate(30))

    left = await service.leave(guild_id=GUILD_ID, discord_id=7)
    assert left is not None and left.brawlhalla_player_id == 10
    assert await service.leave(guild_id=GUILD_ID, discord_id=7) is None

    removed = await service.remove(guild_id=GUILD_ID, brawlhalla_id=30)
    assert removed is not None
    assert await service.remove(guild_id=GUILD_ID, brawlhalla_id=30) is None
    assert await PakistanBoardRepository(session).count_active(GUILD_ID) == 0


async def test_board_is_capped(session: AsyncSession, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pakistan_board_service, "MAX_PAKISTAN_BOARD", 1)
    service = PakistanBoardService(session)
    await service.add(guild_id=GUILD_ID, added_by_discord_id=1, candidate=_candidate(30))
    with pytest.raises(ShaheenError):
        await service.join(guild_id=GUILD_ID, discord_id=7, candidate=_candidate(10))


async def test_leaderboard_is_season_scoped_sorted_and_flags_clan_members(
    session: AsyncSession,
) -> None:
    service = PakistanBoardService(session)
    for brawlhalla_id in (10, 20, 30):
        await service.add(
            guild_id=GUILD_ID, added_by_discord_id=1, candidate=_candidate(brawlhalla_id)
        )
    await _rate(session, 10, 1400)
    await _rate(session, 20, 1900)
    await _rate(session, 30, 2500, season=4)  # last season only — must not rank

    # player 20 is also a clan member
    user = await DiscordUserRepository(session).get_or_create(50)
    member = await ShaheenMemberRepository(session).get_or_create(
        discord_user_id=user.id, guild_id=GUILD_ID
    )
    player_20 = await BrawlhallaPlayerRepository(session).get_by_brawlhalla_id(20)
    assert player_20 is not None
    await MemberPlayerLinkRepository(session).link(
        shaheen_member_id=member.id, brawlhalla_player_id=player_20.id
    )

    rows = await service.leaderboard(GUILD_ID)
    assert [(r.player.brawlhalla_player_id, r.is_clan_member) for r in rows] == [
        (20, True),
        (10, False),
    ]


# ---------- claimed spots, the Top 10 role and weekly climbers (ADR-100) ----------


async def test_rows_report_whether_the_spot_is_claimed(session: AsyncSession) -> None:
    service = PakistanBoardService(session)
    await service.join(guild_id=GUILD_ID, discord_id=7, candidate=_candidate(10))
    await service.add(guild_id=GUILD_ID, added_by_discord_id=1, candidate=_candidate(20))
    await _rate(session, 10, 1400)
    await _rate(session, 20, 1900)

    rows = await service.leaderboard(GUILD_ID)
    assert [(r.player.brawlhalla_player_id, r.is_claimed) for r in rows] == [
        (20, False),
        (10, True),
    ]


async def test_top_role_goes_only_to_claimed_players_inside_the_top_places(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(pakistan_board_service, "PAKISTAN_TOP_ROLE_SIZE", 2)
    service = PakistanBoardService(session)
    await service.add(guild_id=GUILD_ID, added_by_discord_id=1, candidate=_candidate(10))
    await service.join(guild_id=GUILD_ID, discord_id=7, candidate=_candidate(20))
    await service.join(guild_id=GUILD_ID, discord_id=8, candidate=_candidate(30))
    await _rate(session, 10, 2200)  # 1st but unclaimed: keeps the place, no role
    await _rate(session, 20, 2000)  # 2nd, claimed: gets it
    await _rate(session, 30, 1500)  # 3rd: outside the top 2

    assert await service.top_role_earners(GUILD_ID) == {7}


async def test_climbers_rank_rating_gains_inside_the_window(session: AsyncSession) -> None:
    service = PakistanBoardService(session)
    await service.join(guild_id=GUILD_ID, discord_id=7, candidate=_candidate(10))
    await service.add(guild_id=GUILD_ID, added_by_discord_id=1, candidate=_candidate(20))
    await service.add(guild_id=GUILD_ID, added_by_discord_id=1, candidate=_candidate(30))
    now = datetime.now(UTC)
    since = now - timedelta(days=7)
    for brawlhalla_id, before, after in ((10, 1400, 1450), (20, 1500, 1620), (30, 1800, 1700)):
        await _rate(session, brawlhalla_id, before, captured_at=now - timedelta(days=5))
        await _rate(session, brawlhalla_id, after, captured_at=now - timedelta(days=1))
    # a gain from before the window doesn't count
    await _rate(session, 10, 900, captured_at=now - timedelta(days=10))

    climbers = await service.climbers(GUILD_ID, since=since)
    assert [
        (c.player.brawlhalla_player_id, c.rating_gain, c.owner_discord_id) for c in climbers
    ] == [(20, 120, None), (10, 50, 7)]
