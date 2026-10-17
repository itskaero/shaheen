"""The one-tap link panel (docs/DECISIONS.md ADR-136).

A standing message (posted with /linkpanel, typically in #welcome) with one
button. A new member taps it, types their Brawlhalla or Steam64 ID, checks
the player it found, optionally picks their city, and confirms: linked, on
the Pakistan rankings, on their clan's roster and on City Wars, without
leaving Discord. It runs the same link flow as /link <ID>
(bot.cogs.link.complete_link). The button survives restarts (registered in
ShaheenBot.setup_hook); the confirm step is session-lived.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import TYPE_CHECKING, cast

import discord

from bot.content.profile_embeds import build_link_preview_embed
from bot.views.base import PersistentView
from core.exceptions import ShaheenError
from database.session import session_scope
from integrations.brawlhalla.models import SearchResult
from services.cities import CITIES
from services.city_service import CityService
from services.link_service import LinkService
from services.rate_limit import SlidingWindow

if TYPE_CHECKING:
    from bot.client import ShaheenBot

logger = logging.getLogger(__name__)

# Each lookup calls the Brawlhalla API: 5 tries per member per 10 minutes.
_LOOKUPS = SlidingWindow(limit=5, window=timedelta(minutes=10))
_NO_CITY = "none"


def build_link_panel_embed() -> discord.Embed:
    embed = discord.Embed(
        title="🔗 Get on the board",
        colour=0xFF6A1F,
        description=(
            "Link your Brawlhalla account in one tap and you're in:\n"
            "🇵🇰 on the **Pakistan rankings**\n"
            "⚔️ counting for your clan in **Clan Wars**\n"
            "🏙️ representing your city in **City Wars**\n"
            "🎯 tracking your **weekly quests**"
        ),
    )
    embed.add_field(
        name="You'll need",
        value="Your **Brawlhalla ID** (on your in-game profile) or your **Steam64 ID**.",
        inline=False,
    )
    embed.set_footer(text="Takes a minute. Your Discord account stays private on the website.")
    return embed


def _bot(interaction: discord.Interaction) -> ShaheenBot:
    return cast("ShaheenBot", interaction.client)


class LinkPanelView(PersistentView):
    @discord.ui.button(
        label="Link your account",
        emoji="🔗",
        style=discord.ButtonStyle.success,
        custom_id="brawlistan:link_panel:start",
    )
    async def start(self, interaction: discord.Interaction, _button: discord.ui.Button) -> None:
        member = interaction.user
        if not isinstance(member, discord.Member):
            raise ShaheenError("This only works inside the BRAWLISTAN server.")
        bot = _bot(interaction)
        async with session_scope(bot.session_factory) as session:
            existing = await LinkService(session, bot.brawlhalla).get_active_link(
                guild_id=member.guild.id, discord_id=member.id
            )
        if existing is not None:
            player = existing[1]
            city = CITIES.get(player.city or "", None)
            linked = f"✅ You're already linked to **{player.player_name}**"
            if city:
                await interaction.response.send_message(
                    f"{linked}, representing **{city}**.", ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"{linked}. Pick your city below:", view=CityOnlyView(member.id), ephemeral=True
                )
            return
        await interaction.response.send_modal(LinkModal())


class LinkModal(discord.ui.Modal, title="Link your Brawlhalla account"):
    identifier: discord.ui.TextInput[LinkModal] = discord.ui.TextInput(
        label="Brawlhalla ID or Steam64 ID",
        placeholder="e.g. 5734378 (shown on your in-game profile)",
        min_length=3,
        max_length=25,
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        member = interaction.user
        if not isinstance(member, discord.Member):
            raise ShaheenError("This only works inside the BRAWLISTAN server.")
        if not _LOOKUPS.allow(member.id):
            raise ShaheenError("That's a lot of tries. Wait a few minutes and try again.")
        await interaction.response.defer(ephemeral=True, thinking=True)
        bot = _bot(interaction)
        async with session_scope(bot.session_factory) as session:
            service = LinkService(session, bot.brawlhalla)
            candidate = await service.resolve_candidate(str(self.identifier.value).strip())
            existing = await service.get_active_link(guild_id=member.guild.id, discord_id=member.id)
        preview = build_link_preview_embed(
            candidate_name=candidate.name,
            candidate_id=candidate.brawlhalla_id,
            previous_player_name=existing[1].player_name if existing else None,
        )
        preview.add_field(
            name="Your city (optional)",
            value="Pick it below to fight for it in City Wars. You can change it once a season.",
            inline=False,
        )
        await interaction.followup.send(
            embed=preview, view=LinkConfirmView(member.id, candidate), ephemeral=True
        )

    async def on_error(  # type: ignore[override]  # discord.py types Modal.on_error narrower than BaseView
        self, interaction: discord.Interaction, error: Exception, /
    ) -> None:
        message = (
            f"⚠️ {error}"
            if isinstance(error, ShaheenError)
            else "⚠️ Something went wrong on BRAWLISTAN's side. This has been logged."
        )
        if not isinstance(error, ShaheenError):
            logger.exception("Link panel modal failed", exc_info=error)
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)


class _CitySelect(discord.ui.Select["discord.ui.View"]):
    def __init__(self) -> None:
        options = [discord.SelectOption(label="No city for now", value=_NO_CITY, emoji="➖")]
        options += [
            discord.SelectOption(label=label, value=key, emoji="🏙️") for key, label in CITIES.items()
        ]
        super().__init__(placeholder="🏙️ Your city (optional)", options=options[:25])

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()


async def _set_city(bot: ShaheenBot, member: discord.Member, city: str) -> str | None:
    """Set the member's city if they picked one. Returns its label."""
    if city == _NO_CITY or city not in CITIES:
        return None
    async with session_scope(bot.session_factory) as session:
        link = await LinkService(session, bot.brawlhalla).get_active_link(
            guild_id=member.guild.id, discord_id=member.id
        )
        if link is None:
            return None
        await CityService(session).set_city(
            guild_id=member.guild.id, player=link[1], city=city, actor_discord_id=member.id
        )
    return CITIES[city]


class _OwnerOnly(discord.ui.View):
    def __init__(self, owner_id: int) -> None:
        super().__init__(timeout=300)
        self._owner_id = owner_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self._owner_id

    async def on_error(
        self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item
    ) -> None:
        message = f"⚠️ {error}" if isinstance(error, ShaheenError) else "⚠️ Something went wrong."
        if not isinstance(error, ShaheenError):
            logger.exception("Link panel step failed", exc_info=error)
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)


class LinkConfirmView(_OwnerOnly):
    def __init__(self, owner_id: int, candidate: SearchResult) -> None:
        super().__init__(owner_id)
        self._candidate = candidate
        self._city = _CitySelect()
        self.add_item(self._city)

    @discord.ui.button(label="Yes, that's me", style=discord.ButtonStyle.success, emoji="✅", row=1)
    async def confirm(self, interaction: discord.Interaction, _button: discord.ui.Button) -> None:
        from bot.cogs.link import complete_link  # the cog imports the client; import late

        member = interaction.user
        assert isinstance(member, discord.Member)
        await interaction.response.edit_message(content="Linking…", embed=None, view=None)
        bot = _bot(interaction)
        embed = await complete_link(bot, member, self._candidate)
        city = await _set_city(bot, member, (self._city.values or [_NO_CITY])[0])
        if city:
            embed.add_field(name="City Wars", value=f"🏙️ You now represent **{city}**.")
        else:
            embed.add_field(name="City Wars", value="Pick your city anytime with `/city set`.")
        embed.add_field(
            name="Next",
            value="Play ranked: your games count for your clan and city every week.",
            inline=False,
        )
        await interaction.edit_original_response(content=None, embed=embed)
        self.stop()

    @discord.ui.button(label="Not me", style=discord.ButtonStyle.secondary, row=1)
    async def cancel(self, interaction: discord.Interaction, _button: discord.ui.Button) -> None:
        await interaction.response.edit_message(
            content="Cancelled. Tap **Link your account** again with the right ID.",
            embed=None,
            view=None,
        )
        self.stop()


class CityOnlyView(_OwnerOnly):
    """For members already linked without a city."""

    def __init__(self, owner_id: int) -> None:
        super().__init__(owner_id)
        self._city = _CitySelect()
        self.add_item(self._city)

    @discord.ui.button(label="Save city", style=discord.ButtonStyle.success, row=1)
    async def save(self, interaction: discord.Interaction, _button: discord.ui.Button) -> None:
        member = interaction.user
        assert isinstance(member, discord.Member)
        city = await _set_city(_bot(interaction), member, (self._city.values or [_NO_CITY])[0])
        await interaction.response.edit_message(
            content=f"🏙️ You now represent **{city}** on City Wars." if city else "No city saved.",
            view=None,
        )
        self.stop()
