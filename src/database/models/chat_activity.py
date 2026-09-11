"""Per-member chat XP/level (docs/DECISIONS.md ADR-065).

Keyed by raw `discord_id`/`guild_id`, not FK'd through `DiscordUser`/
`ShaheenMember` — everyone who talks earns XP, not just members who've
run `/link` (same reasoning as `Warning`).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import Base, TimestampMixin


class ChatActivity(TimestampMixin, Base):
    __tablename__ = "chat_activity"
    __table_args__ = (UniqueConstraint("guild_id", "discord_id", name="uq_chat_activity_member"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    discord_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    xp: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Stored redundantly for fast display/level-up diffing — always
    # derivable from xp via services.chat_gamification.level_for_xp.
    level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    message_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Drives the anti-spam cooldown — services.chat_gamification only
    # awards XP once per cooldown window per member.
    last_xp_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"ChatActivity(guild_id={self.guild_id}, discord_id={self.discord_id}, xp={self.xp})"
