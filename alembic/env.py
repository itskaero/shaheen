"""Alembic environment.

Only needs DATABASE_URL — it deliberately does not construct the full
application Settings object, so migrations can run in contexts (CI, a bare
migration-only container) that don't have Discord credentials configured.
"""

from __future__ import annotations

import asyncio
import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from core.config import normalize_database_url  # noqa: E402
from database.models import Base  # noqa: E402

load_dotenv()

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

database_url = os.environ.get("DATABASE_URL")
if not database_url:
    raise RuntimeError("DATABASE_URL must be set to run migrations.")
# Managed Postgres providers (Render, Heroku, ...) hand out a bare
# postgres://.../postgresql://... connection string with no driver suffix;
# the async engine below requires +asyncpg. `core.config.Settings` already
# normalizes this for the app itself — reuse the same function here instead
# of duplicating the prefix-swap (this module deliberately doesn't build a
# full Settings object, since migrations can run without Discord/Brawlhalla
# credentials set).
database_url = normalize_database_url(database_url)
config.set_main_option("sqlalchemy.url", database_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def _do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(_do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
