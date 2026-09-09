"""LinkService: link/relink/unlink orchestration against a real (sqlite) DB."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import NotFoundError
from integrations.brawlhalla.errors import BrawlhallaNotFound
from integrations.brawlhalla.models import PlayerRankedResponse, SearchResult
from services.link_service import LinkService

GUILD_ID = 1
DISCORD_ID = 100


class _FakeBrawlhalla:
    def __init__(self, *, region: str | None = "us-e") -> None:
        self.region = region

    async def resolve_identifier(self, identifier: str) -> SearchResult:
        if identifier == "missing":
            raise BrawlhallaNotFound("no such player")
        return SearchResult(brawlhalla_id=int(identifier), name=f"Player{identifier}")

    async def get_ranked(self, brawlhalla_id: int) -> PlayerRankedResponse | None:
        if self.region is None:
            return None
        return PlayerRankedResponse(brawlhalla_id=brawlhalla_id, name="x", region=self.region)

    async def get_stats(self, brawlhalla_id: int):  # pragma: no cover - unused here
        raise NotImplementedError


async def test_link_creates_member_and_player(session: AsyncSession) -> None:
    service = LinkService(session, _FakeBrawlhalla())  # type: ignore[arg-type]
    candidate = await service.resolve_candidate("111")

    outcome = await service.link(
        guild_id=GUILD_ID, discord_id=DISCORD_ID, joined_at=None, candidate=candidate
    )

    assert outcome.player.brawlhalla_player_id == 111
    assert outcome.player.region == "us-e"
    assert outcome.previous_player_name is None

    active = await service.get_active_link(guild_id=GUILD_ID, discord_id=DISCORD_ID)
    assert active is not None
    assert active[1].brawlhalla_player_id == 111


async def test_relink_replaces_active_link(session: AsyncSession) -> None:
    service = LinkService(session, _FakeBrawlhalla())  # type: ignore[arg-type]
    first = await service.resolve_candidate("111")
    await service.link(guild_id=GUILD_ID, discord_id=DISCORD_ID, joined_at=None, candidate=first)

    second = await service.resolve_candidate("222")
    outcome = await service.link(
        guild_id=GUILD_ID, discord_id=DISCORD_ID, joined_at=None, candidate=second
    )

    assert outcome.previous_player_name == "Player111"
    active = await service.get_active_link(guild_id=GUILD_ID, discord_id=DISCORD_ID)
    assert active is not None
    assert active[1].brawlhalla_player_id == 222


async def test_unlink_clears_active_link(session: AsyncSession) -> None:
    service = LinkService(session, _FakeBrawlhalla())  # type: ignore[arg-type]
    candidate = await service.resolve_candidate("111")
    await service.link(
        guild_id=GUILD_ID, discord_id=DISCORD_ID, joined_at=None, candidate=candidate
    )

    unlinked = await service.unlink(guild_id=GUILD_ID, discord_id=DISCORD_ID)
    assert unlinked is not None
    assert unlinked.brawlhalla_player_id == 111

    assert await service.get_active_link(guild_id=GUILD_ID, discord_id=DISCORD_ID) is None


async def test_unlink_with_no_active_link_returns_none(session: AsyncSession) -> None:
    service = LinkService(session, _FakeBrawlhalla())  # type: ignore[arg-type]
    assert await service.unlink(guild_id=GUILD_ID, discord_id=DISCORD_ID) is None


async def test_resolve_candidate_translates_not_found(session: AsyncSession) -> None:
    service = LinkService(session, _FakeBrawlhalla())  # type: ignore[arg-type]
    with pytest.raises(NotFoundError):
        await service.resolve_candidate("missing")


async def test_link_survives_region_lookup_failure(session: AsyncSession) -> None:
    service = LinkService(session, _FakeBrawlhalla(region=None))  # type: ignore[arg-type]
    candidate = await service.resolve_candidate("111")
    outcome = await service.link(
        guild_id=GUILD_ID, discord_id=DISCORD_ID, joined_at=None, candidate=candidate
    )
    assert outcome.player.region is None
