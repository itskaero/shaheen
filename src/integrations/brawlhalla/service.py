"""Shaheen-facing Brawlhalla service: identifier resolution + caching.

This is the only layer Shaheen's own services should talk to
(docs/BRAWLHALLA_API.md's architecture: Discord command -> Shaheen service
-> Brawlhalla service -> BrawlhallaClient -> external API).
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from integrations.brawlhalla.client import BrawlhallaClient
from integrations.brawlhalla.errors import BrawlhallaNotFound
from integrations.brawlhalla.models import PlayerRankedResponse, PlayerStatsResponse, SearchResult

# A Steam64 ID is always 17 digits; a Brawlhalla player ID is much shorter.
# This is a heuristic, not a protocol guarantee — see docs/DECISIONS.md ADR-023.
_STEAM_ID_MIN_DIGITS = 15


@dataclass
class _CacheEntry[T]:
    value: T
    expires_at: float


class BrawlhallaService:
    """High-level Brawlhalla access with a small in-process TTL cache (ADR-027)."""

    def __init__(self, client: BrawlhallaClient, *, ttl_seconds: float = 60.0) -> None:
        self._client = client
        self._ttl_seconds = ttl_seconds
        self._stats_cache: dict[int, _CacheEntry[PlayerStatsResponse]] = {}
        self._ranked_cache: dict[int, _CacheEntry[PlayerRankedResponse | None]] = {}

    async def aclose(self) -> None:
        await self._client.aclose()

    async def resolve_identifier(self, identifier: str) -> SearchResult:
        """Resolve a user-supplied identifier to a Brawlhalla player.

        Accepts either a Steam64 ID (resolved via /search) or a raw
        Brawlhalla player ID (validated via /player/{id}/stats).
        Raises BrawlhallaNotFound if nothing matches.
        """
        cleaned = identifier.strip()
        if not cleaned.isdigit():
            raise BrawlhallaNotFound(f"{identifier!r} is not a valid Brawlhalla or Steam ID.")

        if len(cleaned) >= _STEAM_ID_MIN_DIGITS:
            raw = await self._client.search_by_steam_id(cleaned)
            if raw is None:
                raise BrawlhallaNotFound(f"No Brawlhalla account found for Steam ID {cleaned}.")
            return SearchResult.model_validate(raw)

        brawlhalla_id = int(cleaned)
        stats = await self.get_stats(brawlhalla_id)
        return SearchResult(brawlhalla_id=stats.brawlhalla_id, name=stats.name)

    async def get_stats(self, brawlhalla_id: int) -> PlayerStatsResponse:
        cached = self._stats_cache.get(brawlhalla_id)
        if cached is not None and cached.expires_at > time.monotonic():
            return cached.value

        raw = await self._client.get_player_stats(brawlhalla_id)
        stats = PlayerStatsResponse.model_validate(raw)
        self._stats_cache[brawlhalla_id] = _CacheEntry(stats, time.monotonic() + self._ttl_seconds)
        return stats

    async def get_ranked(self, brawlhalla_id: int) -> PlayerRankedResponse | None:
        cached = self._ranked_cache.get(brawlhalla_id)
        if cached is not None and cached.expires_at > time.monotonic():
            return cached.value

        raw = await self._client.get_player_ranked(brawlhalla_id)
        ranked = PlayerRankedResponse.model_validate(raw) if raw is not None else None
        self._ranked_cache[brawlhalla_id] = _CacheEntry(
            ranked, time.monotonic() + self._ttl_seconds
        )
        return ranked
