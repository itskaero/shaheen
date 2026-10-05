"""teams.accent / accent_secondary: each team's colours for its holographic card

Revision ID: 0022
Revises: 0021
Create Date: 2026-10-05

docs/DECISIONS.md ADR-117 — the WebGPU card shader is shared; a team's two
colours tint its foil. Seeds the two existing teams from their logos.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0022"
down_revision: str | None = "0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SEED = {
    "shaheen": ("#3df26e", "#f0168c"),  # emerald / magenta
    "delight-esports": ("#2ad4ff", "#9b3cff"),  # cyan / violet
}


def upgrade() -> None:
    op.add_column("teams", sa.Column("accent", sa.String(7), nullable=True))
    op.add_column("teams", sa.Column("accent_secondary", sa.String(7), nullable=True))
    for slug, (accent, second) in _SEED.items():
        op.execute(
            sa.text(
                "UPDATE teams SET accent = :a, accent_secondary = :b WHERE slug = :slug"
            ).bindparams(a=accent, b=second, slug=slug)
        )


def downgrade() -> None:
    op.drop_column("teams", "accent_secondary")
    op.drop_column("teams", "accent")
