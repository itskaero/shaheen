"""pakistan_board_entries: players on the Pakistan leaderboard

Revision ID: 0011
Revises: 0010
Create Date: 2026-09-23

Backs docs/DECISIONS.md ADR-099 — a second leaderboard alongside the clan
one, holding Pakistani players who may not be Discord members at all.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pakistan_board_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("guild_id", sa.BigInteger(), nullable=False),
        sa.Column("brawlhalla_player_id", sa.Integer(), nullable=False),
        sa.Column("owner_discord_id", sa.BigInteger(), nullable=True),
        sa.Column("added_by_discord_id", sa.BigInteger(), nullable=False),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("removed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["brawlhalla_player_id"], ["brawlhalla_players.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pakistan_board_entries_guild_id", "pakistan_board_entries", ["guild_id"])
    op.create_index(
        "ix_pakistan_board_entries_brawlhalla_player_id",
        "pakistan_board_entries",
        ["brawlhalla_player_id"],
    )
    op.create_index(
        "uq_one_active_pakistan_entry_per_player",
        "pakistan_board_entries",
        ["guild_id", "brawlhalla_player_id"],
        unique=True,
        postgresql_where=sa.text("removed_at IS NULL"),
        sqlite_where=sa.text("removed_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_one_active_pakistan_entry_per_player", table_name="pakistan_board_entries")
    op.drop_index(
        "ix_pakistan_board_entries_brawlhalla_player_id", table_name="pakistan_board_entries"
    )
    op.drop_index("ix_pakistan_board_entries_guild_id", table_name="pakistan_board_entries")
    op.drop_table("pakistan_board_entries")
