"""clan_war_results

Revision ID: 0028
Revises: 0027
Create Date: 2026-10-15

docs/DECISIONS.md ADR-131: a team's finished Clan Wars week, once per team
and week. The live week is computed from ranking snapshots and never stored.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0028"
down_revision: str | None = "0027"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "clan_war_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("guild_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "team_id", sa.Integer(), sa.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("season", sa.Integer(), nullable=False),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False),
        sa.Column("place", sa.Integer(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("team_id", "week_start", name="uq_clan_war_result"),
    )
    op.create_index("ix_clan_war_results_guild_id", "clan_war_results", ["guild_id"])
    op.create_index("ix_clan_war_results_team_id", "clan_war_results", ["team_id"])
    op.create_index("ix_clan_war_results_season", "clan_war_results", ["season"])


def downgrade() -> None:
    op.drop_index("ix_clan_war_results_season", table_name="clan_war_results")
    op.drop_index("ix_clan_war_results_team_id", table_name="clan_war_results")
    op.drop_index("ix_clan_war_results_guild_id", table_name="clan_war_results")
    op.drop_table("clan_war_results")
