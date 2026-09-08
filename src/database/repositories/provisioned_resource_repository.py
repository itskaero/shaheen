"""Persistence for ProvisionedResource — the /setup idempotency ledger."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.provisioned_resource import ProvisionedResource, ResourceType


class ProvisionedResourceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(
        self, *, guild_id: int, resource_type: ResourceType, logical_key: str
    ) -> ProvisionedResource | None:
        stmt = select(ProvisionedResource).where(
            ProvisionedResource.guild_id == guild_id,
            ProvisionedResource.resource_type == resource_type,
            ProvisionedResource.logical_key == logical_key,
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_for_guild(self, guild_id: int) -> list[ProvisionedResource]:
        stmt = select(ProvisionedResource).where(ProvisionedResource.guild_id == guild_id)
        return list((await self._session.execute(stmt)).scalars().all())

    async def upsert(
        self,
        *,
        guild_id: int,
        resource_type: ResourceType,
        logical_key: str,
        discord_id: int,
    ) -> ProvisionedResource:
        existing = await self.get(
            guild_id=guild_id, resource_type=resource_type, logical_key=logical_key
        )
        now = datetime.now(UTC)
        if existing is not None:
            existing.discord_id = discord_id
            existing.last_verified_at = now
            return existing

        resource = ProvisionedResource(
            guild_id=guild_id,
            resource_type=resource_type,
            logical_key=logical_key,
            discord_id=discord_id,
            last_verified_at=now,
        )
        self._session.add(resource)
        await self._session.flush()
        return resource
