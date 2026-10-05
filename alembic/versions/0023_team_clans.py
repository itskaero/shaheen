"""Teams mirror in-game Brawlhalla clans; four clan teams

Revision ID: 0023
Revises: 0022
Create Date: 2026-10-05

docs/DECISIONS.md ADR-120:
- teams.brawlhalla_clan_id: the clan a team mirrors. The bot's snapshot tick
  reads each clan's member list and keeps the roster in step.
- team_members.source ("clan" | "manual") and clan_rank (Leader, Officer,
  Member, Recruit): a sync only removes the players it added.
- Seeds the owner's four clan teams in every known guild: Delight Esports
  (now linked to its clan, with colours for its new logo), Sigma Grinders,
  Revenant Wolf and Clan Monke. Their rosters fill on the bot's next tick.
"""

from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0023"
down_revision: str | None = "0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CLAN_TEAMS = (
    # slug, name, tag, clan id, accent, accent 2
    ("delight-esports", "Delight Esports", "DE", 2042085, "#e9c46a", "#1f6f8a"),
    ("sigma-grinders", "Sigma Grinders", "SG", 1777529, "#8b3dff", "#d9d4ff"),
    ("revenant-wolf", "Revenant Wolf", "RW", 2542774, "#e3122d", "#c7cad6"),
    ("clan-monke", "Clan Monke", "MONKE", 1389219, "#e8b923", "#2fbf4a"),
)


def upgrade() -> None:
    op.add_column("teams", sa.Column("brawlhalla_clan_id", sa.BigInteger(), nullable=True))
    op.add_column(
        "team_members",
        sa.Column("source", sa.String(8), nullable=False, server_default="manual"),
    )
    op.add_column("team_members", sa.Column("clan_rank", sa.String(16), nullable=True))

    bind = op.get_bind()
    now = datetime.now(UTC)
    guilds = sorted(
        {
            row[0]
            for row in bind.execute(
                sa.text(
                    "SELECT guild_id FROM shaheen_members UNION SELECT guild_id FROM guild_settings "
                    "UNION SELECT guild_id FROM teams"
                )
            )
        }
    )
    for guild_id in guilds:
        for slug, name, tag, clan_id, accent, accent2 in CLAN_TEAMS:
            values = {
                "guild": guild_id,
                "slug": slug,
                "clan": clan_id,
                "accent": accent,
                "accent2": accent2,
            }
            existing = bind.execute(
                sa.text("SELECT id FROM teams WHERE guild_id = :guild AND slug = :slug"), values
            ).first()
            if existing:
                bind.execute(
                    sa.text(
                        "UPDATE teams SET brawlhalla_clan_id = :clan, accent = :accent, "
                        "accent_secondary = :accent2, logo = :slug WHERE id = :id"
                    ),
                    {**values, "id": existing[0]},
                )
                continue
            bind.execute(
                sa.text(
                    "INSERT INTO teams (guild_id, slug, name, tag, country, logo, description, "
                    "is_founding, accent, accent_secondary, brawlhalla_clan_id, created_at, "
                    "updated_at) VALUES (:guild, :slug, :name, :tag, 'PK', :slug, NULL, "
                    ":founding, :accent, :accent2, :clan, :now, :now)"
                ),
                {**values, "name": name, "tag": tag, "founding": False, "now": now},
            )


def downgrade() -> None:
    op.drop_column("team_members", "clan_rank")
    op.drop_column("team_members", "source")
    op.drop_column("teams", "brawlhalla_clan_id")
