"""team_members.show_tag: players choose whether to wear their team tag

Revision ID: 0021
Revises: 0020
Create Date: 2026-10-05

docs/DECISIONS.md ADR-115 — "[SHN] kaero." on the rankings, players page and
profile, unless the player turns it off with /team tag. On for everyone today.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0021"
down_revision: str | None = "0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "team_members",
        sa.Column("show_tag", sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_column("team_members", "show_tag")
