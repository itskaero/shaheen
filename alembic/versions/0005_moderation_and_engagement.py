"""moderation and engagement tables: warnings, chat_activity

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-11

Moderation commands (warn/warnings/clearwarnings) and chat-message XP/
leveling. See docs/DECISIONS.md ADR-065.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "warnings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("guild_id", sa.BigInteger(), nullable=False),
        sa.Column("discord_id", sa.BigInteger(), nullable=False),
        sa.Column("moderator_discord_id", sa.BigInteger(), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_warnings_guild_id", "warnings", ["guild_id"])
    op.create_index("ix_warnings_discord_id", "warnings", ["discord_id"])

    op.create_table(
        "chat_activity",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("guild_id", sa.BigInteger(), nullable=False),
        sa.Column("discord_id", sa.BigInteger(), nullable=False),
        sa.Column("xp", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("level", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("message_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_xp_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("guild_id", "discord_id", name="uq_chat_activity_member"),
    )
    op.create_index("ix_chat_activity_guild_id", "chat_activity", ["guild_id"])
    op.create_index("ix_chat_activity_discord_id", "chat_activity", ["discord_id"])


def downgrade() -> None:
    op.drop_index("ix_chat_activity_discord_id", table_name="chat_activity")
    op.drop_index("ix_chat_activity_guild_id", table_name="chat_activity")
    op.drop_table("chat_activity")

    op.drop_index("ix_warnings_discord_id", table_name="warnings")
    op.drop_index("ix_warnings_guild_id", table_name="warnings")
    op.drop_table("warnings")
