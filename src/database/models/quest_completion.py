"""A weekly quest a player finished (docs/DECISIONS.md ADR-128).

Progress itself is never stored: it is worked out from the ranking snapshots
the bot already takes. Only completions are kept, once each per player, week
and quest, so a tick that runs twice can't award XP twice. Season XP is the
count of a season's completions.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import Base


class QuestCompletion(Base):
    __tablename__ = "quest_completions"
    __table_args__ = (
        UniqueConstraint(
            "brawlhalla_player_id", "week_start", "quest_key", name="uq_quest_completion"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    brawlhalla_player_id: Mapped[int] = mapped_column(
        ForeignKey("brawlhalla_players.id", ondelete="CASCADE"), nullable=False, index=True
    )
    season: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    # The Monday (Pakistan time) the quest week began.
    week_start: Mapped[date] = mapped_column(Date, nullable=False)
    quest_key: Mapped[str] = mapped_column(String(24), nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
