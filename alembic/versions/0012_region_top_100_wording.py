"""region_top_100: say which "region" it means

Revision ID: 0012
Revises: 0011
Create Date: 2026-09-23

docs/DECISIONS.md ADR-100 — "top 100 of your region" read as a country;
it's the Brawlhalla server region's 1v1 ladder (the API's region_rank).
Wording only; the key and who holds it are unchanged.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_OLD = "Ranked inside the top 100 of your region."
_NEW = "Ranked inside the top 100 of your Brawlhalla server region's 1v1 ladder (e.g. SEA)."


def _set(description: str) -> None:
    op.execute(
        sa.text("UPDATE achievements SET description = :d WHERE key = 'region_top_100'").bindparams(
            d=description
        )
    )


def upgrade() -> None:
    _set(_NEW)


def downgrade() -> None:
    _set(_OLD)
