"""BrawlhallaService: identifier resolution heuristic and TTL caching."""

from __future__ import annotations

import pytest

from integrations.brawlhalla.errors import BrawlhallaNotFound
from integrations.brawlhalla.service import BrawlhallaService


class _FakeClient:
    def __init__(self) -> None:
        self.stats_calls = 0
        self.ranked_calls = 0
        self.search_calls = 0

    async def search_by_steam_id(self, steam_id64: str) -> dict | None:
        self.search_calls += 1
        if steam_id64 == "76561198025185087":
            return {"brawlhalla_id": 555, "name": "SteamPlayer"}
        return None

    async def get_player_stats(self, brawlhalla_id: int) -> dict:
        self.stats_calls += 1
        return {"brawlhalla_id": brawlhalla_id, "name": "DirectPlayer", "games": 10, "wins": 5}

    async def get_player_ranked(self, brawlhalla_id: int) -> dict | None:
        self.ranked_calls += 1
        return {"brawlhalla_id": brawlhalla_id, "name": "DirectPlayer", "tier": "Gold I"}

    async def aclose(self) -> None:
        pass


async def test_resolve_identifier_treats_long_numbers_as_steam_id() -> None:
    client = _FakeClient()
    service = BrawlhallaService(client)  # type: ignore[arg-type]
    result = await service.resolve_identifier("76561198025185087")
    assert result.brawlhalla_id == 555
    assert client.search_calls == 1
    assert client.stats_calls == 0


async def test_resolve_identifier_treats_short_numbers_as_brawlhalla_id() -> None:
    client = _FakeClient()
    service = BrawlhallaService(client)  # type: ignore[arg-type]
    result = await service.resolve_identifier("12345")
    assert result.brawlhalla_id == 12345
    assert client.stats_calls == 1
    assert client.search_calls == 0


async def test_resolve_identifier_rejects_non_numeric_input() -> None:
    client = _FakeClient()
    service = BrawlhallaService(client)  # type: ignore[arg-type]
    with pytest.raises(BrawlhallaNotFound):
        await service.resolve_identifier("not-an-id")


async def test_get_stats_is_cached_within_ttl() -> None:
    client = _FakeClient()
    service = BrawlhallaService(client, ttl_seconds=60)  # type: ignore[arg-type]
    await service.get_stats(1)
    await service.get_stats(1)
    assert client.stats_calls == 1


async def test_get_ranked_is_cached_within_ttl() -> None:
    client = _FakeClient()
    service = BrawlhallaService(client, ttl_seconds=60)  # type: ignore[arg-type]
    await service.get_ranked(1)
    await service.get_ranked(1)
    assert client.ranked_calls == 1


async def test_get_stats_refetches_after_ttl_expires() -> None:
    client = _FakeClient()
    service = BrawlhallaService(client, ttl_seconds=-1)  # type: ignore[arg-type]
    await service.get_stats(1)
    await service.get_stats(1)
    assert client.stats_calls == 2
