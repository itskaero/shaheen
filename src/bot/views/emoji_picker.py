"""Interactive picker for the emoji candidate pool (docs/DECISIONS.md
ADR-092).

Browsing ~260 candidate crops (src/assets/emoji_candidates/) one at a time
would be tedious without a UI: EmojiBrowseView opens on a legend select,
then an icon browser (◀ Prev / ▶ Next / ➕ Add / 🔁 Legends / ✅ Done) once
a legend is picked, showing the current candidate as the embed's image.
Session-lived (bounded timeout, no custom_id routing) — unlike bot/views/
application.py's PersistentView pieces, this exists only for the duration
of one staff member's browsing session and is never re-registered across
restarts.
"""

from __future__ import annotations

from pathlib import Path

import discord

from bot.content.emoji_embeds import (
    build_emoji_browse_intro_embed,
    build_emoji_candidate_preview_embed,
    build_emoji_sync_embed,
)
from services.emoji_service import EmojiService, candidate_files, candidate_legends

_TIMEOUT_SECONDS = 300  # 5 minutes idle
_NO_CANDIDATES_VALUE = "__none__"


def _sanitize_emoji_name(raw: str, *, fallback: str) -> str:
    """Discord emoji names: 2-32 characters, alphanumeric and underscores."""
    cleaned = "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in raw.strip())
    cleaned = cleaned.strip("_")
    if len(cleaned) < 2:
        cleaned = fallback
    return cleaned[:32]


class EmojiBrowseView(discord.ui.View):
    """Owns all the UI-building; every handler ends by editing the one
    message this view is attached to, swapping between "pick a legend" and
    "browse its candidates" layouts on the same message rather than
    posting a new one each step.
    """

    def __init__(self, *, author_id: int) -> None:
        super().__init__(timeout=_TIMEOUT_SECONDS)
        self.author_id = author_id
        self.legend: str | None = None
        self.files: tuple[Path, ...] = ()
        self.index = 0
        self.queue: list[tuple[str, Path]] = []
        self._legend_select: discord.ui.Select[EmojiBrowseView] | None = None
        self._build_legend_picker_items()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "Only the person who ran this command can use this picker.", ephemeral=True
            )
            return False
        return True

    async def on_timeout(self) -> None:
        for child in self.children:
            if isinstance(child, discord.ui.Select | discord.ui.Button):
                child.disabled = True

    def current_embed(self) -> discord.Embed:
        if self.legend is None:
            return build_emoji_browse_intro_embed()
        return build_emoji_candidate_preview_embed(
            legend=self.legend, index=self.index, total=len(self.files), queue_count=len(self.queue)
        )

    def current_file(self) -> discord.File | None:
        if self.legend is None or not self.files:
            return None
        return discord.File(self.files[self.index], filename="preview.png")

    # --- legend-picker layout -------------------------------------------------

    def _build_legend_picker_items(self) -> None:
        self.clear_items()
        self.legend = None
        self.files = ()
        self.index = 0
        legends = candidate_legends()
        options = [
            discord.SelectOption(label=legend.replace("_", " ").title(), value=legend)
            for legend in legends[:25]
        ] or [discord.SelectOption(label="No candidates packaged", value=_NO_CANDIDATES_VALUE)]
        select: discord.ui.Select[EmojiBrowseView] = discord.ui.Select(
            placeholder="Choose a legend to browse", options=options
        )
        select.callback = self._on_legend_selected  # type: ignore[method-assign]
        self._legend_select = select
        self.add_item(select)
        if self.queue:
            finish: discord.ui.Button[EmojiBrowseView] = discord.ui.Button(
                label=f"Done ({len(self.queue)})",
                emoji="✅",
                style=discord.ButtonStyle.primary,
                row=1,
            )
            finish.callback = self._on_done  # type: ignore[method-assign]
            self.add_item(finish)

    async def _on_legend_selected(self, interaction: discord.Interaction) -> None:
        assert self._legend_select is not None
        legend = self._legend_select.values[0]
        if legend == _NO_CANDIDATES_VALUE:
            await interaction.response.defer()
            return
        self.legend = legend
        self.files = candidate_files(legend)
        self.index = 0
        if not self.files:
            await interaction.response.send_message(
                f"No candidates found for {legend!r} — its folder may have been removed.",
                ephemeral=True,
            )
            self._build_legend_picker_items()
            return
        await self._render(interaction)

    # --- icon-browser layout ---------------------------------------------------

    def _build_browser_items(self) -> None:
        self.clear_items()
        add_button: discord.ui.Button[EmojiBrowseView] = discord.ui.Button(
            label="Add", emoji="➕", style=discord.ButtonStyle.success
        )
        done_button: discord.ui.Button[EmojiBrowseView] = discord.ui.Button(
            label=f"Done ({len(self.queue)})", emoji="✅", style=discord.ButtonStyle.primary
        )
        prev_button: discord.ui.Button[EmojiBrowseView] = discord.ui.Button(
            emoji="◀️", style=discord.ButtonStyle.secondary
        )
        next_button: discord.ui.Button[EmojiBrowseView] = discord.ui.Button(
            emoji="▶️", style=discord.ButtonStyle.secondary
        )
        legends_button: discord.ui.Button[EmojiBrowseView] = discord.ui.Button(
            label="Legends", emoji="🔁"
        )
        buttons = (
            (prev_button, self._on_prev),
            (next_button, self._on_next),
            (add_button, self._on_add),
            (legends_button, self._on_change_legend),
            (done_button, self._on_done),
        )
        for button, handler in buttons:
            button.callback = handler  # type: ignore[method-assign]
            self.add_item(button)

    async def _render(self, interaction: discord.Interaction) -> None:
        """The one place that actually edits the message — every handler
        updates self's state, then calls this to reflect it.
        """
        if self.legend is not None:
            self._build_browser_items()
        else:
            self._build_legend_picker_items()
        file = self.current_file()
        await interaction.response.edit_message(
            embed=self.current_embed(), attachments=[file] if file else [], view=self
        )

    async def _on_prev(self, interaction: discord.Interaction) -> None:
        self.index = (self.index - 1) % len(self.files)
        await self._render(interaction)

    async def _on_next(self, interaction: discord.Interaction) -> None:
        self.index = (self.index + 1) % len(self.files)
        await self._render(interaction)

    async def _on_add(self, interaction: discord.Interaction) -> None:
        assert self.legend is not None
        path = self.files[self.index]
        proposed = f"{self.legend}_{path.stem.removeprefix('expr_')}"
        await interaction.response.send_modal(
            _NameEmojiModal(view=self, path=path, proposed=proposed)
        )

    async def _on_change_legend(self, interaction: discord.Interaction) -> None:
        self.legend = None
        await self._render(interaction)

    async def _on_done(self, interaction: discord.Interaction) -> None:
        if not self.queue:
            await interaction.response.send_message(
                "Nothing queued yet — add a candidate first.", ephemeral=True
            )
            return
        if interaction.guild is None:
            await interaction.response.send_message(
                "This can only be used inside the Shaheen server.", ephemeral=True
            )
            return
        await interaction.response.defer()
        report = await EmojiService(interaction.guild).sync(files=self.queue)
        self.queue.clear()
        self.clear_items()
        self.stop()
        await interaction.edit_original_response(
            embed=build_emoji_sync_embed(report), attachments=[], view=self
        )


class _NameEmojiModal(discord.ui.Modal, title="Name this emoji"):
    def __init__(self, *, view: EmojiBrowseView, path: Path, proposed: str) -> None:
        super().__init__()
        self._view = view
        self._path = path
        self.name_input: discord.ui.TextInput[_NameEmojiModal] = discord.ui.TextInput(
            label="Emoji name",
            default=_sanitize_emoji_name(proposed, fallback=path.stem),
            max_length=32,
            min_length=2,
        )
        self.add_item(self.name_input)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        name = _sanitize_emoji_name(self.name_input.value, fallback=self._path.stem)
        self._view.queue.append((name, self._path))
        self._view._build_browser_items()
        file = self._view.current_file()
        await interaction.response.edit_message(
            embed=self._view.current_embed(), attachments=[file] if file else [], view=self._view
        )
