"""A Brawlhalla player on the Pakistan leaderboard (docs/DECISIONS.md ADR-099).

Separate from MemberPlayerLink on purpose: the clan board is Discord
members who /link'd, while this board also holds Pakistani players staff
added by ID who may never have joined the server. Soft-deleted like links
(`removed_at`), and at most one active row per player per guild.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, text
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import Base, TimestampMixin

_ACTIVE_ONLY = text("removed_at IS NULL")


class PakistanBoardEntry(TimestampMixin, Base):
    __tablename__ = "pakistan_board_entries"
    __table_args__ = (
        Index(
            "uq_one_active_pakistan_entry_per_player",
            "guild_id",
            "brawlhalla_player_id",
            unique=True,
            postgresql_where=_ACTIVE_ONLY,
            sqlite_where=_ACTIVE_ONLY,
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    brawlhalla_player_id: Mapped[int] = mapped_column(
        ForeignKey("brawlhalla_players.id"), nullable=False, index=True
    )
    # Set when a member added themselves; None for a staff-added player.
    owner_discord_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    added_by_discord_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
