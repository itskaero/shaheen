"""ranking snapshots: season stamp

Revision ID: 0009
Revises: 0008
Create Date: 2026-09-18

Backs docs/DECISIONS.md ADR-088. Brawlhalla wipes ranked ratings at the
start of each season and its API never says which season a response belongs
to, so `ranking_snapshots` has silently been mixing pre- and post-reset
readings. Nothing downstream could tell them apart: the leaderboard would
have ranked a stale 1900 above a freshly-placed 1500 for as long as members
took to re-place, and clan averages would have blended two seasons.

Existing rows are left NULL on purpose rather than backfilled to the
current season. They were captured before anything tracked seasons, so
their season is genuinely unknown, and claiming otherwise would put stale
ratings back on the current-season leaderboard — the exact bug this fixes.
Services treat NULL as "some earlier season", never as current.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("ranking_snapshots", sa.Column("season", sa.Integer(), nullable=True))
    op.create_index(
        "ix_ranking_snapshots_season", "ranking_snapshots", ["season"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_ranking_snapshots_season", table_name="ranking_snapshots")
    op.drop_column("ranking_snapshots", "season")
