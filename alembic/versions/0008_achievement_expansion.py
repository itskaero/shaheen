"""achievement expansion: catalog 5 -> 30, achievements.category, ranking_snapshots.region_rank

Revision ID: 0008
Revises: 0007
Create Date: 2026-09-17

Backs docs/DECISIONS.md ADR-081. The old 5-entry catalog couldn't tell
members apart: first_link goes to everyone who links, and games_100/500
measure lifetime career games, which any established player clears on
their first snapshot. This seeds 25 more across four sources (ranked
standings, clan competition, community, tenure), adds a `category` so a
30-entry gallery stays readable, and adds `region_rank` — fetched from the
Brawlhalla API and displayed in Discord since Phase 2, but never stored,
so nothing could ever award on it.

Seed rows are a literal copy of services/achievements.py's CATALOG rather
than an import, per the rule in database/models/achievement.py: migrations
must stay stable even when that catalog changes later.
"""

from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ACHIEVEMENTS_TABLE = sa.table(
    "achievements",
    sa.column("key", sa.String),
    sa.column("name", sa.String),
    sa.column("description", sa.String),
    sa.column("category", sa.String),
    # timezone=True must match the real column type — see 0003's note: a
    # naive-typed bind against a tz-aware value makes asyncpg raise.
    sa.column("created_at", sa.DateTime(timezone=True)),
    sa.column("updated_at", sa.DateTime(timezone=True)),
)

# Categories for the five rows 0003 already seeded.
_EXISTING_CATEGORIES = (
    ("first_link", "onboarding"),
    ("games_100", "milestone"),
    ("games_500", "milestone"),
    ("tier_platinum", "ranked"),
    ("tier_diamond_plus", "ranked"),
)

# The 25 new ones. (key, name, description, category)
_NEW_ACHIEVEMENTS = (
    ("games_1000", "Veteran of a Thousand", "Played 1,000 games.", "milestone"),
    ("games_2500", "Relentless", "Played 2,500 games.", "milestone"),
    ("games_5000", "Unbroken", "Played 5,000 games.", "milestone"),
    ("tier_gold", "Gold Shaheen", "Reached Gold tier in ranked.", "ranked"),
    ("tier_valhallan", "Valhallan", "Reached Valhallan — the top of the ladder.", "ranked"),
    ("peak_1500", "Ascendant", "Hit a peak rating of 1500.", "ranked"),
    ("peak_1800", "Skyborne", "Hit a peak rating of 1800.", "ranked"),
    ("peak_2000", "Above the Clouds", "Hit a peak rating of 2000.", "ranked"),
    ("global_top_1000", "Global Elite", "Ranked inside the global top 1,000.", "ranked"),
    ("region_top_100", "Regional Force", "Ranked inside the top 100 of your region.", "ranked"),
    ("win_rate_60", "Sharpened", "Held a 60% ranked win rate over 50+ ranked games.", "ranked"),
    ("first_win", "First Blood", "Won your first clan match.", "competition"),
    ("wins_10", "Contender", "Won 10 clan matches.", "competition"),
    ("wins_50", "Dominator", "Won 50 clan matches.", "competition"),
    ("tournament_entrant", "Bracket Debut", "Entered your first clan tournament.", "competition"),
    ("tournament_finalist", "Finalist", "Reached a clan tournament final.", "competition"),
    ("tournament_champion", "Champion", "Won a clan tournament.", "competition"),
    ("scrim_regular", "Sparring Partner", "Joined 10 clan scrims.", "competition"),
    ("chat_level_10", "Voice of the Nest", "Reached chat level 10.", "community"),
    ("chat_level_25", "Nest Elder", "Reached chat level 25.", "community"),
    ("chat_level_50", "Keeper of the Nest", "Reached chat level 50.", "community"),
    ("mvp_of_week", "MVP of the Week", "Named MVP in a weekly digest.", "community"),
    ("veteran_30d", "One Moon", "30 days with Shaheen.", "tenure"),
    ("veteran_180d", "Half a Year Higher", "180 days with Shaheen.", "tenure"),
    ("veteran_365d", "Year of the Shaheen", "365 days with Shaheen.", "tenure"),
)


def upgrade() -> None:
    op.add_column(
        "ranking_snapshots", sa.Column("region_rank", sa.Integer(), nullable=True)
    )
    op.add_column(
        "achievements",
        sa.Column("category", sa.String(length=32), nullable=False, server_default="milestone"),
    )

    for key, category in _EXISTING_CATEGORIES:
        op.execute(
            sa.update(_ACHIEVEMENTS_TABLE)
            .where(_ACHIEVEMENTS_TABLE.c.key == key)
            .values(category=category)
        )

    now = datetime.now(UTC)
    op.bulk_insert(
        _ACHIEVEMENTS_TABLE,
        [
            {
                "key": key,
                "name": name,
                "description": description,
                "category": category,
                "created_at": now,
                "updated_at": now,
            }
            for key, name, description, category in _NEW_ACHIEVEMENTS
        ],
    )


def downgrade() -> None:
    # Delete exactly the keys this revision added — member_achievements
    # rows referencing them go first so the FK stays satisfied.
    new_keys = [key for key, _name, _description, _category in _NEW_ACHIEVEMENTS]
    op.execute(
        sa.text(
            "DELETE FROM member_achievements WHERE achievement_id IN "
            "(SELECT id FROM achievements WHERE key IN :keys)"
        ).bindparams(sa.bindparam("keys", value=new_keys, expanding=True))
    )
    op.execute(
        sa.delete(_ACHIEVEMENTS_TABLE).where(_ACHIEVEMENTS_TABLE.c.key.in_(new_keys))
    )

    op.drop_column("achievements", "category")
    op.drop_column("ranking_snapshots", "region_rank")
