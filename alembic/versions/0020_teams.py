"""Teams: SHAHEEN (founding team) and Delight Esports

Revision ID: 0020
Revises: 0019
Create Date: 2026-10-05

docs/DECISIONS.md ADR-114:
- teams, team_members: rosters of Brawlhalla players, history kept via
  left_at, at most one active team per player.
- Seeds every known guild with SHAHEEN, the founding team, whose roster is
  every player currently linked by a member (what "SHAHEEN" meant on the
  site until now), and Delight Esports with an empty roster for staff to
  fill with /team add.
"""

from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0020"
down_revision: str | None = "0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ACTIVE = sa.text("left_at IS NULL")

_SEED = (
    {
        "slug": "shaheen",
        "name": "SHAHEEN",
        "tag": "SHN",
        "logo": "shaheen",
        "description": "The clan BRAWLISTAN grew out of. Pakistan's founding team.",
        "is_founding": True,
    },
    {
        "slug": "delight-esports",
        "name": "Delight Esports",
        "tag": "DE",
        "logo": "delight-esports",
        "description": None,
        "is_founding": False,
    },
)


def upgrade() -> None:
    teams = op.create_table(
        "teams",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("guild_id", sa.BigInteger(), nullable=False),
        sa.Column("slug", sa.String(48), nullable=False),
        sa.Column("name", sa.String(40), nullable=False),
        sa.Column("tag", sa.String(6), nullable=False),
        sa.Column("country", sa.String(2), nullable=False),
        sa.Column("logo", sa.String(48), nullable=True),
        sa.Column("description", sa.String(280), nullable=True),
        sa.Column("is_founding", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_teams_guild_id", "teams", ["guild_id"])
    op.create_index("uq_teams_guild_slug", "teams", ["guild_id", "slug"], unique=True)

    members = op.create_table(
        "team_members",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("brawlhalla_player_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("left_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"]),
        sa.ForeignKeyConstraint(["brawlhalla_player_id"], ["brawlhalla_players.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_team_members_team_id", "team_members", ["team_id"])
    op.create_index(
        "uq_one_active_team_per_player",
        "team_members",
        ["brawlhalla_player_id"],
        unique=True,
        postgresql_where=_ACTIVE,
        sqlite_where=_ACTIVE,
    )

    _seed(teams, members)


def _seed(teams: sa.Table, members: sa.Table) -> None:
    bind = op.get_bind()
    now = datetime.now(UTC)
    guilds = sorted(
        {
            row[0]
            for row in bind.execute(
                sa.text(
                    "SELECT guild_id FROM shaheen_members UNION SELECT guild_id FROM guild_settings"
                )
            )
        }
    )
    for guild_id in guilds:
        team_ids = {}
        for team in _SEED:
            result = bind.execute(
                teams.insert().values(
                    guild_id=guild_id, country="PK", created_at=now, updated_at=now, **team
                )
            )
            team_ids[team["slug"]] = result.inserted_primary_key[0]
        linked = bind.execute(
            sa.text(
                "SELECT DISTINCT l.brawlhalla_player_id FROM member_player_links l "
                "JOIN shaheen_members m ON m.id = l.shaheen_member_id "
                "WHERE m.guild_id = :guild AND l.unlinked_at IS NULL"
            ),
            {"guild": guild_id},
        )
        for (player_id,) in linked:
            bind.execute(
                members.insert().values(
                    team_id=team_ids["shaheen"],
                    brawlhalla_player_id=player_id,
                    role="player",
                    joined_at=now,
                    created_at=now,
                    updated_at=now,
                )
            )


def downgrade() -> None:
    op.drop_index("uq_one_active_team_per_player", table_name="team_members")
    op.drop_index("ix_team_members_team_id", table_name="team_members")
    op.drop_table("team_members")
    op.drop_index("uq_teams_guild_slug", table_name="teams")
    op.drop_index("ix_teams_guild_id", table_name="teams")
    op.drop_table("teams")
