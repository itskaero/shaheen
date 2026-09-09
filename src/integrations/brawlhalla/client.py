"""Low-level Brawlhalla API HTTP client.

No cog or service outside this integration should build a Brawlhalla URL or
call httpx directly (docs/BRAWLHALLA_API.md). This module only speaks raw
dicts; integrations/brawlhalla/service.py parses them into the typed models
in integrations/brawlhalla/models.py.
"""

from __future__ import annotations

import asyncio
import logging

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


class BrawlhallaClient:
    """Thin async wrapper around the Brawlhalla Developer API."""

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._api_key = api_key
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

    async def _get_or_none(self, path: str, *, params: dict | None = None) -> dict | None:
        try:
            return await self._get(path, params=params)
        except BrawlhallaNotFound:
            return None

    async def _get(self, path: str, *, params: dict | None = None) -> dict:
        query = {"api_key": self._api_key, **(params or {})}

        attempt = 0
        while True:
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
