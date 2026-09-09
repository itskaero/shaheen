"""clan tables: ranking_snapshots, legend_snapshots, achievements (+seed), member_achievements

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-08

Phase 3 (docs/ROADMAP.md): scheduled snapshots, achievements, Hall of Fame,
milestone announcements. The achievements seed data is a literal copy of
services/achievements.py's CATALOG at the time this migration was written
— see docs/DECISIONS.md ADR-030 for why it's copied rather than imported.
"""

from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ACHIEVEMENTS_TABLE = sa.table(
    "achievements",
    sa.column("key", sa.String),
    sa.column("name", sa.String),
    sa.column("description", sa.String),
    # timezone=True here must match the real column type declared for
    # "achievements" below — this lightweight sa.table/sa.column pair only
    # exists to tell op.bulk_insert() how to bind these parameters, and a
    # mismatch (naive-typed bind vs. the tz-aware `now` value passed below)
    # makes asyncpg's codec raise "can't subtract offset-naive and
    # offset-aware datetimes" against real Postgres — sqlite's driver
    # doesn't enforce this, so it doesn't show up there.
    sa.column("created_at", sa.DateTime(timezone=True)),
    sa.column("updated_at", sa.DateTime(timezone=True)),
)

_SEED_ACHIEVEMENTS = (
    ("first_link", "First Contact", "Linked a Brawlhalla account to Shaheen."),
    ("games_100", "Centurion", "Played 100 games."),
    ("games_500", "Battle-Hardened", "Played 500 games."),
    ("tier_platinum", "Platinum Shaheen", "Reached Platinum tier in ranked."),
    ("tier_diamond_plus", "Diamond Shaheen", "Reached Diamond tier or higher in ranked."),
)


def upgrade() -> None:
    op.create_table(
        "ranking_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "brawlhalla_player_id",
            sa.Integer(),
            sa.ForeignKey("brawlhalla_players.id"),
            nullable=False,
        ),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=True),
        sa.Column("peak_rating", sa.Integer(), nullable=True),
        sa.Column("tier", sa.String(length=32), nullable=True),
        sa.Column("wins", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("games", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("region", sa.String(length=16), nullable=True),
        sa.Column("global_rank", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_ranking_snapshots_brawlhalla_player_id", "ranking_snapshots", ["brawlhalla_player_id"]
    )
    op.create_index("ix_ranking_snapshots_captured_at", "ranking_snapshots", ["captured_at"])

    op.create_table(
        "legend_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "brawlhalla_player_id",
            sa.Integer(),
            sa.ForeignKey("brawlhalla_players.id"),
            nullable=False,
        ),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("legend_id", sa.Integer(), nullable=False),
        sa.Column("legend_name_key", sa.String(length=32), nullable=False),
        sa.Column("games", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("wins", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("kos", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("damagedealt", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("falls", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_legend_snapshots_brawlhalla_player_id", "legend_snapshots", ["brawlhalla_player_id"]
    )
    op.create_index("ix_legend_snapshots_captured_at", "legend_snapshots", ["captured_at"])

    op.create_table(
        "achievements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("description", sa.String(length=256), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("key", name="uq_achievements_key"),
    )
    op.create_index("ix_achievements_key", "achievements", ["key"])

    now = datetime.now(UTC)
    op.bulk_insert(
        _ACHIEVEMENTS_TABLE,
        [
            {"key": key, "name": name, "description": description, "created_at": now, "updated_at": now}
            for key, name, description in _SEED_ACHIEVEMENTS
        ],
    )

    op.create_table(
        "member_achievements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "shaheen_member_id", sa.Integer(), sa.ForeignKey("shaheen_members.id"), nullable=False
        ),
        sa.Column(
            "achievement_id", sa.Integer(), sa.ForeignKey("achievements.id"), nullable=False
        ),
        sa.Column("awarded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("extra", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "shaheen_member_id", "achievement_id", name="uq_member_achievement"
        ),
    )
    op.create_index(
        "ix_member_achievements_shaheen_member_id", "member_achievements", ["shaheen_member_id"]
    )
    op.create_index(
        "ix_member_achievements_achievement_id", "member_achievements", ["achievement_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_member_achievements_achievement_id", table_name="member_achievements")
    op.drop_index("ix_member_achievements_shaheen_member_id", table_name="member_achievements")
    op.drop_table("member_achievements")

    op.drop_index("ix_achievements_key", table_name="achievements")
    op.drop_table("achievements")

    op.drop_index("ix_legend_snapshots_captured_at", table_name="legend_snapshots")
    op.drop_index("ix_legend_snapshots_brawlhalla_player_id", table_name="legend_snapshots")
    op.drop_table("legend_snapshots")

    op.drop_index("ix_ranking_snapshots_captured_at", table_name="ranking_snapshots")
    op.drop_index("ix_ranking_snapshots_brawlhalla_player_id", table_name="ranking_snapshots")
    op.drop_table("ranking_snapshots")
