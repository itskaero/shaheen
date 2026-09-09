"""identity tables: discord_users, shaheen_members, brawlhalla_players, member_player_links

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-08

Phase 2 (docs/ROADMAP.md): adds the identity/linking schema behind /link,
/unlink, /profile, /rank, /stats, /legends. RankingSnapshot/LegendSnapshot
are deferred to Phase 3 — see docs/DECISIONS.md ADR-024.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "discord_users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("discord_id", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("discord_id", name="uq_discord_users_discord_id"),
    )
    op.create_index("ix_discord_users_discord_id", "discord_users", ["discord_id"])

    op.create_table(
        "shaheen_members",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("discord_user_id", sa.Integer(), sa.ForeignKey("discord_users.id"), nullable=False),
        sa.Column("guild_id", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("discord_user_id", "guild_id", name="uq_member_per_guild"),
    )
    op.create_index("ix_shaheen_members_discord_user_id", "shaheen_members", ["discord_user_id"])
    op.create_index("ix_shaheen_members_guild_id", "shaheen_members", ["guild_id"])

    op.create_table(
        "brawlhalla_players",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("brawlhalla_player_id", sa.BigInteger(), nullable=False),
        sa.Column("player_name", sa.String(length=64), nullable=False),
        sa.Column("region", sa.String(length=16), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("brawlhalla_player_id", name="uq_brawlhalla_players_player_id"),
    )
    op.create_index(
        "ix_brawlhalla_players_brawlhalla_player_id", "brawlhalla_players", ["brawlhalla_player_id"]
    )

    op.create_table(
        "member_player_links",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "shaheen_member_id", sa.Integer(), sa.ForeignKey("shaheen_members.id"), nullable=False
        ),
        sa.Column(
            "brawlhalla_player_id",
            sa.Integer(),
            sa.ForeignKey("brawlhalla_players.id"),
            nullable=False,
        ),
        sa.Column("linked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("unlinked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_member_player_links_shaheen_member_id", "member_player_links", ["shaheen_member_id"]
    )
    op.create_index(
        "ix_member_player_links_brawlhalla_player_id",
        "member_player_links",
        ["brawlhalla_player_id"],
    )
    # At most one active (unlinked_at IS NULL) link per member.
    op.create_index(
        "uq_one_active_link_per_member",
        "member_player_links",
        ["shaheen_member_id"],
        unique=True,
        postgresql_where=sa.text("unlinked_at IS NULL"),
        sqlite_where=sa.text("unlinked_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_one_active_link_per_member", table_name="member_player_links")
    op.drop_index("ix_member_player_links_brawlhalla_player_id", table_name="member_player_links")
    op.drop_index("ix_member_player_links_shaheen_member_id", table_name="member_player_links")
    op.drop_table("member_player_links")

    op.drop_index("ix_brawlhalla_players_brawlhalla_player_id", table_name="brawlhalla_players")
    op.drop_table("brawlhalla_players")

    op.drop_index("ix_shaheen_members_guild_id", table_name="shaheen_members")
    op.drop_index("ix_shaheen_members_discord_user_id", table_name="shaheen_members")
    op.drop_table("shaheen_members")

    op.drop_index("ix_discord_users_discord_id", table_name="discord_users")
    op.drop_table("discord_users")
