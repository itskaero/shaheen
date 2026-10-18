"""A team's finished Clan Wars week (docs/DECISIONS.md ADR-131).

The live week is computed from ranking snapshots and never stored. Once a
week is over its standings are kept, once each per team and week, so a tick
that runs twice can't record a week twice. The season table is built from
these rows.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import Base


class ClanWarResult(Base):
    __tablename__ = "clan_war_results"
    __table_args__ = (UniqueConstraint("team_id", "week_start", name="uq_clan_war_result"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, index=True
    )
    season: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    # The Monday (Pakistan time) the war week began.
    week_start: Mapped[date] = mapped_column(Date, nullable=False)
    points: Mapped[int] = mapped_column(Integer, nullable=False)
    # 1 is the week's winner.
    place: Mapped[int] = mapped_column(Integer, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # The week's MVP, its top scorer from any team (ADR-136): stored on every
    # row of the week, so any team's row answers "who was MVP".
    mvp_brawlhalla_player_id: Mapped[int | None] = mapped_column(
        ForeignKey("brawlhalla_players.id", ondelete="SET NULL"), nullable=True
    )
    mvp_points: Mapped[int | None] = mapped_column(Integer, nullable=True)
