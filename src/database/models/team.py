"""Teams in the BRAWLISTAN network (docs/DECISIONS.md ADR-114).

A roster holds Brawlhalla players, not Discord members, so a player who
isn't in the server can still be on a team. Memberships are never deleted:
leaving sets `left_at`, keeping a team's history. A player is on at most one
team at a time (partial unique index).

SHAHEEN, the clan BRAWLISTAN grew from, is the founding team
(`is_founding`).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import Base, TimestampMixin

TEAM_ROLES = ("captain", "player")
_ACTIVE = text("left_at IS NULL")


class Team(TimestampMixin, Base):
    __tablename__ = "teams"
    __table_args__ = (Index("uq_teams_guild_slug", "guild_id", "slug", unique=True),)

    id: Mapped[int] = mapped_column(primary_key=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(48), nullable=False)
    name: Mapped[str] = mapped_column(String(40), nullable=False)
    tag: Mapped[str] = mapped_column(String(6), nullable=False)
    country: Mapped[str] = mapped_column(String(2), nullable=False, default="PK")
    # web/assets/img/teams/<logo>.{webp,png}; None shows a monogram.
    logo: Mapped[str | None] = mapped_column(String(48), nullable=True)
    description: Mapped[str | None] = mapped_column(String(280), nullable=True)
    is_founding: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # The team's two colours as #rrggbb (ADR-117): they tint its holographic
    # card. None uses the BRAWLISTAN emerald and magenta.
    accent: Mapped[str | None] = mapped_column(String(7), nullable=True)
    accent_secondary: Mapped[str | None] = mapped_column(String(7), nullable=True)


class TeamMember(TimestampMixin, Base):
    __tablename__ = "team_members"
    __table_args__ = (
        Index(
            "uq_one_active_team_per_player",
            "brawlhalla_player_id",
            unique=True,
            postgresql_where=_ACTIVE,
            sqlite_where=_ACTIVE,
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False, index=True)
    brawlhalla_player_id: Mapped[int] = mapped_column(
        ForeignKey("brawlhalla_players.id"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="player")
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    left_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # The player's choice to wear the team tag next to their name, e.g.
    # "[SHN] kaero." on the rankings (ADR-115). On by default.
    show_tag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
