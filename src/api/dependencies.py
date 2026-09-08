"""FastAPI dependency providers — DB session and settings, sourced from
app.state (set up once in api/app.py's lifespan).
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import Settings


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    session_factory = request.app.state.session_factory
    async with session_factory() as session:
        yield session


def get_settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings
