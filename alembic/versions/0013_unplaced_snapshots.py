"""ranking_snapshots: store "unplaced this season" as NULL, not 0 / "None"

Revision ID: 0013
Revises: 0012
Create Date: 2026-09-23

docs/DECISIONS.md ADR-101 — after the Season 41 -> 42 reset the Brawlhalla
API answered with rating 0 and tier "None" for players without placement
games, and those were stored as-is. The API models now normalize that to
NULL; this cleans up the rows already written. No downgrade: the zeros
carried no information.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "UPDATE ranking_snapshots SET rating = NULL, tier = NULL "
        "WHERE rating <= 0 OR lower(trim(tier)) IN ('', 'none', 'unranked')"
    )
    op.execute("UPDATE ranking_snapshots SET peak_rating = NULL WHERE peak_rating <= 0")
    op.execute("UPDATE ranking_snapshots SET global_rank = NULL WHERE global_rank <= 0")
    op.execute("UPDATE ranking_snapshots SET region_rank = NULL WHERE region_rank <= 0")


def downgrade() -> None:
    pass
