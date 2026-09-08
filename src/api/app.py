"""Shaheen's public API (docs/DECISIONS.md ADR-039).

Read-only, unauthenticated, and built on the exact same services/
repositories/database the Discord bot uses (docs/ARCHITECTURE.md). Run
with: `uv run uvicorn api.app:app --host 0.0.0.0 --port 8000`.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import clan, leaderboard, players
from core.config import load_settings
from core.logging import configure_logging
from database.session import create_engine, create_session_factory

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = load_settings()
    configure_logging(settings.log_level)

    engine = create_engine(settings.database_url)
    app.state.settings = settings
    app.state.session_factory = create_session_factory(engine)

    logger.info("Shaheen API ready (guild=%s)", settings.guild_id)
    try:
        yield
    finally:
        await engine.dispose()
        logger.info("Shaheen API stopped.")


app = FastAPI(
    title="Shaheen API",
    description=(
        "Public read-only clan/player data for the future Shaheen website "
        "(docs/ROADMAP.md Phase 5)."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    # Every endpoint is already public and read-only (ADR-039), so there is
    # no per-origin data to protect — allow any origin rather than
    # maintaining a frontend-hosting-URL allowlist (ADR-043).
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(clan.router)
app.include_router(leaderboard.router)
app.include_router(players.router)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
