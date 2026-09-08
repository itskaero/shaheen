"""competition tables: matches, challenges, scrims, tournaments

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-08

Phase 4 (docs/ROADMAP.md): challenges, scrims, match records, tournaments,
match history. See docs/DECISIONS.md ADR-033 through ADR-038.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "matches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("guild_id", sa.BigInteger(), nullable=False),
        sa.Column("kind", sa.String(length=8), nullable=False),
        sa.Column(
            "status", sa.String(length=24), nullable=False, server_default="pending_confirmation"
        ),
        sa.Column(
            "reported_by_member_id", sa.Integer(), sa.ForeignKey("shaheen_members.id"), nullable=True
        ),
        sa.Column("reported_winning_side", sa.String(length=1), nullable=True),
        sa.Column("winning_side", sa.String(length=1), nullable=True),
        sa.Column(
            "resolved_by_member_id", sa.Integer(), sa.ForeignKey("shaheen_members.id"), nullable=True
        ),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_matches_guild_id", "matches", ["guild_id"])

    op.create_table(
        "match_participants",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("match_id", sa.Integer(), sa.ForeignKey("matches.id"), nullable=False),
        sa.Column(
            "shaheen_member_id", sa.Integer(), sa.ForeignKey("shaheen_members.id"), nullable=False
        ),
        sa.Column("side", sa.String(length=1), nullable=False),
        sa.UniqueConstraint("match_id", "shaheen_member_id", name="uq_match_participant"),
    )
    op.create_index("ix_match_participants_match_id", "match_participants", ["match_id"])
    op.create_index(
        "ix_match_participants_shaheen_member_id", "match_participants", ["shaheen_member_id"]
    )

    op.create_table(
        "challenges",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("guild_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "challenger_member_id",
            sa.Integer(),
            sa.ForeignKey("shaheen_members.id"),
            nullable=False,
        ),
        sa.Column(
            "opponent_member_id", sa.Integer(), sa.ForeignKey("shaheen_members.id"), nullable=False
        ),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("match_id", sa.Integer(), sa.ForeignKey("matches.id"), nullable=True),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_challenges_guild_id", "challenges", ["guild_id"])

    op.create_table(
        "scrims",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("guild_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_by_member_id",
            sa.Integer(),
            sa.ForeignKey("shaheen_members.id"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(length=8), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="open"),
        sa.Column("match_id", sa.Integer(), sa.ForeignKey("matches.id"), nullable=True),
        sa.Column("announcement_channel_id", sa.BigInteger(), nullable=True),
        sa.Column("announcement_message_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_scrims_guild_id", "scrims", ["guild_id"])

    op.create_table(
        "scrim_signups",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("scrim_id", sa.Integer(), sa.ForeignKey("scrims.id"), nullable=False),
        sa.Column(
            "shaheen_member_id", sa.Integer(), sa.ForeignKey("shaheen_members.id"), nullable=False
        ),
        sa.Column("side", sa.String(length=1), nullable=False),
        sa.UniqueConstraint("scrim_id", "shaheen_member_id", name="uq_scrim_signup"),
    )
    op.create_index("ix_scrim_signups_scrim_id", "scrim_signups", ["scrim_id"])
    op.create_index(
        "ix_scrim_signups_shaheen_member_id", "scrim_signups", ["shaheen_member_id"]
    )

    op.create_table(
        "tournaments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("guild_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("kind", sa.String(length=8), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="registration"),
        sa.Column(
            "created_by_member_id",
            sa.Integer(),
            sa.ForeignKey("shaheen_members.id"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_tournaments_guild_id", "tournaments", ["guild_id"])

    op.create_table(
        "tournament_entrants",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tournament_id", sa.Integer(), sa.ForeignKey("tournaments.id"), nullable=False),
        sa.Column("seed", sa.Integer(), nullable=True),
        sa.Column("eliminated", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index(
        "ix_tournament_entrants_tournament_id", "tournament_entrants", ["tournament_id"]
    )

    op.create_table(
        "tournament_entrant_members",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "tournament_entrant_id",
            sa.Integer(),
            sa.ForeignKey("tournament_entrants.id"),
            nullable=False,
        ),
        sa.Column(
            "shaheen_member_id", sa.Integer(), sa.ForeignKey("shaheen_members.id"), nullable=False
        ),
        sa.UniqueConstraint(
            "tournament_entrant_id", "shaheen_member_id", name="uq_entrant_member"
        ),
    )
    op.create_index(
        "ix_tournament_entrant_members_tournament_entrant_id",
        "tournament_entrant_members",
        ["tournament_entrant_id"],
    )
    op.create_index(
        "ix_tournament_entrant_members_shaheen_member_id",
        "tournament_entrant_members",
        ["shaheen_member_id"],
    )

    op.create_table(
        "tournament_matches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tournament_id", sa.Integer(), sa.ForeignKey("tournaments.id"), nullable=False),
        sa.Column("round_number", sa.Integer(), nullable=False),
        sa.Column("slot_index", sa.Integer(), nullable=False),
        sa.Column(
            "entrant_a_id", sa.Integer(), sa.ForeignKey("tournament_entrants.id"), nullable=True
        ),
        sa.Column(
            "entrant_b_id", sa.Integer(), sa.ForeignKey("tournament_entrants.id"), nullable=True
        ),
        sa.Column("match_id", sa.Integer(), sa.ForeignKey("matches.id"), nullable=True),
        sa.Column(
            "winner_entrant_id",
            sa.Integer(),
            sa.ForeignKey("tournament_entrants.id"),
            nullable=True,
        ),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.UniqueConstraint(
            "tournament_id", "round_number", "slot_index", name="uq_tournament_bracket_slot"
        ),
    )
    op.create_index(
        "ix_tournament_matches_tournament_id", "tournament_matches", ["tournament_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_tournament_matches_tournament_id", table_name="tournament_matches")
    op.drop_table("tournament_matches")

    op.drop_index(
        "ix_tournament_entrant_members_shaheen_member_id", table_name="tournament_entrant_members"
    )
    op.drop_index(
        "ix_tournament_entrant_members_tournament_entrant_id",
        table_name="tournament_entrant_members",
    )
    op.drop_table("tournament_entrant_members")

    op.drop_index("ix_tournament_entrants_tournament_id", table_name="tournament_entrants")
    op.drop_table("tournament_entrants")

    op.drop_index("ix_tournaments_guild_id", table_name="tournaments")
    op.drop_table("tournaments")

    op.drop_index("ix_scrim_signups_shaheen_member_id", table_name="scrim_signups")
    op.drop_index("ix_scrim_signups_scrim_id", table_name="scrim_signups")
    op.drop_table("scrim_signups")

    op.drop_index("ix_scrims_guild_id", table_name="scrims")
    op.drop_table("scrims")

    op.drop_index("ix_challenges_guild_id", table_name="challenges")
    op.drop_table("challenges")

    op.drop_index("ix_match_participants_shaheen_member_id", table_name="match_participants")
    op.drop_index("ix_match_participants_match_id", table_name="match_participants")
    op.drop_table("match_participants")

    op.drop_index("ix_matches_guild_id", table_name="matches")
    op.drop_table("matches")
