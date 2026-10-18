"""staff_members

Revision ID: 0029
Revises: 0028
Create Date: 2026-10-16

docs/DECISIONS.md ADR-135: the Founder and Admin role holders, mirrored by
the bot for the Founding Team page (display name, role and avatar only).
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0029"
down_revision: str | None = "0028"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "staff_members",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("guild_id", sa.BigInteger(), nullable=False),
        sa.Column("discord_id", sa.BigInteger(), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("display_name", sa.String(64), nullable=False),
        sa.Column(
            "brawlhalla_player_id",
            sa.Integer(),
            sa.ForeignKey("brawlhalla_players.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("avatar_key", sa.String(64), nullable=True),
        sa.Column("avatar", sa.LargeBinary(), nullable=True),
        sa.Column("avatar_type", sa.String(32), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("guild_id", "discord_id", name="uq_staff_guild_discord"),
    )
    op.create_index("ix_staff_members_guild_id", "staff_members", ["guild_id"])


def downgrade() -> None:
    op.drop_index("ix_staff_members_guild_id", table_name="staff_members")
    op.drop_table("staff_members")
