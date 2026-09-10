"""Async SQLAlchemy engine/session plumbing.

Nothing outside this module and database/repositories/ should import
SQLAlchemy directly — cogs and services depend on repositories, not raw
sessions or SQL (docs/ARCHITECTURE.md).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def create_engine(database_url: str) -> AsyncEngine:
    connect_args: dict[str, object] = {}
    if database_url.startswith("postgresql+asyncpg://"):
        # asyncpg's own connect() timeout (seconds) — without this, an
        # unreachable/slow Postgres host leaves the API's request handler
        # hanging indefinitely instead of failing fast with a real error
        # the frontend can show (docs/DECISIONS.md ADR-059). Not applied
        # for sqlite (the test suite's DATABASE_URL), which has no
        # equivalent concept and no connect-hang failure mode to guard.
        connect_args["timeout"] = 10
    return create_async_engine(database_url, pool_pre_ping=True, connect_args=connect_args)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


@asynccontextmanager
async def session_scope(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    """One unit-of-work: commits on success, rolls back on error."""
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
