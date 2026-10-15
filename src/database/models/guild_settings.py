"""Per-guild settings: the active setup mode and the last announced season.

See docs/DECISIONS.md ADR-011, ADR-015 and ADR-102.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String, false
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
    # Staff's /feature pick for the website's Featured Player (ADR-111): a
    # Brawlhalla account id, never a Discord id, so the API can expose it.
    featured_brawlhalla_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    featured_note: Mapped[str | None] = mapped_column(String(140), nullable=True)
    featured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Join access (ADR-123): the role a new member gets while approval is on,
    # the role that grants access (/approval, or on join while approval is
    # off), and the switch. Internal only; never exposed by the API.
    join_role_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    approved_role_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    approval_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    # Coaching (ADR-126): the Discord role whose holders are coaches, and the
    # channel coaching requests are posted in. Internal only.
    coach_role_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    coaching_channel_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"GuildSettings(guild_id={self.guild_id}, setup_mode={self.setup_mode!r})"
