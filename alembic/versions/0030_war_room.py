"""clan war rosters, war room and spar ping settings

Revision ID: 0030
Revises: 0029
Create Date: 2026-10-17

docs/DECISIONS.md ADR-136: Clan Wars rosters locked per week, the war room's
channel and state, and the opt-in Spar Ping role.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0030"
down_revision: str | None = "0029"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SETTINGS_COLUMNS = (
    ("war_room_channel_id", sa.BigInteger()),
    ("war_room_message_id", sa.BigInteger()),
    ("war_room_leader_team_id", sa.Integer()),
    ("war_room_leader_week", sa.Date()),
    ("war_room_countdown_week", sa.Date()),
    ("war_room_verdict_week", sa.Date()),
    ("spar_role_id", sa.BigInteger()),
    ("spar_last_ping_at", sa.DateTime(timezone=True)),
)


def upgrade() -> None:
    op.create_table(
        "clan_war_rosters",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("guild_id", sa.BigInteger(), nullable=False),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column(
            "team_id", sa.Integer(), sa.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "brawlhalla_player_id",
            sa.Integer(),
            sa.ForeignKey("brawlhalla_players.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.UniqueConstraint("week_start", "brawlhalla_player_id", name="uq_clan_war_roster_player"),
    )
    op.create_index(
        "ix_clan_war_rosters_guild_week", "clan_war_rosters", ["guild_id", "week_start"]
    )
    with op.batch_alter_table("guild_settings") as batch:
        for name, kind in _SETTINGS_COLUMNS:
            batch.add_column(sa.Column(name, kind, nullable=True))
    with op.batch_alter_table("clan_war_results") as batch:
        batch.add_column(
            sa.Column(
                "mvp_brawlhalla_player_id",
                sa.Integer(),
                sa.ForeignKey(
                    "brawlhalla_players.id",
                    ondelete="SET NULL",
                    name="fk_clan_war_results_mvp_player",
                ),
                nullable=True,
            )
        )
        batch.add_column(sa.Column("mvp_points", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("clan_war_results") as batch:
        batch.drop_column("mvp_points")
        batch.drop_column("mvp_brawlhalla_player_id")
    with op.batch_alter_table("guild_settings") as batch:
        for name, _kind in reversed(_SETTINGS_COLUMNS):
            batch.drop_column(name)
    op.drop_index("ix_clan_war_rosters_guild_week", table_name="clan_war_rosters")
    op.drop_table("clan_war_rosters")
