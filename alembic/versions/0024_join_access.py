"""guild_settings: join role, approved role and the approval switch

Revision ID: 0024
Revises: 0023
Create Date: 2026-10-05

docs/DECISIONS.md ADR-123: staff choose the role a new member gets on join
(when approval is on) and the role that grants access (given by /approval,
or straight away on join when approval is off). Off and unset by default, so
nothing changes until staff configure it.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0024"
down_revision: str | None = "0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("guild_settings", sa.Column("join_role_id", sa.BigInteger(), nullable=True))
    op.add_column("guild_settings", sa.Column("approved_role_id", sa.BigInteger(), nullable=True))
    op.add_column(
        "guild_settings",
        sa.Column("approval_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("guild_settings", "approval_enabled")
    op.drop_column("guild_settings", "approved_role_id")
    op.drop_column("guild_settings", "join_role_id")
