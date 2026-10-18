"""Reaction roles (docs/DECISIONS.md ADR-137): react to a message, get a role;
remove the reaction, lose it.

Staff bind an emoji on a message to a role. The rules (one role per emoji per
message, Discord's 20-reaction limit, emoji and message-link parsing) live
here; whether a role is safe to hand out is checked on the Discord side
(bot/cogs/reaction_roles.py) because it needs the live role. Discord-free.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import ShaheenError
from database.models.reaction_role import ReactionRole
from database.repositories.audit_log_repository import AuditLogRepository
from database.repositories.reaction_role_repository import ReactionRoleRepository

# Discord allows 20 different reactions on one message.
MAX_PER_MESSAGE = 20
_CUSTOM = re.compile(r"^<(a?):([A-Za-z0-9_]{2,32}):(\d{15,25})>$")
_LINK = re.compile(
    r"^https://(?:(?:ptb|canary)\.)?discord(?:app)?\.com/channels/(\d{15,25})/(\d{15,25})/(\d{15,25})/?$"
)
_VARIATION_SELECTOR = "️"


@dataclass(frozen=True)
class MessageRef:
    guild_id: int
    channel_id: int
    message_id: int


def normalize_emoji(text: str) -> str | None:
    """`<:name:id>` / `<a:name:id>` for a custom emoji, or the Unicode emoji
    without its variation selector (Discord sends reactions both with and
    without it). None for anything that isn't an emoji."""
    text = text.strip()
    if match := _CUSTOM.match(text):
        animated, name, emoji_id = match.groups()
        return f"<{animated}:{name}:{emoji_id}>"
    text = text.replace(_VARIATION_SELECTOR, "")
    if not text or len(text) > 16 or any(c.isspace() for c in text):
        return None
    if all(ord(c) < 128 for c in text):  # letters, digits, ":name:" shortcodes
        return None
    return text


def emoji_key(emoji: str) -> str:
    """What two emoji are compared by: a custom emoji's ID (it survives a
    rename), else the normalised Unicode."""
    if match := _CUSTOM.match(emoji):
        return match.group(3)
    return emoji.replace(_VARIATION_SELECTOR, "")


def parse_message_link(text: str) -> MessageRef | None:
    """A message link (right-click → Copy Message Link)."""
    match = _LINK.match(text.strip())
    if match is None:
        return None
    guild_id, channel_id, message_id = (int(part) for part in match.groups())
    return MessageRef(guild_id, channel_id, message_id)


class ReactionRoleService:
    def __init__(self, session: AsyncSession) -> None:
        self._bindings = ReactionRoleRepository(session)
        self._audit = AuditLogRepository(session)

    async def add(
        self, *, message: MessageRef, emoji: str, role_id: int, actor_discord_id: int
    ) -> ReactionRole:
        existing = await self._bindings.for_message(message.message_id)
        if any(emoji_key(b.emoji) == emoji_key(emoji) for b in existing):
            raise ShaheenError(f"{emoji} already gives a role on that message. Remove it first.")
        if any(b.role_id == role_id for b in existing):
            raise ShaheenError("That role already has an emoji on that message.")
        if len(existing) >= MAX_PER_MESSAGE:
            raise ShaheenError(f"A message can hold at most {MAX_PER_MESSAGE} reactions.")
        binding = await self._bindings.add(
            ReactionRole(
                guild_id=message.guild_id,
                channel_id=message.channel_id,
                message_id=message.message_id,
                emoji=emoji,
                role_id=role_id,
            )
        )
        await self._audit.add(
            guild_id=message.guild_id,
            action="reaction_role.add",
            source="discord",
            subject=f"{emoji} -> role {role_id}",
            actor_discord_id=actor_discord_id,
            detail={"message_id": message.message_id, "role_id": role_id, "emoji": emoji},
        )
        return binding

    async def remove(
        self, *, guild_id: int, message_id: int, emoji: str, actor_discord_id: int
    ) -> ReactionRole:
        binding = await self._find(guild_id, message_id, emoji)
        if binding is None:
            raise ShaheenError(f"{emoji} doesn't give a role on that message.")
        await self._bindings.delete(binding)
        await self._audit.add(
            guild_id=guild_id,
            action="reaction_role.remove",
            source="discord",
            subject=f"{emoji} -> role {binding.role_id}",
            actor_discord_id=actor_discord_id,
            detail={"message_id": message_id, "role_id": binding.role_id, "emoji": emoji},
        )
        return binding

    async def role_for(self, guild_id: int, message_id: int, emoji: str) -> int | None:
        binding = await self._find(guild_id, message_id, emoji)
        return binding.role_id if binding else None

    async def for_message(self, message_id: int) -> list[ReactionRole]:
        return await self._bindings.for_message(message_id)

    async def for_guild(self, guild_id: int) -> list[ReactionRole]:
        return await self._bindings.for_guild(guild_id)

    async def message_ids(self) -> set[int]:
        return await self._bindings.message_ids()

    async def forget_message(self, message_id: int) -> int:
        """Drop every binding on a deleted message."""
        return await self._bindings.delete_message(message_id)

    async def _find(self, guild_id: int, message_id: int, emoji: str) -> ReactionRole | None:
        key = emoji_key(emoji)
        return next(
            (
                b
                for b in await self._bindings.for_message(message_id)
                if b.guild_id == guild_id and emoji_key(b.emoji) == key
            ),
            None,
        )
