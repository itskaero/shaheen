"""Reaction roles (docs/DECISIONS.md ADR-137): react to a message, get a role.

One row per (message, emoji). `emoji` is stored normalised by
services/reaction_roles.normalize_emoji: a Unicode emoji without its
variation selector, or a custom one as `<:name:id>`.
"""

from __future__ import annotations

from sqlalchemy import BigInteger, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import Base, TimestampMixin


class ReactionRole(TimestampMixin, Base):
    __tablename__ = "reaction_roles"
    __table_args__ = (
        UniqueConstraint("message_id", "emoji", name="uq_reaction_role_message_emoji"),
        Index("ix_reaction_roles_guild", "guild_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    channel_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    message_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    emoji: Mapped[str] = mapped_column(String(80), nullable=False)
    role_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
