"""Per-guild settings, currently just the active setup mode.

See docs/DECISIONS.md ADR-011 and ADR-015.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import Base, TimestampMixin


class GuildSettings(TimestampMixin, Base):
    """Persisted per-guild configuration set by /setup."""

    __tablename__ = "guild_settings"

    guild_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    setup_mode: Mapped[str] = mapped_column(String(16), nullable=False, default="development")
    last_setup_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"GuildSettings(guild_id={self.guild_id}, setup_mode={self.setup_mode!r})"
