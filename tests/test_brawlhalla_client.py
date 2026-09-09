"""BrawlhallaClient against a mocked transport — no real network calls."""

from __future__ import annotations

import httpx
import pytest

from integrations.brawlhalla.client import BrawlhallaClient
from integrations.brawlhalla.errors import (
    BrawlhallaForbidden,
    BrawlhallaNotFound,
    BrawlhallaServiceUnavailable,
)


def _client(handler) -> BrawlhallaClient:  # noqa: ANN001
    transport = httpx.MockTransport(handler)
    http = httpx.AsyncClient(base_url="https://api.brawlhalla.com/", transport=transport)
    return BrawlhallaClient("test-key", http_client=http)


async def _no_sleep(_seconds: float) -> None:
    return None


async def test_get_player_stats_returns_parsed_json() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["api_key"] == "test-key"
        assert request.url.path == "/player/123/stats"
        return httpx.Response(200, json={"brawlhalla_id": 123, "name": "Foo"})

    client = _client(handler)
    result = await client.get_player_stats(123)
    assert result == {"brawlhalla_id": 123, "name": "Foo"}
    await client.aclose()


async def test_get_player_ranked_returns_none_on_404() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "not found"})

    client = _client(handler)
    assert await client.get_player_ranked(999) is None
    await client.aclose()


async def test_get_player_stats_raises_not_found_on_404() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "not found"})

    client = _client(handler)
    with pytest.raises(BrawlhallaNotFound):
        await client.get_player_stats(999)
    await client.aclose()


async def test_forbidden_on_bad_api_key() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"error": "forbidden"})

    client = _client(handler)
    with pytest.raises(BrawlhallaForbidden):
        await client.get_player_stats(1)
    await client.aclose()


async def test_retries_on_503_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("integrations.brawlhalla.client.asyncio.sleep", _no_sleep)
    calls = {"count": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        if calls["count"] < 2:
            return httpx.Response(503, json={"error": "maintenance"})
        return httpx.Response(200, json={"brawlhalla_id": 1, "name": "Retried"})

    client = _client(handler)
    result = await client.get_player_stats(1)
    assert result["name"] == "Retried"
    assert calls["count"] == 2
    await client.aclose()


async def test_gives_up_after_max_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("integrations.brawlhalla.client.asyncio.sleep", _no_sleep)

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": "maintenance"})

    client = _client(handler)
    with pytest.raises(BrawlhallaServiceUnavailable):
        await client.get_player_stats(1)
    await client.aclose()


async def test_search_by_steam_id_sends_steamid_param() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/search"
        assert request.url.params["steamid"] == "76561198025185087"
        return httpx.Response(200, json={"brawlhalla_id": 42, "name": "SteamPlayer"})

    client = _client(handler)
    result = await client.search_by_steam_id("76561198025185087")
    assert result == {"brawlhalla_id": 42, "name": "SteamPlayer"}
    await client.aclose()
