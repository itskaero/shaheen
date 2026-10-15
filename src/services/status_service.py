"""System status for /admin status (docs/DECISIONS.md ADR-129).

Discord-agnostic: the bot passes its own facts (gateway latency, uptime,
which background loops are running) as plain values, and this module adds
the database's and decides what needs attention. The same report could back
a future API health page.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from database.repositories.system_repository import SystemRepository
from database.session import session_scope

logger = logging.getLogger(__name__)

# A snapshot is late once this many intervals have passed without one: one
# missed tick can be a restart, two in a row is a fault.
LATE_AFTER_INTERVALS = 2
SLOW_GATEWAY_MS = 500
SLOW_DATABASE_MS = 300


@dataclass(frozen=True)
class BotFacts:
    gateway_ms: int
    uptime: timedelta
    loops: dict[str, bool] = field(default_factory=dict)  # loop name -> running


@dataclass(frozen=True)
class SystemStatus:
    now: datetime
    bot: BotFacts
    database_ok: bool
    database_ms: int | None
    schema_revision: str | None
    last_snapshot_at: datetime | None
    tracked_players: int | None
    snapshot_interval: timedelta

    @property
    def snapshot_age(self) -> timedelta | None:
        if self.last_snapshot_at is None:
            return None
        return self.now - self.last_snapshot_at

    def problems(self) -> list[str]:
        """What needs attention, most serious first. Empty means healthy."""
        found: list[str] = []
        if not self.database_ok:
            found.append("The database is unreachable.")
        elif self.database_ms is not None and self.database_ms > SLOW_DATABASE_MS:
            found.append(f"The database is slow ({self.database_ms} ms).")
        found.extend(
            f"The {name} loop isn't running."
            for name, running in self.bot.loops.items()
            if not running
        )
        age = self.snapshot_age
        if self.database_ok and age is None:
            found.append("No ranking snapshot has been taken yet.")
        elif age is not None and age > self.snapshot_interval * LATE_AFTER_INTERVALS:
            found.append(
                "The last ranking snapshot is "
                f"{format_age(age)} old: check the Brawlhalla API key and the bot logs."
            )
        if self.bot.gateway_ms > SLOW_GATEWAY_MS:
            found.append(f"Discord latency is high ({self.bot.gateway_ms} ms).")
        return found


def format_age(age: timedelta) -> str:
    seconds = max(0, int(age.total_seconds()))
    if seconds < 60:
        return f"{seconds}s"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m"
    hours, minutes = divmod(minutes, 60)
    if hours < 48:
        return f"{hours}h {minutes}m" if minutes else f"{hours}h"
    return f"{hours // 24}d {hours % 24}h"


class StatusService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def check(
        self, *, now: datetime, bot: BotFacts, snapshot_interval: timedelta
    ) -> SystemStatus:
        """Never raises for a database fault: an unreachable database is part
        of the report, not an error."""
        database_ok = False
        database_ms: int | None = None
        revision: str | None = None
        last_snapshot_at: datetime | None = None
        tracked: int | None = None
        try:
            async with session_scope(self._session_factory) as session:
                repo = SystemRepository(session)
                started = time.perf_counter()
                await repo.ping()
                database_ms = round((time.perf_counter() - started) * 1000)
                database_ok = True
                revision = await repo.schema_revision()
                last_snapshot_at = await repo.last_snapshot_at()
                tracked = await repo.tracked_player_count()
        except Exception as error:
            # The message only: a connection error can carry the URL's host
            # but never the password (SQLAlchemy masks it).
            logger.warning("Status check: database query failed: %s", type(error).__name__)

        if last_snapshot_at is not None and last_snapshot_at.tzinfo is None:
            # SQLite (tests) returns naive datetimes; stored values are UTC.
            last_snapshot_at = last_snapshot_at.replace(tzinfo=now.tzinfo)

        return SystemStatus(
            now=now,
            bot=bot,
            database_ok=database_ok,
            database_ms=database_ms,
            schema_revision=revision,
            last_snapshot_at=last_snapshot_at,
            tracked_players=tracked,
            snapshot_interval=snapshot_interval,
        )
