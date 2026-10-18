"""Clan Wars rosters, locked at the start of each week (docs/DECISIONS.md ADR-136).

A player scores for the team they were on when the week began (Monday 00:00
PKT), so switching clans mid-week can't carry a week's points to another team.
The bot locks the roster on its first tick of the week; until then the
current rosters are used.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import BigInteger, Date, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import Base


class ClanWarRoster(Base):
    __tablename__ = "clan_war_rosters"
    __table_args__ = (
        UniqueConstraint("week_start", "brawlhalla_player_id", name="uq_clan_war_roster_player"),
        Index("ix_clan_war_rosters_guild_week", "guild_id", "week_start"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    week_start: Mapped[date] = mapped_column(Date, nullable=False)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    brawlhalla_player_id: Mapped[int] = mapped_column(
        ForeignKey("brawlhalla_players.id", ondelete="CASCADE"), nullable=False
    )
