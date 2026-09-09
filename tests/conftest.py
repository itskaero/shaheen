from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from database.models import Achievement, Base
from database.session import create_session_factory
from services.achievements import CATALOG


@pytest.fixture
async def session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield create_session_factory(engine)
    finally:
        await engine.dispose()


@pytest.fixture
async def session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    async with session_factory() as s:
        yield s


@pytest.fixture
async def achievement_catalog(session: AsyncSession) -> dict[str, Achievement]:
    """Seeds services.achievements.CATALOG, mirroring the Phase 3 migration's seed data."""
    rows = {}
    for definition in CATALOG:
        row = Achievement(
            key=definition.key, name=definition.name, description=definition.description
        )
        session.add(row)
        rows[definition.key] = row
    await session.flush()
    return rows
