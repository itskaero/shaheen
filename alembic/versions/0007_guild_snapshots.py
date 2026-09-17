"""guild_snapshots: append-only Discord guild-level stat snapshots

Revision ID: 0007
Revises: 0006
Create Date: 2026-09-17

Backs the clan page's new "Discord Members" / "Server Boost" stat tiles
(docs/DECISIONS.md ADR for this round). Guild-wide numbers only — no
per-member Discord identity — captured by the bot's existing snapshot tick
(src/bot/cogs/clan.py) from its already-cached discord.Guild object and
served by the read-only API via services/website_service.py. Same
append-only, captured_at-indexed shape as ranking_snapshots (0003).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "guild_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("guild_id", sa.BigInteger(), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("member_count", sa.Integer(), nullable=False),
        sa.Column("boost_tier", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("boost_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_guild_snapshots_guild_id", "guild_snapshots", ["guild_id"])
    op.create_index("ix_guild_snapshots_captured_at", "guild_snapshots", ["captured_at"])


def downgrade() -> None:
    op.drop_index("ix_guild_snapshots_captured_at", table_name="guild_snapshots")
    op.drop_index("ix_guild_snapshots_guild_id", table_name="guild_snapshots")
    op.drop_table("guild_snapshots")
