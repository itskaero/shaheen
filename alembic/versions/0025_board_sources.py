"""pakistan_board_entries: where an entry came from, and opt-outs

Revision ID: 0025
Revises: 0024
Create Date: 2026-10-05

docs/DECISIONS.md ADR-125:
- source: "self" (/link or /pakistan join), "staff" (/pakistan add) or "team"
  (on a Pakistani team's roster). The team sync only removes what it added.
- excluded: the player left (/pakistan leave) or staff removed them, so the
  team sync and /link won't put them back. Existing removed rows count as
  excluded: each was someone leaving, being replaced, or removed by staff.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0025"
down_revision: str | None = "0024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "pakistan_board_entries",
        sa.Column("source", sa.String(8), nullable=False, server_default="staff"),
    )
    op.add_column(
        "pakistan_board_entries",
        sa.Column("excluded", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.execute(
        "UPDATE pakistan_board_entries SET source = 'self' WHERE owner_discord_id IS NOT NULL"
    )
    op.get_bind().execute(
        sa.text(
            "UPDATE pakistan_board_entries SET excluded = :yes WHERE removed_at IS NOT NULL"
        ).bindparams(yes=True)
    )


def downgrade() -> None:
    op.drop_column("pakistan_board_entries", "excluded")
    op.drop_column("pakistan_board_entries", "source")
