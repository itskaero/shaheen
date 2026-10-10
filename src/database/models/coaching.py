"""Coaches and coaching requests (docs/DECISIONS.md ADR-126).

The Coach role in Discord decides who coaches: the bot mirrors its holders
into `coaches` (`active` follows the role; a coach who loses it keeps their
row and request history). A coach's public identity is their linked
Brawlhalla account (ADR-040); `discord_id` and `display_name` are internal and
never reach the API.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String, UniqueConstraint, true
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import Base, TimestampMixin

REQUEST_STATUSES = ("open", "accepted", "declined")


class Coach(TimestampMixin, Base):
    __tablename__ = "coaches"
    __table_args__ = (UniqueConstraint("guild_id", "discord_id", name="uq_coaches_guild_discord"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    discord_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    display_name: Mapped[str] = mapped_column(String(64), nullable=False)
    # Their linked account, refreshed on every sync; None until they /link.
    brawlhalla_player_id: Mapped[int | None] = mapped_column(
        ForeignKey("brawlhalla_players.id", ondelete="SET NULL"), nullable=True
    )
    specialty: Mapped[str | None] = mapped_column(String(80), nullable=True)
    # Up to three legend name keys, comma-separated.
    legends: Mapped[str | None] = mapped_column(String(120), nullable=True)
    availability: Mapped[str | None] = mapped_column(String(80), nullable=True)
    bio: Mapped[str | None] = mapped_column(String(280), nullable=True)
    accepting: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )
    active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )


class CoachingRequest(TimestampMixin, Base):
    __tablename__ = "coaching_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    coach_id: Mapped[int] = mapped_column(
        ForeignKey("coaches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    student_discord_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    message: Mapped[str] = mapped_column(String(280), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="open")
    # The request card in the coaching channel, once posted.
    channel_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
