"""Low-level Brawlhalla API HTTP client.

No cog or service outside this integration should build a Brawlhalla URL or
call httpx directly (docs/BRAWLHALLA_API.md). This module only speaks raw
dicts; integrations/brawlhalla/service.py parses them into the typed models
in integrations/brawlhalla/models.py.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from collections.abc import Awaitable, Callable

import httpx

from integrations.brawlhalla.errors import (
    BrawlhallaAPIError,
    BrawlhallaForbidden,
    BrawlhallaNotFound,
    BrawlhallaRateLimited,
    BrawlhallaServiceUnavailable,
    BrawlhallaUnauthorized,
)

logger = logging.getLogger(__name__)

BASE_URL = "https://api.brawlhalla.com/"  # ADR-022
DEFAULT_TIMEOUT = 10.0
MAX_RETRIES = 2
RETRY_BACKOFF_SECONDS = (0.5, 1.5)
# The API allows about 180 requests per 15 minutes per key (and ~10 a
# second). Stay under it so a snapshot tick that walks every tracked player,
# clan rosters included (ADR-120), paces itself instead of hitting 429s.
RATE_LIMIT = 170
RATE_WINDOW_SECONDS = 900.0
MIN_INTERVAL_SECONDS = 0.12


class RateLimiter:
    """Sliding-window limiter: at most `limit` requests per `window` seconds,
    and at least `min_interval` between two requests. Waits rather than
    refusing. The clock and sleep are injectable for tests."""

    def __init__(
        self,
        limit: int = RATE_LIMIT,
        window: float = RATE_WINDOW_SECONDS,
        min_interval: float = MIN_INTERVAL_SECONDS,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Awaitable[object]] = asyncio.sleep,
    ) -> None:
        self._limit = limit
        self._window = window
        self._min_interval = min_interval
        self._clock = clock
        self._sleep = sleep
        self._sent: deque[float] = deque()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            while True:
                now = self._clock()
                while self._sent and now - self._sent[0] >= self._window:
                    self._sent.popleft()
                waits = []
                if len(self._sent) >= self._limit:
                    waits.append(self._sent[0] + self._window - now)
                if self._sent and now - self._sent[-1] < self._min_interval:
                    waits.append(self._sent[-1] + self._min_interval - now)
                if not waits:
                    self._sent.append(now)
                    return
                delay = max(waits)
                if delay > 5:
                    logger.info("Brawlhalla API budget used up; waiting %.0fs", delay)
                await self._sleep(delay)


class BrawlhallaClient:
    """Thin async wrapper around the Brawlhalla Developer API."""

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        http_client: httpx.AsyncClient | None = None,
        rate_limiter: RateLimiter | None = None,
    ) -> None:
        self._api_key = api_key
        self._limiter = rate_limiter or RateLimiter()
        self._owns_client = http_client is None
        self._http = http_client or httpx.AsyncClient(base_url=base_url, timeout=timeout)

    async def aclose(self) -> None:
        if self._owns_client:
            await self._http.aclose()

    async def search_by_steam_id(self, steam_id64: str) -> dict | None:
        """GET /search — resolves a Steam64 ID to a Brawlhalla player. None if unmatched."""
        return await self._get_or_none("search", params={"steamid": steam_id64})

    async def get_player_stats(self, brawlhalla_id: int) -> dict:
        """GET /player/{id}/stats. Raises BrawlhallaNotFound for an invalid ID."""
        return await self._get(f"player/{brawlhalla_id}/stats")

    async def get_player_ranked(self, brawlhalla_id: int) -> dict | None:
        """GET /player/{id}/ranked. None if the player has no ranked history."""
        return await self._get_or_none(f"player/{brawlhalla_id}/ranked")

    async def get_clan(self, clan_id: int) -> dict:
        """GET /clan/{id}: the clan and its members (ADR-120). Raises
        BrawlhallaNotFound for an unknown clan."""
        return await self._get(f"clan/{clan_id}/")

    async def _get_or_none(self, path: str, *, params: dict | None = None) -> dict | None:
        try:
            return await self._get(path, params=params)
        except BrawlhallaNotFound:
            return None

    async def _get(self, path: str, *, params: dict | None = None) -> dict:
        query = {"api_key": self._api_key, **(params or {})}

        attempt = 0
        while True:
            await self._limiter.acquire()
            try:
                response = await self._http.get(path, params=query)
            except httpx.TimeoutException as exc:
                raise BrawlhallaAPIError(f"Brawlhalla API request to {path!r} timed out") from exc
            except httpx.HTTPError as exc:
                raise BrawlhallaAPIError(f"Brawlhalla API request to {path!r} failed") from exc

            if response.status_code == 200:
                return response.json()

            if response.status_code in (429, 503) and attempt < MAX_RETRIES:
                delay = RETRY_BACKOFF_SECONDS[min(attempt, len(RETRY_BACKOFF_SECONDS) - 1)]
                logger.warning(
                    "Brawlhalla API %s on %s, retrying in %.1fs (attempt %d/%d)",
                    response.status_code,
                    path,
                    delay,
                    attempt + 1,
                    MAX_RETRIES,
                )
                await asyncio.sleep(delay)
                attempt += 1
                continue

            _raise_for_status(response.status_code, path)

    async def __aenter__(self) -> BrawlhallaClient:
        return self

    async def __aexit__(self, *_exc_info: object) -> None:
        await self.aclose()


def _raise_for_status(status_code: int, path: str) -> None:
    message = f"Brawlhalla API returned {status_code} for {path!r}"
    if status_code == 401:
        raise BrawlhallaUnauthorized(message)
    if status_code == 403:
        raise BrawlhallaForbidden(message)
    if status_code == 404:
        raise BrawlhallaNotFound(message)
    if status_code == 429:
        raise BrawlhallaRateLimited(message)
    if status_code == 503:
        raise BrawlhallaServiceUnavailable(message)
    raise BrawlhallaAPIError(message)
