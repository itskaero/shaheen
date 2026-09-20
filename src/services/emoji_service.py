"""Uploading Shaheen's curated legend-expression emoji pack.

docs/DECISIONS.md ADR-090. The pack lives at src/assets/emoji/*.png — 128x128
crops taken from the clan's Brawlhalla legend art, one distinct expression
per legend, deliberately picked so no two emoji repeat the same reaction
(a "GG" from two different legends would just be a wasted slot). `/emoji
sync` uploads whichever ones the guild doesn't already have by name; it's
safe to run again — after adding files to the folder, or on a guild whose
emoji were wiped — since anything already present by name is left alone.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import discord

_EMOJI_DIR = Path(__file__).resolve().parents[1] / "assets" / "emoji"


def available_emoji_files() -> tuple[Path, ...]:
    """Every packaged emoji source file, sorted for a stable upload order."""
    if not _EMOJI_DIR.is_dir():
        return ()
    return tuple(sorted(_EMOJI_DIR.glob("*.png")))


@dataclass
class EmojiSyncReport:
    created: list[str] = field(default_factory=list)
    skipped_existing: list[str] = field(default_factory=list)
    skipped_no_room: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.created) + len(self.skipped_existing) + len(self.skipped_no_room)


class EmojiService:
    """Uploads the packaged pack to a guild.

    Never deletes or replaces an existing emoji — a name collision is
    skipped rather than overwritten, so a staff member who hand-picked a
    different image for that name doesn't get it silently clobbered by a
    later sync.
    """

    def __init__(self, guild: discord.Guild) -> None:
        self._guild = guild

    async def sync(self) -> EmojiSyncReport:
        report = EmojiSyncReport()
        files = available_emoji_files()
        if not files:
            return report

        existing_names = {emoji.name for emoji in self._guild.emojis}
        # Discord counts animated and static emoji separately against the
        # guild's limit (50/100/150/250 by boost tier); the pack is all
        # static PNGs, so only that half of the count matters here.
        static_count = sum(1 for emoji in self._guild.emojis if not emoji.animated)
        limit = self._guild.emoji_limit

        for path in files:
            name = path.stem
            if name in existing_names:
                report.skipped_existing.append(name)
                continue
            if static_count >= limit:
                report.skipped_no_room.append(name)
                continue
            try:
                image_bytes = path.read_bytes()
                await self._guild.create_custom_emoji(
                    name=name, image=image_bytes, reason="Shaheen /emoji sync"
                )
            except discord.Forbidden:
                report.errors.append(f"Missing permission to create emoji {name!r}.")
                continue
            except discord.HTTPException as exc:
                report.errors.append(f"Discord error for emoji {name!r}: {exc}")
                continue
            report.created.append(name)
            static_count += 1

        return report
