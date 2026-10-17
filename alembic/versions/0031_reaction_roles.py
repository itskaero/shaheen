"""reaction roles

Revision ID: 0031
Revises: 0030
Create Date: 2026-10-17

docs/DECISIONS.md ADR-137: react to a message to get a role.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0031"
down_revision: str | None = "0030"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "reaction_roles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("guild_id", sa.BigInteger(), nullable=False),
        sa.Column("channel_id", sa.BigInteger(), nullable=False),
        sa.Column("message_id", sa.BigInteger(), nullable=False),
        sa.Column("emoji", sa.String(length=80), nullable=False),
        sa.Column("role_id", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("message_id", "emoji", name="uq_reaction_role_message_emoji"),
    )
    op.create_index("ix_reaction_roles_guild", "reaction_roles", ["guild_id"])
    op.create_index("ix_reaction_roles_message_id", "reaction_roles", ["message_id"])


def downgrade() -> None:
    op.drop_index("ix_reaction_roles_message_id", table_name="reaction_roles")
    op.drop_index("ix_reaction_roles_guild", table_name="reaction_roles")
    op.drop_table("reaction_roles")
