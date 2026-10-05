"""SetupService against the BRAWLISTAN contract (docs/DECISIONS.md ADR-109).

- /setup never touches permissions: no overwrites on create, no overwrite
  reconciliation on later runs, roles created with none, and role repair
  only renames.
- /setup restructure deletes only ledger-tracked resources outside the
  spec, and never anything the owner made by hand.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import discord
from sqlalchemy.ext.asyncio import AsyncSession

from bot.constants import ROLE_FOUNDER, ROLE_PLAYER, CategorySpec, ChannelSpec
from database.models.provisioned_resource import ResourceType
from database.repositories.provisioned_resource_repository import ProvisionedResourceRepository
from services.setup_planner import ActionType, CategoryAction, ChannelAction, RoleAction
from services.setup_service import SetupReport, SetupService

GUILD_ID = 1


def _service(guild: Mock | None = None, session: AsyncSession | None = None) -> SetupService:
    guild = guild or Mock()
    guild.id = GUILD_ID
    service = SetupService(guild, session=session)  # type: ignore[arg-type]
    return service


# --- no permissions, ever ----------------------------------------------------


async def test_existing_category_is_not_re_permissioned() -> None:
    service = _service()
    service._remember = AsyncMock()  # type: ignore[method-assign]
    category = Mock(spec=discord.CategoryChannel)
    category.id = 1
    category.edit = AsyncMock()
    service._guild.get_channel = Mock(return_value=category)

    spec = CategorySpec(logical_key="category:test", name="TEST", channels=())
    await service._apply_categories(
        (CategoryAction(type=ActionType.VERIFY, spec=spec, existing_id=1),),
        SetupReport(mode="launch"),
    )

    category.edit.assert_not_awaited()


async def test_existing_channel_is_not_re_permissioned() -> None:
    service = _service()
    service._remember = AsyncMock()  # type: ignore[method-assign]
    channel = Mock(spec=discord.TextChannel)
    channel.id = 2
    channel.edit = AsyncMock()
    service._guild.get_channel = Mock(return_value=channel)

    spec = ChannelSpec(logical_key="channel:test", name="test", kind="text")
    action = ChannelAction(
        type=ActionType.VERIFY, spec=spec, category_logical_key="category:test", existing_id=2
    )
    await service._apply_channels((action,), {}, SetupReport(mode="launch"))

    channel.edit.assert_not_awaited()


async def test_repaired_channel_edit_carries_no_overwrites() -> None:
    service = _service()
    service._remember = AsyncMock()  # type: ignore[method-assign]
    channel = Mock(spec=discord.TextChannel)
    channel.id = 2
    channel.edit = AsyncMock()
    service._guild.get_channel = Mock(return_value=channel)

    spec = ChannelSpec(logical_key="channel:test", name="rankings", kind="text", topic="t")
    action = ChannelAction(
        type=ActionType.REPAIR,
        spec=spec,
        category_logical_key="category:test",
        existing_id=2,
        diffs=("name: 'leaderboard' -> 'rankings'",),
    )
    await service._apply_channels((action,), {}, SetupReport(mode="launch"))

    channel.edit.assert_awaited_once()
    assert "overwrites" not in channel.edit.await_args.kwargs


async def test_new_channel_and_category_are_created_without_overwrites() -> None:
    guild = Mock()
    category = Mock(spec=discord.CategoryChannel)
    category.id = 10
    guild.create_category = AsyncMock(return_value=category)
    channel = Mock(spec=discord.TextChannel)
    channel.id = 11
    guild.create_text_channel = AsyncMock(return_value=channel)
    service = _service(guild)
    service._remember = AsyncMock()  # type: ignore[method-assign]

    cat_spec = CategorySpec(logical_key="category:test", name="TEST", channels=())
    by_key = await service._apply_categories(
        (CategoryAction(type=ActionType.CREATE, spec=cat_spec),), SetupReport(mode="launch")
    )
    chan_spec = ChannelSpec(logical_key="channel:test", name="test", kind="text")
    await service._apply_channels(
        (
            ChannelAction(
                type=ActionType.CREATE, spec=chan_spec, category_logical_key="category:test"
            ),
        ),
        by_key,
        SetupReport(mode="launch"),
    )

    assert "overwrites" not in guild.create_category.await_args.kwargs
    assert "overwrites" not in guild.create_text_channel.await_args.kwargs


async def test_new_role_is_created_with_no_permissions() -> None:
    guild = Mock()
    role = Mock(spec=discord.Role)
    role.id = 5
    guild.create_role = AsyncMock(return_value=role)
    service = _service(guild)
    service._remember = AsyncMock()  # type: ignore[method-assign]

    await service._apply_roles(
        (RoleAction(type=ActionType.CREATE, spec=ROLE_PLAYER),), SetupReport(mode=None)
    )

    assert guild.create_role.await_args.kwargs["permissions"].value == 0


async def test_role_repair_only_renames() -> None:
    """The old Leader role becomes Founder, keeping whatever permissions,
    colour and members the owner gave it."""
    guild = Mock()
    role = Mock(spec=discord.Role)
    role.id = 5
    role.edit = AsyncMock()
    guild.get_role = Mock(return_value=role)
    service = _service(guild)
    service._remember = AsyncMock()  # type: ignore[method-assign]

    action = RoleAction(
        type=ActionType.REPAIR,
        spec=ROLE_FOUNDER,
        existing_id=5,
        diffs=("name: 'Leader' -> 'Founder'",),
    )
    report = SetupReport(mode=None)
    await service._apply_roles((action,), report)

    role.edit.assert_awaited_once()
    assert set(role.edit.await_args.kwargs) == {"name", "reason"}
    assert role.edit.await_args.kwargs["name"] == "Founder"
    assert report.roles.repaired == ["Founder"]


# --- /setup restructure ------------------------------------------------------


def _live(obj_id: int, name: str) -> Mock:
    obj = Mock()
    obj.id = obj_id
    obj.name = name
    obj.delete = AsyncMock()
    return obj


async def _seed(session: AsyncSession, rows: list[tuple[ResourceType, str, int]]) -> None:
    repo = ProvisionedResourceRepository(session)
    for resource_type, key, discord_id in rows:
        await repo.upsert(
            guild_id=GUILD_ID, resource_type=resource_type, logical_key=key, discord_id=discord_id
        )


async def test_restructure_deletes_only_ledger_resources_outside_the_spec(
    session: AsyncSession,
) -> None:
    await _seed(
        session,
        [
            (ResourceType.ROLE, "role:shaheen_leader", 100),  # Founder: kept
            (ResourceType.ROLE, "role:guest", 101),  # retired
            (ResourceType.CHANNEL, "channel:leaderboard", 200),  # #rankings: kept
            (ResourceType.CHANNEL, "channel:mod_log", 201),  # retired
            (ResourceType.CATEGORY, "category:development", 300),  # retired
        ],
    )
    live = {
        100: _live(100, "Founder"),
        101: _live(101, "Guest"),
        200: _live(200, "rankings"),
        201: _live(201, "mod-log"),
        300: _live(300, "DEVELOPMENT"),
        # A channel the owner made by hand, never in the ledger.
        999: _live(999, "owner-made"),
    }
    guild = Mock()
    guild.get_role = Mock(side_effect=live.get)
    guild.get_channel = Mock(side_effect=live.get)
    service = _service(guild, session)

    retired = await service.retired_resources()
    assert [(r.logical_key, r.name) for r in retired] == [
        ("channel:mod_log", "mod-log"),
        ("category:development", "DEVELOPMENT"),
        ("role:guest", "Guest"),
    ]

    report = await service.restructure()

    assert (report.channels_deleted, report.categories_deleted, report.roles_deleted) == (1, 1, 1)
    for kept in (100, 200, 999):
        live[kept].delete.assert_not_awaited()
    for gone in (101, 201, 300):
        live[gone].delete.assert_awaited_once()
    remaining = {
        r.logical_key for r in await ProvisionedResourceRepository(session).list_for_guild(GUILD_ID)
    }
    assert remaining == {"role:shaheen_leader", "channel:leaderboard"}


async def test_restructure_keeps_a_row_it_could_not_delete_and_forgets_vanished_ones(
    session: AsyncSession,
) -> None:
    await _seed(
        session,
        [
            (ResourceType.ROLE, "role:guest", 101),
            (ResourceType.ROLE, "role:mvp", 102),  # already deleted by hand
        ],
    )
    guest = _live(101, "Guest")
    guest.delete = AsyncMock(side_effect=discord.Forbidden(Mock(status=403), "no"))
    guild = Mock()
    guild.get_role = Mock(side_effect={101: guest}.get)
    service = _service(guild, session)

    report = await service.restructure()

    assert report.roles_deleted == 0
    assert len(report.errors) == 1
    remaining = {
        r.logical_key for r in await ProvisionedResourceRepository(session).list_for_guild(GUILD_ID)
    }
    assert remaining == {"role:guest"}  # retried next run; role:mvp forgotten


def test_restructure_preview_lists_only_live_resources_and_warns() -> None:
    from bot.content.embeds import build_restructure_preview_embed
    from services.setup_service import RetiredResource

    embed = build_restructure_preview_embed(
        [
            RetiredResource(ResourceType.CHANNEL, "channel:mod_log", 1, "mod-log"),
            RetiredResource(ResourceType.ROLE, "role:mvp", 2, None),
        ]
    )
    deleted = embed.fields[0].value
    assert "mod-log" in deleted
    assert "mvp" not in deleted
    assert "1 already deleted" in (embed.footer.text or "")


def test_restructure_preview_with_nothing_to_remove() -> None:
    from bot.content.embeds import build_restructure_preview_embed

    embed = build_restructure_preview_embed([])
    assert "Nothing to remove" in (embed.description or "")
