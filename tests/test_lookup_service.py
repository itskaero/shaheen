"""LookupService: unlinked rank probe with clan context (ADR-083).

The point of /lookup isn't the raw rating — it's where that rating would
sit against Shaheen's own ladder — so these cover the clan half as much as
the fetch half, plus the guarantee that nothing is written.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import NotFoundError
from database.models.member_player_link import MemberPlayerLink
from database.models.ranking_snapshot import RankingSnapshot
from database.repositories.brawlhalla_player_repository import BrawlhallaPlayerRepository
from database.repositories.discord_user_repository import DiscordUserRepository
from database.repositories.member_player_link_repository import MemberPlayerLinkRepository
from database.repositories.ranking_snapshot_repository import RankingSnapshotRepository
from database.repositories.shaheen_member_repository import ShaheenMemberRepository
from integrations.brawlhalla.errors import BrawlhallaNotFound
from integrations.brawlhalla.models import (
    PlayerRankedResponse,
    PlayerStatsResponse,
    SearchResult,
)
from services.lookup_service import LookupService

GUILD_ID = 1


class _FakeBrawlhalla:
    def __init__(self, *, rating: int | None = 1600, known: bool = True) -> None:
        self.rating = rating
        self.known = known

    async def resolve_identifier(self, identifier: str) -> SearchResult:
        if not self.known:
            raise BrawlhallaNotFound(f"No Brawlhalla account found for {identifier}.")
        return SearchResult(brawlhalla_id=777, name="Stranger")

    async def get_stats(self, brawlhalla_id: int) -> PlayerStatsResponse:
        return PlayerStatsResponse(
            brawlhalla_id=brawlhalla_id, name="Stranger", games=400, wins=220, level=42
        )

    async def get_ranked(self, brawlhalla_id: int) -> PlayerRankedResponse | None:
        if self.rating is None:
            return None
        return PlayerRankedResponse(
            brawlhalla_id=brawlhalla_id,
            name="Stranger",
            tier="Diamond",
            rating=self.rating,
            peak_rating=self.rating + 50,
            wins=120,
            games=200,
        )


async def _linked_member_with_rating(
    session: AsyncSession, *, discord_id: int, brawlhalla_id: int, rating: int
) -> None:
    user = await DiscordUserRepository(session).get_or_create(discord_id)
    member = await ShaheenMemberRepository(session).get_or_create(
        discord_user_id=user.id, guild_id=GUILD_ID
    )
    player = await BrawlhallaPlayerRepository(session).upsert(
        brawlhalla_player_id=brawlhalla_id, player_name=f"P{brawlhalla_id}", region=None
    )
    await MemberPlayerLinkRepository(session).link(
        shaheen_member_id=member.id, brawlhalla_player_id=player.id
    )
    await RankingSnapshotRepository(session).add(
        RankingSnapshot(
            brawlhalla_player_id=player.id,
            captured_at=datetime.now(UTC),
            rating=rating,
            peak_rating=rating,
            tier="Gold",
            wins=10,
            games=20,
        )
    )


async def test_lookup_places_the_player_against_the_clan(session: AsyncSession) -> None:
    await _linked_member_with_rating(session, discord_id=1, brawlhalla_id=10, rating=1800)
    await _linked_member_with_rating(session, discord_id=2, brawlhalla_id=20, rating=1400)

    result = await LookupService(session, _FakeBrawlhalla(rating=1600)).lookup(  # type: ignore[arg-type]
        guild_id=GUILD_ID, identifier="777"
    )

    assert result.player_name == "Stranger"
    assert result.brawlhalla_id == 777
    assert result.clan_context is not None
    assert result.clan_context.would_be_rank == 2
    assert result.clan_context.above == ("P10", 1800)
    assert result.clan_context.below == ("P20", 1400)


async def test_lookup_writes_nothing(session: AsyncSession) -> None:
    """A probe must not create a member, a player row, or a link."""
    await LookupService(session, _FakeBrawlhalla()).lookup(  # type: ignore[arg-type]
        guild_id=GUILD_ID, identifier="777"
    )

    links = await session.execute(select(func.count()).select_from(MemberPlayerLink))
    assert links.scalar_one() == 0
    player = await BrawlhallaPlayerRepository(session).get_by_brawlhalla_id(777)
    assert player is None


async def test_lookup_without_ranked_data_has_no_clan_context(session: AsyncSession) -> None:
    await _linked_member_with_rating(session, discord_id=1, brawlhalla_id=10, rating=1800)

    result = await LookupService(session, _FakeBrawlhalla(rating=None)).lookup(  # type: ignore[arg-type]
        guild_id=GUILD_ID, identifier="777"
    )

    assert result.ranked is None
    assert result.clan_context is None


async def test_lookup_raises_not_found_for_an_unknown_identifier(session: AsyncSession) -> None:
    """The cog turns this into the "Steam64 or Brawlhalla ID" help embed."""
    with pytest.raises(NotFoundError):
        await LookupService(session, _FakeBrawlhalla(known=False)).lookup(  # type: ignore[arg-type]
            guild_id=GUILD_ID, identifier="SomeUsername"
        )
