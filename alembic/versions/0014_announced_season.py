"""guild_settings.announced_season: last season-start post

Revision ID: 0014
Revises: 0013
Create Date: 2026-09-23

docs/DECISIONS.md ADR-102 — the bot announces each new Pakistan season once;
this remembers which Brawlhalla season it last announced.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("guild_settings", sa.Column("announced_season", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("guild_settings") as batch:
        batch.drop_column("announced_season")
