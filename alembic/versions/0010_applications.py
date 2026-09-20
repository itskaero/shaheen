"""applications: membership applications and their review

Revision ID: 0010
Revises: 0009
Create Date: 2026-09-20

Backs docs/DECISIONS.md ADR-089. Joining Shaheen was previously: land in the
server, receive the auto-assigned Guest role, and wait for a staff member to
notice and run /verify. Nothing recorded who asked, what they said, who
decided, or why. This table is that record.

`answers` is JSON so the application form can change without a migration —
the questions are presentation, the decision is the data.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_STATUS = sa.Enum(
    "PENDING", "APPROVED", "DENIED", "WITHDRAWN", name="application_status"
)


def upgrade() -> None:
    op.create_table(
        "applications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("guild_id", sa.BigInteger(), nullable=False),
        sa.Column("discord_id", sa.BigInteger(), nullable=False),
        sa.Column("status", _STATUS, nullable=False),
        sa.Column("answers", sa.JSON(), nullable=False),
        sa.Column("review_message_id", sa.BigInteger(), nullable=True),
        sa.Column("reviewer_discord_id", sa.BigInteger(), nullable=True),
        sa.Column("review_note", sa.String(length=512), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("brawlhalla_identifier", sa.String(length=32), nullable=True),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_applications_guild_status", "applications", ["guild_id", "status"], unique=False
    )
    op.create_index(
        "ix_applications_guild_discord", "applications", ["guild_id", "discord_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_applications_guild_discord", table_name="applications")
    op.drop_index("ix_applications_guild_status", table_name="applications")
    op.drop_table("applications")
    # Postgres keeps a standalone enum type behind after the table goes;
    # SQLite has no such type, hence the dialect check.
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        _STATUS.drop(bind, checkfirst=True)
