"""Uploading Shaheen's legend-expression emoji.

docs/DECISIONS.md ADR-090/ADR-092. Two sources:

- src/assets/emoji/*.png — the curated 24-emoji pack, one distinct
  expression per legend, deliberately picked so no two emoji repeat the
  same reaction (a "GG" from two different legends would just be a wasted
  slot). `/emoji sync` uploads whichever ones the guild doesn't already
  have by name; safe to re-run any time.
- src/assets/emoji_candidates/<legend>/*.png — every cell from the
  original sprite sheets, ~260 across 16 legends, unfiltered and
  unnamed. This is raw material for `/emoji browse` (bot/views/
  emoji_picker.py) to pick from and name interactively — nothing here
  uploads automatically.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

import discord

_EMOJI_DIR = Path(__file__).resolve().parents[1] / "assets" / "emoji"
_CANDIDATES_DIR = Path(__file__).resolve().parents[1] / "assets" / "emoji_candidates"


def available_emoji_files() -> tuple[Path, ...]:
    """Every packaged emoji source file, sorted for a stable upload order."""
    if not _EMOJI_DIR.is_dir():
        return ()
    return tuple(sorted(_EMOJI_DIR.glob("*.png")))


def candidate_legends() -> tuple[str, ...]:
    """Every legend with a candidate folder, sorted — the `/emoji browse`
    picker's legend list.
    """
    if not _CANDIDATES_DIR.is_dir():
        return ()
    return tuple(sorted(p.name for p in _CANDIDATES_DIR.iterdir() if p.is_dir()))


def candidate_files(legend: str) -> tuple[Path, ...]:
    """Every candidate crop for one legend, sorted. Empty for an unknown
    legend rather than raising — a stale/renamed folder shouldn't crash the
    picker mid-browse.
    """
    legend_dir = _CANDIDATES_DIR / legend
    if not legend_dir.is_dir():
        return ()
    return tuple(sorted(legend_dir.glob("*.png")))


@dataclass
class EmojiSyncReport:
    created: list[str] = field(default_factory=list)
    skipped_existing: list[str] = field(default_factory=list)
    skipped_no_room: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.created) + len(self.skipped_existing) + len(self.skipped_no_room)


@dataclass
class EmojiClearReport:
    deleted: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.deleted) + len(self.errors)


class EmojiService:
    """Uploads the packaged pack to a guild.

    Never deletes or replaces an existing emoji — a name collision is
    skipped rather than overwritten, so a staff member who hand-picked a
    different image for that name doesn't get it silently clobbered by a
    later sync.
    """

    def __init__(self, guild: discord.Guild) -> None:
        self._guild = guild

    async def sync(self, files: Sequence[tuple[str, Path]] | None = None) -> EmojiSyncReport:
        """Uploads `files` (name, image_path) pairs, or the curated pack by
        default. The picker (`/emoji browse`) is the only caller that ever
        passes `files` explicitly — a staff-chosen name for a staff-chosen
        candidate crop.
        """
        report = EmojiSyncReport()
        pairs = (
            files if files is not None else [(path.stem, path) for path in available_emoji_files()]
        )
        if not pairs:
            return report

        existing_names = {emoji.name for emoji in self._guild.emojis}
        # Discord counts animated and static emoji separately against the
        # guild's limit (50/100/150/250 by boost tier); the pack is all
        # static PNGs, so only that half of the count matters here.
        static_count = sum(1 for emoji in self._guild.emojis if not emoji.animated)
        limit = self._guild.emoji_limit

        for name, path in pairs:
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

    async def clear(self) -> EmojiClearReport:
        """Deletes every custom emoji in the guild, regardless of origin —
        not just the Shaheen pack. `/emoji clear` (docs/DECISIONS.md
        ADR-094) is the only caller; unlike `sync`, this is explicitly the
        exception to this class's own "never deletes or replaces" rule
        above, gated behind a much stronger confirmation than sync/browse.
        A failure on one emoji (missing permission, already gone, a rate
        limit) is recorded and skipped rather than aborting the batch —
        same resilience posture as `sync`.
        """
        report = EmojiClearReport()
        for emoji in list(self._guild.emojis):
            try:
                await emoji.delete(reason="Shaheen /emoji clear")
            except discord.Forbidden:
                report.errors.append(f"Missing permission to delete emoji {emoji.name!r}.")
                continue
            except discord.HTTPException as exc:
                report.errors.append(f"Discord error for emoji {emoji.name!r}: {exc}")
                continue
            report.deleted.append(emoji.name)

        return report
