"""guild_settings: re-announce Pakistan Season 1 under its new name

Revision ID: 0018
Revises: 0017
Create Date: 2026-10-04

docs/DECISIONS.md ADR-108 — the owner's BRAWLISTAN season cards number
Markhor as Season 1 (Zarb-e-Shaheen moves to 2). Brawlhalla S42 is now the
Season of Markhor, so the start-of-season post goes out once more with the
new name and card. Clearing announced_season lets the next snapshot tick do
that, exactly as on a first deploy.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0018"
down_revision: str | None = "0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("UPDATE guild_settings SET announced_season = NULL")


def downgrade() -> None:
    pass
