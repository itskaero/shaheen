"""Paginated /help (docs/DECISIONS.md ADR-121): previous and next buttons, a
page counter and a category menu over the pages from help_pages().

Session-lived like the other non-persistent views (ADR-038): it answers only
the member who ran /help and switches its controls off when it times out.
"""

from __future__ import annotations

import contextlib

import discord

from bot.content.help_embeds import HelpSection, build_help_page

TIMEOUT_SECONDS = 300


class _CategoryMenu(discord.ui.Select["HelpPaginator"]):
    def __init__(self, pages: list[HelpSection | None]) -> None:
        options = [
            discord.SelectOption(label="Overview", value="0", emoji="📖"),
            *(
                discord.SelectOption(label=page.title[:100], value=str(i))
                for i, page in enumerate(pages)
                if page is not None
            ),
        ]
        super().__init__(placeholder="Jump to a category", options=options[:25], row=1)

    async def callback(self, interaction: discord.Interaction) -> None:
        assert self.view is not None
        await self.view.show(interaction, int(self.values[0]))


class HelpPaginator(discord.ui.View):
    def __init__(self, pages: list[HelpSection | None], *, author_id: int, start: int = 0) -> None:
        super().__init__(timeout=TIMEOUT_SECONDS)
        self.pages = pages
        self.author_id = author_id
        self.index = max(0, min(start, len(pages) - 1))
        self.message: discord.InteractionMessage | None = None

        self.menu = _CategoryMenu(pages)
        self.add_item(self.menu)
        self._sync_buttons()

    def embed(self) -> discord.Embed:
        return build_help_page(self.pages, self.index)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "This menu is someone else's — run /help for your own.", ephemeral=True
            )
            return False
        return True

    def _sync_buttons(self) -> None:
        self.previous.disabled = self.index == 0
        self.next.disabled = self.index >= len(self.pages) - 1
        self.counter.label = f"{self.index + 1} / {len(self.pages)}"
        for option in self.menu.options:
            option.default = option.value == str(self.index)

    async def show(self, interaction: discord.Interaction, index: int) -> None:
        self.index = max(0, min(index, len(self.pages) - 1))
        self._sync_buttons()
        await interaction.response.edit_message(embed=self.embed(), view=self)

    @discord.ui.button(emoji="◀️", style=discord.ButtonStyle.secondary, row=0)
    async def previous(self, interaction: discord.Interaction, _button: discord.ui.Button) -> None:
        await self.show(interaction, self.index - 1)

    @discord.ui.button(label="1 / 1", style=discord.ButtonStyle.secondary, disabled=True, row=0)
    async def counter(self, _interaction: discord.Interaction, _button: discord.ui.Button) -> None:
        """A label only."""

    @discord.ui.button(emoji="▶️", style=discord.ButtonStyle.primary, row=0)
    async def next(self, interaction: discord.Interaction, _button: discord.ui.Button) -> None:
        await self.show(interaction, self.index + 1)

    async def on_timeout(self) -> None:
        for item in self.children:
            if isinstance(item, discord.ui.Button | discord.ui.Select):
                item.disabled = True
        if self.message is not None:
            # The reply may already be gone; then there is nothing to tidy.
            with contextlib.suppress(discord.HTTPException):
                await self.message.edit(view=self)
