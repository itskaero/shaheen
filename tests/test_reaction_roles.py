"""Reaction roles (docs/DECISIONS.md ADR-137): emoji and link parsing, the
bindings, the role safety check and the panel."""

from __future__ import annotations

from dataclasses import dataclass, field

import discord
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from bot.cogs.reaction_roles import (
    PANEL_FOOTER,
    _panel_intro,
    build_list_embed,
    build_panel_embed,
    role_problem,
)
from core.exceptions import ShaheenError
from services.reaction_role_service import (
    MAX_PER_MESSAGE,
    MessageRef,
    ReactionRoleService,
    emoji_key,
    normalize_emoji,
    parse_message_link,
)

GUILD = 111111111111111111
CHANNEL = 222222222222222222
MESSAGE = 333333333333333333
REF = MessageRef(GUILD, CHANNEL, MESSAGE)


def test_normalize_emoji() -> None:
    assert normalize_emoji(" 🇵🇰 ") == "🇵🇰"
    assert normalize_emoji("❤️") == "❤"  # variation selector dropped
    assert normalize_emoji("1️⃣") == "1⃣"
    assert normalize_emoji("<:shaheen:123456789012345678>") == "<:shaheen:123456789012345678>"
    assert normalize_emoji("<a:fire:123456789012345678>") == "<a:fire:123456789012345678>"
    for bad in ("", "abc", ":smile:", "🔥 🔥", "<:x:12>", "@everyone"):
        assert normalize_emoji(bad) is None, bad


def test_custom_emoji_matched_by_id() -> None:
    assert emoji_key("<:old:123456789012345678>") == emoji_key("<:renamed:123456789012345678>")
    assert emoji_key("❤️") == emoji_key("❤")


def test_parse_message_link() -> None:
    link = f"https://discord.com/channels/{GUILD}/{CHANNEL}/{MESSAGE}"
    assert parse_message_link(link) == REF
    assert parse_message_link(link.replace("discord.com", "ptb.discord.com")) == REF
    assert parse_message_link(link.replace("discord.com", "discordapp.com")) == REF
    assert parse_message_link(str(MESSAGE)) is None
    assert parse_message_link("https://evil.example/channels/1/2/3") is None


async def test_add_remove_and_lookup(session: AsyncSession) -> None:
    service = ReactionRoleService(session)
    await service.add(message=REF, emoji="🇵🇰", role_id=10, actor_discord_id=1)
    await service.add(
        message=REF, emoji="<:shaheen:123456789012345678>", role_id=11, actor_discord_id=1
    )
    assert await service.role_for(GUILD, MESSAGE, "🇵🇰") == 10
    # A renamed custom emoji still matches; another guild never does.
    assert await service.role_for(GUILD, MESSAGE, "<:shn:123456789012345678>") == 11
    assert await service.role_for(999, MESSAGE, "🇵🇰") is None
    assert await service.message_ids() == {MESSAGE}

    with pytest.raises(ShaheenError):
        await service.add(message=REF, emoji="🇵🇰", role_id=12, actor_discord_id=1)
    with pytest.raises(ShaheenError):
        await service.add(message=REF, emoji="🔥", role_id=10, actor_discord_id=1)

    removed = await service.remove(
        guild_id=GUILD, message_id=MESSAGE, emoji="🇵🇰", actor_discord_id=1
    )
    assert removed.role_id == 10
    assert await service.role_for(GUILD, MESSAGE, "🇵🇰") is None
    with pytest.raises(ShaheenError):
        await service.remove(guild_id=GUILD, message_id=MESSAGE, emoji="🇵🇰", actor_discord_id=1)

    assert await service.forget_message(MESSAGE) == 1
    assert await service.message_ids() == set()


async def test_twenty_reactions_per_message(session: AsyncSession) -> None:
    service = ReactionRoleService(session)
    emojis = [chr(0x1F600 + i) for i in range(MAX_PER_MESSAGE + 1)]
    for i, emoji in enumerate(emojis[:MAX_PER_MESSAGE]):
        await service.add(message=REF, emoji=emoji, role_id=100 + i, actor_discord_id=1)
    with pytest.raises(ShaheenError):
        await service.add(message=REF, emoji=emojis[-1], role_id=999, actor_discord_id=1)


@dataclass
class _Role:
    name: str
    position: int
    permissions: discord.Permissions = field(default_factory=discord.Permissions.none)
    managed: bool = False
    default: bool = False

    def is_default(self) -> bool:
        return self.default

    def __ge__(self, other: _Role) -> bool:
        return self.position >= other.position


@dataclass
class _Member:
    top_role: _Role


def test_role_problem() -> None:
    bot = _Member(top_role=_Role("BRAWLISTAN", 10))
    assert role_problem(_Role("EU", 3), bot_member=bot) is None  # type: ignore[arg-type]
    for role in (
        _Role("@everyone", 0, default=True),
        _Role("Nitro Booster", 4, managed=True),
        _Role("Mods", 5, permissions=discord.Permissions(kick_members=True)),
        _Role("Admin", 6, permissions=discord.Permissions(administrator=True)),
        _Role("Above", 10),
    ):
        assert role_problem(role, bot_member=bot) is not None, role.name  # type: ignore[arg-type]


def test_panel_embed_and_intro_round_trip() -> None:
    empty = build_panel_embed("Pick your region", "Tap a flag.", [])
    assert empty.footer.text == PANEL_FOOTER
    assert _panel_intro(empty.description or "") == "Tap a flag."
    full = build_panel_embed("Pick your region", "Tap a flag.", [("🇵🇰", 10), ("🌏", 11)])
    assert (full.description or "").endswith("🇵🇰  <@&10>\n🌏  <@&11>")
    assert _panel_intro(full.description or "") == "Tap a flag."
    assert _panel_intro(build_panel_embed("T", None, [("🔥", 1)]).description or "") is None


async def test_list_embed(session: AsyncSession) -> None:
    service = ReactionRoleService(session)
    assert "None yet" in (build_list_embed(GUILD, []).description or "")
    await service.add(message=REF, emoji="🔥", role_id=5, actor_discord_id=1)
    text = build_list_embed(GUILD, await service.for_guild(GUILD)).description or ""
    assert f"/{GUILD}/{CHANNEL}/{MESSAGE}" in text and "🔥 <@&5>" in text
