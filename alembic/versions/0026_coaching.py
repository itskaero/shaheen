"""coaches, coaching_requests, and the coaching settings

Revision ID: 0026
Revises: 0025
Create Date: 2026-10-10

docs/DECISIONS.md ADR-126: holders of the Coach role are mirrored into
`coaches`; members ask for coaching with /coach request, which becomes a
`coaching_requests` row. guild_settings gains the Coach role and the
coaching channel. Nothing exists until staff run /coach setup.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0026"
down_revision: str | None = "0025"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    op.add_column("guild_settings", sa.Column("coach_role_id", sa.BigInteger(), nullable=True))
    op.add_column(
        "guild_settings", sa.Column("coaching_channel_id", sa.BigInteger(), nullable=True)
    )
    op.create_table(
        "coaches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("guild_id", sa.BigInteger(), nullable=False),
        sa.Column("discord_id", sa.BigInteger(), nullable=False),
        sa.Column("display_name", sa.String(64), nullable=False),
        sa.Column(
            "brawlhalla_player_id",
            sa.Integer(),
            sa.ForeignKey("brawlhalla_players.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("specialty", sa.String(80), nullable=True),
        sa.Column("legends", sa.String(120), nullable=True),
        sa.Column("availability", sa.String(80), nullable=True),
        sa.Column("bio", sa.String(280), nullable=True),
        sa.Column("accepting", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        *_timestamps(),
        sa.UniqueConstraint("guild_id", "discord_id", name="uq_coaches_guild_discord"),
    )
    op.create_index("ix_coaches_guild_id", "coaches", ["guild_id"])
    op.create_table(
        "coaching_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("guild_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "coach_id",
            sa.Integer(),
            sa.ForeignKey("coaches.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("student_discord_id", sa.BigInteger(), nullable=False),
        sa.Column("message", sa.String(280), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("channel_message_id", sa.BigInteger(), nullable=True),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
    )
    op.create_index("ix_coaching_requests_guild_id", "coaching_requests", ["guild_id"])
    op.create_index("ix_coaching_requests_coach_id", "coaching_requests", ["coach_id"])
    op.create_index(
        "ix_coaching_requests_student_discord_id", "coaching_requests", ["student_discord_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_coaching_requests_student_discord_id", table_name="coaching_requests")
    op.drop_index("ix_coaching_requests_coach_id", table_name="coaching_requests")
    op.drop_index("ix_coaching_requests_guild_id", table_name="coaching_requests")
    op.drop_table("coaching_requests")
    op.drop_index("ix_coaches_guild_id", table_name="coaches")
    op.drop_table("coaches")
    op.drop_column("guild_settings", "coaching_channel_id")
    op.drop_column("guild_settings", "coach_role_id")
