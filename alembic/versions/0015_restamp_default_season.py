"""ranking_snapshots: restamp the default "season 1" as S41 / S42

Revision ID: 0015
Revises: 0014
Create Date: 2026-09-23

docs/DECISIONS.md ADR-102 — production never set BRAWLHALLA_SEASON, so every
rating row was stamped with the default 1. Shaheen went live inside
Brawlhalla Season 41, so rows before the S42 reset (2026-09-23 00:00 UTC)
are S41 and rows after it are S42. NULL-season rows are left alone.

No downgrade: after upgrading, new S42 rows can't be told apart from the
restamped ones, and turning genuine S42 readings back into "season 1"
would be the wrong kind of lossy.
"""

from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Mirrors services/seasons.py's ANCHOR_START; copied, not imported, so this
# migration keeps meaning the same thing if that module ever changes.
_S42_START = datetime(2026, 9, 23, tzinfo=UTC)


def _restamp(season: int, comparison: str) -> None:
    op.execute(
        sa.text(
            f"UPDATE ranking_snapshots SET season = :season "
            f"WHERE season = 1 AND captured_at {comparison} :anchor"
        ).bindparams(
            sa.bindparam("season", season),
            sa.bindparam("anchor", _S42_START, type_=sa.DateTime(timezone=True)),
        )
    )


def upgrade() -> None:
    _restamp(41, "<")
    _restamp(42, ">=")


def downgrade() -> None:
    pass
