"""weekly digest: chat_activity.weekly_xp

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-12

Backs the weekly recap/MVP-of-the-week digest (services/digest_service.py,
docs/DECISIONS.md ADR-070) — a running counter zeroed by the digest job each
week, same shape as `xp` but reset periodically instead of cumulative.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "chat_activity",
        sa.Column("weekly_xp", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("chat_activity", "weekly_xp")
