"""ranking_snapshots: best 2v2 team per reading

Revision ID: 0016
Revises: 0015
Create Date: 2026-10-04

docs/DECISIONS.md ADR-105 — the Rankings page's 2v2 tab. Each snapshot also
records the player's best placed 2v2 team (rating, peak, tier, partner name).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_COLUMNS = ("rating_2v2", "peak_rating_2v2", "tier_2v2", "partner_2v2")


def upgrade() -> None:
    op.add_column("ranking_snapshots", sa.Column("rating_2v2", sa.Integer(), nullable=True))
    op.add_column("ranking_snapshots", sa.Column("peak_rating_2v2", sa.Integer(), nullable=True))
    op.add_column("ranking_snapshots", sa.Column("tier_2v2", sa.String(32), nullable=True))
    op.add_column("ranking_snapshots", sa.Column("partner_2v2", sa.String(64), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("ranking_snapshots") as batch:
        for column in _COLUMNS:
            batch.drop_column(column)
