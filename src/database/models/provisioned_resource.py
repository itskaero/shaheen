"""Tracks Discord resources created by /setup, for idempotent re-runs.

See docs/DECISIONS.md ADR-011 and docs/SETUP_FLOW.md's idempotency
requirement: find existing resources by stored ID before falling back to
name matching.
"""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import Base, TimestampMixin


class ResourceType(enum.StrEnum):
    ROLE = "role"
    CATEGORY = "category"
    CHANNEL = "channel"


class ProvisionedResource(TimestampMixin, Base):
    """One Discord role/category/channel that /setup is responsible for.

    `logical_key` is the stable, code-defined identifier for the resource
    (e.g. "role:shaheen_leader", "channel:announcements") — see
    bot/constants.py, which is the single source of truth for these keys.
    """

    __tablename__ = "provisioned_resources"
    __table_args__ = (
        UniqueConstraint("guild_id", "resource_type", "logical_key", name="uq_resource_identity"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    resource_type: Mapped[ResourceType] = mapped_column(
        Enum(ResourceType, native_enum=False, length=16), nullable=False
    )
    logical_key: Mapped[str] = mapped_column(String(128), nullable=False)
    discord_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    last_verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return (
            f"ProvisionedResource(guild_id={self.guild_id}, "
            f"resource_type={self.resource_type}, logical_key={self.logical_key!r}, "
            f"discord_id={self.discord_id})"
        )
