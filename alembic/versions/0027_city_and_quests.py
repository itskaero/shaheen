"""brawlhalla_players.city and quest_completions

Revision ID: 0027
Revises: 0026
Create Date: 2026-10-15

docs/DECISIONS.md ADR-128:
- brawlhalla_players.city: the Pakistani city a player represents (City Wars).
- quest_completions: a weekly quest a player finished, once per player, week
  and quest. Progress is computed from ranking snapshots and never stored.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0027"
down_revision: str | None = "0026"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("brawlhalla_players", sa.Column("city", sa.String(24), nullable=True))
    op.create_index("ix_brawlhalla_players_city", "brawlhalla_players", ["city"])
    op.create_table(
        "quest_completions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "brawlhalla_player_id",
            sa.Integer(),
            sa.ForeignKey("brawlhalla_players.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("season", sa.Integer(), nullable=False),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("quest_key", sa.String(24), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "brawlhalla_player_id", "week_start", "quest_key", name="uq_quest_completion"
        ),
    )
    op.create_index(
        "ix_quest_completions_brawlhalla_player_id", "quest_completions", ["brawlhalla_player_id"]
    )
    op.create_index("ix_quest_completions_season", "quest_completions", ["season"])


def downgrade() -> None:
    op.drop_index("ix_quest_completions_season", table_name="quest_completions")
    op.drop_index("ix_quest_completions_brawlhalla_player_id", table_name="quest_completions")
    op.drop_table("quest_completions")
    op.drop_index("ix_brawlhalla_players_city", table_name="brawlhalla_players")
    op.drop_column("brawlhalla_players", "city")
