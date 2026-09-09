"""Entrypoint: config -> logging -> database -> Discord client."""

from __future__ import annotations

import asyncio
import logging

from bot.client import ShaheenBot
from core.config import load_settings
from core.logging import configure_logging
from database.session import create_engine, create_session_factory

logger = logging.getLogger(__name__)


async def run() -> None:
    settings = load_settings()
    configure_logging(settings.log_level)

    logger.info("Starting Shaheen Bot (guild=%s, mode=%s)", settings.guild_id, settings.setup_mode)

    engine = create_engine(settings.database_url)
    session_factory = create_session_factory(engine)

    bot = ShaheenBot(settings=settings, session_factory=session_factory)
    try:
        await bot.start(settings.discord_token.get_secret_value())
    finally:
        await bot.close()
        await engine.dispose()
        logger.info("Shaheen Bot stopped.")


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
