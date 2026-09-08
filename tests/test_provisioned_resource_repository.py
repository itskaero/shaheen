from sqlalchemy.ext.asyncio import AsyncSession

from database.models.provisioned_resource import ResourceType
from database.repositories.provisioned_resource_repository import ProvisionedResourceRepository


async def test_upsert_creates_then_updates(session: AsyncSession) -> None:
    repo = ProvisionedResourceRepository(session)

    created = await repo.upsert(
        guild_id=1, resource_type=ResourceType.ROLE, logical_key="role:leader", discord_id=100
    )
    assert created.discord_id == 100

    updated = await repo.upsert(
        guild_id=1, resource_type=ResourceType.ROLE, logical_key="role:leader", discord_id=200
    )
    assert updated.id == created.id
    assert updated.discord_id == 200

    fetched = await repo.get(guild_id=1, resource_type=ResourceType.ROLE, logical_key="role:leader")
    assert fetched is not None
    assert fetched.discord_id == 200


async def test_get_returns_none_when_missing(session: AsyncSession) -> None:
    repo = ProvisionedResourceRepository(session)
    result = await repo.get(
        guild_id=1, resource_type=ResourceType.CHANNEL, logical_key="channel:nope"
    )
    assert result is None


async def test_list_for_guild_scopes_by_guild(session: AsyncSession) -> None:
    repo = ProvisionedResourceRepository(session)
    await repo.upsert(
        guild_id=1, resource_type=ResourceType.ROLE, logical_key="role:a", discord_id=1
    )
    await repo.upsert(
        guild_id=2, resource_type=ResourceType.ROLE, logical_key="role:a", discord_id=2
    )

    guild_1_resources = await repo.list_for_guild(1)
    assert len(guild_1_resources) == 1
    assert guild_1_resources[0].discord_id == 1
