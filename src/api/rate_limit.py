"""A small per-client sliding-window rate limiter for the API's few write
endpoints (docs/DECISIONS.md ADR-107).

In memory, which fits the deployment: one Render instance, and a restart
merely resets the windows. If the API ever scales out, move this to the
database or a shared cache.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request


def client_ip(request: Request) -> str:
    """The caller's address. Render (like most proxies) puts the original
    client first in X-Forwarded-For.
    """
    forwarded = request.headers.get("x-forwarded-for", "")
    first = forwarded.split(",")[0].strip()
    if first:
        return first
    return request.client.host if request.client else "unknown"


class RateLimiter:
    def __init__(self, *, limit: int, window_seconds: float) -> None:
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str, *, now: float | None = None) -> None:
        now = time.monotonic() if now is None else now
        hits = self._hits[key]
        while hits and now - hits[0] > self.window:
            hits.popleft()
        if len(hits) >= self.limit:
            raise HTTPException(
                status_code=429, detail="Too many attempts. Wait a few minutes and try again."
            )
        hits.append(now)

    def reset(self) -> None:
        self._hits.clear()
