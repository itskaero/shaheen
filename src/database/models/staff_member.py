"""Founders and Admins shown on the Founding Team page (docs/DECISIONS.md ADR-135).

The bot mirrors the holders of the Founder and Admin roles here, like the
Coach role (ADR-126). What the website may show is deliberately narrow: the
member's server display name (or their linked Brawlhalla name), their role
and their avatar image, which is stored here so the public page never needs
a Discord CDN URL (those carry the user id). `discord_id` and `avatar_key`
are internal and never reach the API.
"""

from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    Boolean,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    UniqueConstraint,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import Base, TimestampMixin

STAFF_ROLES = ("founder", "admin")  # display order


class StaffMember(TimestampMixin, Base):
    __tablename__ = "staff_members"
    __table_args__ = (UniqueConstraint("guild_id", "discord_id", name="uq_staff_guild_discord"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    discord_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    # "founder" or "admin": the highest of the two the member holds.
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    # The member's name in the server (nickname, else global display name).
    display_name: Mapped[str] = mapped_column(String(64), nullable=False)
    # Their linked account, refreshed on every sync; None until they /link.
    brawlhalla_player_id: Mapped[int | None] = mapped_column(
        ForeignKey("brawlhalla_players.id", ondelete="SET NULL"), nullable=True
    )
    # Discord's avatar hash, to re-download only when it changes.
    avatar_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    avatar: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    avatar_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # Discord's role-list order within a role, so the page matches the server.
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )
