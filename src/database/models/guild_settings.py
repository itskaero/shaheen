"""Per-guild settings: the active setup mode and the last announced season.

See docs/DECISIONS.md ADR-011, ADR-015 and ADR-102.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import Base, TimestampMixin


class GuildSettings(TimestampMixin, Base):
    """Persisted per-guild configuration set by /setup."""

    __tablename__ = "guild_settings"

    guild_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    setup_mode: Mapped[str] = mapped_column(String(16), nullable=False, default="development")
    last_setup_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # The Brawlhalla season whose start the bot last announced (ADR-102).
    announced_season: Mapped[int | None] = mapped_column(Integer, nullable=True)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"GuildSettings(guild_id={self.guild_id}, setup_mode={self.setup_mode!r})"
