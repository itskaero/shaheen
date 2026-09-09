"""A Discord account known to Shaheen, independent of any one guild."""

from __future__ import annotations

from sqlalchemy import BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import Base, TimestampMixin


class DiscordUser(TimestampMixin, Base):
    __tablename__ = "discord_users"

    id: Mapped[int] = mapped_column(primary_key=True)
    discord_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"DiscordUser(discord_id={self.discord_id})"
