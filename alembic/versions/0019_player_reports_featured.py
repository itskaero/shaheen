"""Player reports and the featured player

Revision ID: 0019
Revises: 0018
Create Date: 2026-10-05

docs/DECISIONS.md ADR-111:
- player_reports: one moderation record per report, from Discord /report or
  the website's Report Player.
- guild_settings.featured_*: staff's /feature pick for the website.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0019"
down_revision: str | None = "0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "player_reports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("guild_id", sa.BigInteger(), nullable=False),
        sa.Column("source", sa.String(16), nullable=False),
        sa.Column("reporter_discord_id", sa.BigInteger(), nullable=True),
        sa.Column("reported_discord_id", sa.BigInteger(), nullable=True),
        sa.Column("reported_brawlhalla_id", sa.BigInteger(), nullable=True),
        sa.Column("reported_name", sa.String(64), nullable=False),
        sa.Column("reason", sa.String(1000), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("report_message_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_player_reports_guild_id", "player_reports", ["guild_id"])
    op.create_index(
        "ix_player_reports_reporter_discord_id", "player_reports", ["reporter_discord_id"]
    )
    op.add_column(
        "guild_settings", sa.Column("featured_brawlhalla_id", sa.BigInteger(), nullable=True)
    )
    op.add_column("guild_settings", sa.Column("featured_note", sa.String(140), nullable=True))
    op.add_column(
        "guild_settings", sa.Column("featured_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("guild_settings", "featured_at")
    op.drop_column("guild_settings", "featured_note")
    op.drop_column("guild_settings", "featured_brawlhalla_id")
    op.drop_index("ix_player_reports_reporter_discord_id", table_name="player_reports")
    op.drop_index("ix_player_reports_guild_id", table_name="player_reports")
    op.drop_table("player_reports")
