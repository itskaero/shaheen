"""Read-only database facts for /admin status (docs/DECISIONS.md ADR-129).

Nothing here writes. Each call is a single cheap query, so the status check
never loads a table.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.brawlhalla_player import BrawlhallaPlayer
from database.models.ranking_snapshot import RankingSnapshot


class SystemRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def ping(self) -> None:
        """Raises if the database can't answer `SELECT 1`."""
        await self._session.execute(text("SELECT 1"))

    async def schema_revision(self) -> str | None:
        """The Alembic revision the schema is at, or None without one
        (a database made by `create_all`, as in the tests)."""
        try:
            result = await self._session.execute(text("SELECT version_num FROM alembic_version"))
        except DBAPIError:
            await self._session.rollback()
            return None
        return result.scalar_one_or_none()

    async def last_snapshot_at(self) -> datetime | None:
        """When the bot last stored any ranking reading."""
        stmt = select(func.max(RankingSnapshot.captured_at))
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def tracked_player_count(self) -> int:
        stmt = select(func.count()).select_from(BrawlhallaPlayer)
        return int((await self._session.execute(stmt)).scalar_one())
