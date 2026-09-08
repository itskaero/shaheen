"""initial setup tables: provisioned_resources, guild_settings

Revision ID: 0001
Revises:
Create Date: 2026-09-08

Phase 1 database scope is setup-only — see docs/DECISIONS.md ADR-014.
DiscordUser/ShaheenMember/BrawlhallaPlayer and the rest of
docs/DATABASE.md's entities arrive with the Phase 2 migration that
introduces /link.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "provisioned_resources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("guild_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "resource_type",
            sa.Enum("role", "category", "channel", name="resource_type", native_enum=False, length=16),
            nullable=False,
        ),
        sa.Column("logical_key", sa.String(length=128), nullable=False),
        sa.Column("discord_id", sa.BigInteger(), nullable=False),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "guild_id", "resource_type", "logical_key", name="uq_resource_identity"
        ),
    )
    op.create_index(
        "ix_provisioned_resources_guild_id",
        "provisioned_resources",
        ["guild_id"],
    )

    op.create_table(
        "guild_settings",
        sa.Column("guild_id", sa.BigInteger(), primary_key=True),
        sa.Column("setup_mode", sa.String(length=16), nullable=False, server_default="development"),
        sa.Column("last_setup_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("guild_settings")
    op.drop_index("ix_provisioned_resources_guild_id", table_name="provisioned_resources")
    op.drop_table("provisioned_resources")
