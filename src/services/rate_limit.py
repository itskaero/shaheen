"""A small in-memory sliding-window rate limit for bot buttons (ADR-136).

Per process, like api/rate_limit.py: enough for one bot instance. Used where a
button can trigger a Brawlhalla API lookup or a role ping.
"""

from __future__ import annotations

from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta


class SlidingWindow:
    def __init__(self, *, limit: int, window: timedelta) -> None:
        self._limit = limit
        self._window = window
        self._hits: dict[int, deque[datetime]] = defaultdict(deque)

    def allow(self, key: int, *, now: datetime | None = None) -> bool:
        """Record a hit for `key` if it's under the limit; False if it isn't."""
        now = now or datetime.now(UTC)
        hits = self._hits[key]
        while hits and now - hits[0] >= self._window:
            hits.popleft()
        if len(hits) >= self._limit:
            return False
        hits.append(now)
        return True
