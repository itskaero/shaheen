"""Website account linking: link codes, audit log, verification, one link per player

Revision ID: 0017
Revises: 0016
Create Date: 2026-10-04

docs/DECISIONS.md ADR-107:
- link_codes: hashed one-time codes from /link, redeemed on the website.
- audit_log: who claimed, verified or reported what.
- member_player_links.verified_at / verified_by_discord_id: staff /verify.
- uq_one_active_link_per_player: a Brawlhalla account can be actively linked
  to at most one member. Nothing enforced that before, so any duplicate
  active links are resolved first: the earliest link keeps the account and
  later ones are closed (unlinked_at set), never deleted.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0017"
down_revision: str | None = "0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ACTIVE = sa.text("unlinked_at IS NULL")


def upgrade() -> None:
    op.create_table(
        "link_codes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code_hash", sa.String(64), nullable=False),
        sa.Column("guild_id", sa.BigInteger(), nullable=False),
        sa.Column("discord_id", sa.BigInteger(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("used_for_player_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["used_for_player_id"], ["brawlhalla_players.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code_hash"),
    )
    op.create_index("ix_link_codes_discord_id", "link_codes", ["discord_id"])

    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("guild_id", sa.BigInteger(), nullable=False),
        sa.Column("action", sa.String(48), nullable=False),
        sa.Column("source", sa.String(16), nullable=False),
        sa.Column("actor_discord_id", sa.BigInteger(), nullable=True),
        sa.Column("subject", sa.String(160), nullable=False),
        sa.Column("detail", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_log_guild_id", "audit_log", ["guild_id"])
    op.create_index("ix_audit_log_action", "audit_log", ["action"])

    op.add_column(
        "member_player_links", sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "member_player_links", sa.Column("verified_by_discord_id", sa.BigInteger(), nullable=True)
    )

    # Close all but the earliest active link per player before the index.
    op.execute(
        """
        UPDATE member_player_links SET unlinked_at = CURRENT_TIMESTAMP
        WHERE unlinked_at IS NULL AND id NOT IN (
            SELECT MIN(id) FROM member_player_links
            WHERE unlinked_at IS NULL GROUP BY brawlhalla_player_id
        )
        """
    )
    op.create_index(
        "uq_one_active_link_per_player",
        "member_player_links",
        ["brawlhalla_player_id"],
        unique=True,
        postgresql_where=_ACTIVE,
        sqlite_where=_ACTIVE,
    )


def downgrade() -> None:
    op.drop_index("uq_one_active_link_per_player", table_name="member_player_links")
    with op.batch_alter_table("member_player_links") as batch:
        batch.drop_column("verified_by_discord_id")
        batch.drop_column("verified_at")
    op.drop_index("ix_audit_log_action", table_name="audit_log")
    op.drop_index("ix_audit_log_guild_id", table_name="audit_log")
    op.drop_table("audit_log")
    op.drop_index("ix_link_codes_discord_id", table_name="link_codes")
    op.drop_table("link_codes")
