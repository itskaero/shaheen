"""BRAWLISTAN network commands (docs/DECISIONS.md ADR-111): /ping, /site,
/rankings, /season, /legend, /tournaments, /looking, and /clanwars (ADR-131).

Any member, no permission check. Thin: data comes from services, embeds from
bot/content/network_embeds.py. Read-only replies are ephemeral, like /help.
None of these call the Brawlhalla API — they read what the snapshot loop
already stored.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Literal

import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy.ext.asyncio import AsyncSession

from bot.checks.permissions import require_setup_authorized
from bot.client import ShaheenBot
from bot.cogs.competition import announce_scrim
from bot.content.competition_embeds import build_spar_kiosk_embed
from bot.content.network_embeds import (
    build_city_board_embed,
    build_clan_wars_embed,
    build_legend_embed,
    build_ping_embed,
    build_quests_embed,
    build_rankings_embed,
    build_rising_embed,
    build_season_embed,
    build_site_embed,
    build_tournaments_embed,
    season_view,
    site_view,
)
from bot.content.season_embeds import attach_season_badge
from bot.spar_ping import spar_ping_message, toggle_spar_role
from bot.views.spar import SparKioskView
from core.exceptions import ShaheenError
from database.models.brawlhalla_player import BrawlhallaPlayer
from database.models.match import MatchKind
from database.repositories.tournament_repository import TournamentRepository
from database.session import session_scope
from services.cities import CITIES
from services.city_service import CityService
from services.clan_war_service import ClanWarService
from services.legend_art import available_portraits, legend_display_name, normalize_legend_key
from services.link_service import LinkService
from services.network_service import NetworkService
from services.pakistan_board_service import PakistanBoardService
from services.quest_service import QuestService
from services.rankings_service import RankingsService, ranked_rows
from services.seasons import pakistan_season

_ALL_LEGENDS = 200  # more than Brawlhalla has; "every legend" for the meta lookup


def _guild(interaction: discord.Interaction) -> discord.Guild:
    if interaction.guild is None:
        raise ShaheenError("This command can only be used inside the BRAWLISTAN server.")
    return interaction.guild


class NetworkCog(commands.Cog):
    def __init__(self, bot: ShaheenBot) -> None:
        self.bot = bot

    @app_commands.command(name="ping", description="Check that the bot is awake")
    async def ping(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(
            embed=build_ping_embed(round(self.bot.latency * 1000)), ephemeral=True
        )

    @app_commands.command(name="site", description="Links to the BRAWLISTAN website")
    async def site(self, interaction: discord.Interaction) -> None:
        url = self.bot.settings.site_url
        await interaction.response.send_message(
            embed=build_site_embed(url), view=site_view(url), ephemeral=True
        )

    @app_commands.command(name="rankings", description="Pakistan's top players")
    @app_commands.describe(board="Which board (default: 1v1)")
    async def rankings(
        self,
        interaction: discord.Interaction,
        board: Literal["1v1", "2v2", "rising", "city"] = "1v1",
    ) -> None:
        guild = _guild(interaction)
        await interaction.response.defer(ephemeral=True)
        site_url = self.bot.settings.site_url
        async with session_scope(self.bot.session_factory) as session:
            if board == "city":
                season, standings = await RankingsService(session).cities(guild.id)
                embed = build_city_board_embed(
                    standings=standings, season=season, site_url=site_url
                )
            elif board == "rising":
                climbers = await PakistanBoardService(session).climbers(
                    guild.id, since=datetime.now(UTC) - timedelta(days=7), limit=10
                )
                embed = build_rising_embed(climbers=climbers, site_url=site_url)
            else:
                result = await RankingsService(session).pakistan(guild.id)
                embed = build_rankings_embed(
                    rows=ranked_rows(result, board),
                    bracket=board,
                    season=result.season,
                    site_url=site_url,
                )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="season", description="The current Pakistan season")
    async def season(self, interaction: discord.Interaction) -> None:
        current = self.bot.current_brawlhalla_season()
        season = pakistan_season(current)
        if season is None:
            raise ShaheenError("Pakistan seasons start with Brawlhalla Season 42.")
        embed = build_season_embed(season, now=datetime.now(UTC))
        files = attach_season_badge(embed, current)
        view = season_view(self.bot.settings.site_url, current)
        await interaction.response.send_message(embed=embed, files=files, view=view, ephemeral=True)

    @app_commands.command(name="legend", description="How a Legend is played across Pakistan")
    @app_commands.describe(name="The Legend")
    async def legend(self, interaction: discord.Interaction, name: str) -> None:
        guild = _guild(interaction)
        key = normalize_legend_key(name)
        if not key or len(key) > 32:
            raise ShaheenError("Pick a Legend from the list.")
        await interaction.response.defer(ephemeral=True)
        async with session_scope(self.bot.session_factory) as session:
            meta = await NetworkService(session).legend_meta(guild.id, limit=_ALL_LEGENDS)
        rank, entry = next(
            (
                (i, e)
                for i, e in enumerate(meta, start=1)
                if normalize_legend_key(e.legend_name_key) == key
            ),
            (None, None),
        )
        if entry is None and key not in available_portraits():
            raise ShaheenError(f"No Legend called {name!r}.")
        await interaction.followup.send(
            embed=build_legend_embed(entry, legend_key=key, rank=rank), ephemeral=True
        )

    @legend.autocomplete("name")
    async def _legend_names(
        self, _interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        needle = normalize_legend_key(current)
        names = sorted(k for k in available_portraits() if needle in k)
        return [app_commands.Choice(name=legend_display_name(k), value=k) for k in names[:25]]

    @app_commands.command(name="tournaments", description="Upcoming and recent tournaments")
    async def tournaments(self, interaction: discord.Interaction) -> None:
        guild = _guild(interaction)
        await interaction.response.defer(ephemeral=True)
        async with session_scope(self.bot.session_factory) as session:
            rows = await TournamentRepository(session).list_for_guild(guild.id, limit=10)
        await interaction.followup.send(
            embed=build_tournaments_embed(rows, site_url=self.bot.settings.site_url),
            ephemeral=True,
        )

    @app_commands.command(name="looking", description="Find a 1v1 sparring partner or 2v2 game")
    @app_commands.describe(
        mode="1v1 or 2v2", note="Optional, e.g. 'FT5, NA servers' (80 characters, no links)"
    )
    @app_commands.checks.cooldown(1, 120, key=lambda i: i.user.id)
    async def looking(
        self,
        interaction: discord.Interaction,
        mode: Literal["1v1", "2v2"],
        note: app_commands.Range[str, 1, 120] | None = None,
    ) -> None:
        member = interaction.user
        if not isinstance(member, discord.Member):
            raise ShaheenError("This command can only be used inside the BRAWLISTAN server.")
        await interaction.response.defer(ephemeral=True)
        kind = MatchKind.TWO_V_TWO if mode == "2v2" else MatchKind.ONE_V_ONE
        # Same flow as /scrim and the spar kiosk: a spar card in
        # #looking-for-game, with you already on Side A (ADR-136).
        await announce_scrim(
            self.bot,
            interaction,
            member,
            kind,
            ephemeral_confirmation=True,
            note=note,
            join_creator=True,
        )

    @app_commands.command(
        name="sparping", description="Turn spar pings on or off: get tagged when someone's looking"
    )
    async def sparping(self, interaction: discord.Interaction) -> None:
        member = interaction.user
        if not isinstance(member, discord.Member):
            raise ShaheenError("This command can only be used inside the BRAWLISTAN server.")
        await interaction.response.defer(ephemeral=True)
        state = await toggle_spar_role(self.bot, member)
        await interaction.followup.send(spar_ping_message(state), ephemeral=True)

    @app_commands.command(
        name="sparpanel", description="Post the looking-for-game panel in this channel (admin)"
    )
    @require_setup_authorized()
    async def spar_panel(self, interaction: discord.Interaction) -> None:
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            raise ShaheenError("Run this in a text channel.")
        await channel.send(embed=build_spar_kiosk_embed(), view=SparKioskView())
        await interaction.response.send_message("Spar panel posted.", ephemeral=True)

    # --- City Wars and weekly quests (ADR-128) -----------------------------

    city = app_commands.Group(name="city", description="Represent your city in City Wars")

    async def _linked_player(
        self, guild: discord.Guild, member_id: int, session: AsyncSession
    ) -> BrawlhallaPlayer | None:
        link = await LinkService(session, self.bot.brawlhalla).get_active_link(
            guild_id=guild.id, discord_id=member_id
        )
        if link is None:
            return None
        return link[1]

    @city.command(name="set", description="Pick the city you represent on City Wars")
    @app_commands.describe(city="Your city")
    @app_commands.choices(
        city=[app_commands.Choice(name=label, value=key) for key, label in CITIES.items()]
    )
    async def city_set(self, interaction: discord.Interaction, city: str) -> None:
        guild = _guild(interaction)
        await interaction.response.defer(ephemeral=True)
        async with session_scope(self.bot.session_factory) as session:
            player = await self._linked_player(guild, interaction.user.id, session)
            if player is None:
                raise ShaheenError("Link your Brawlhalla account first with `/link`.")
            await CityService(session).set_city(
                guild_id=guild.id, player=player, city=city, actor_discord_id=interaction.user.id
            )
        await interaction.followup.send(
            f"🏙️ You now represent **{CITIES[city]}** on City Wars. "
            "It counts once you're placed this season.",
            ephemeral=True,
        )

    @city.command(name="clear", description="Stop representing a city")
    async def city_clear(self, interaction: discord.Interaction) -> None:
        guild = _guild(interaction)
        await interaction.response.defer(ephemeral=True)
        async with session_scope(self.bot.session_factory) as session:
            player = await self._linked_player(guild, interaction.user.id, session)
            if player is None:
                raise ShaheenError("Link your Brawlhalla account first with `/link`.")
            await CityService(session).set_city(
                guild_id=guild.id, player=player, city=None, actor_discord_id=interaction.user.id
            )
        await interaction.followup.send("Your city is cleared.", ephemeral=True)

    @app_commands.command(name="quests", description="This week's quests and your season level")
    @app_commands.describe(user="Whose quests (defaults to you)")
    async def quests(
        self, interaction: discord.Interaction, user: discord.Member | None = None
    ) -> None:
        guild = _guild(interaction)
        target = user or interaction.user
        await interaction.response.defer(ephemeral=True)
        async with session_scope(self.bot.session_factory) as session:
            player = await self._linked_player(guild, target.id, session)
            if player is None:
                who = (
                    "You haven't"
                    if target.id == interaction.user.id
                    else f"{target.display_name} hasn't"
                )
                raise ShaheenError(f"{who} linked a Brawlhalla account (`/link`).")
            status = await QuestService(session).status(player)
            embed = build_quests_embed(player_name=player.player_name, status=status)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="clanwars", description="This week's Clan Wars standings")
    async def clanwars(self, interaction: discord.Interaction) -> None:
        guild = _guild(interaction)
        await interaction.response.defer(ephemeral=True)
        async with session_scope(self.bot.session_factory) as session:
            board = await ClanWarService(
                session, min_games=self.bot.settings.clan_wars_min_games
            ).board(guild.id)
            embed = build_clan_wars_embed(board=board, site_url=self.bot.settings.site_url)
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: ShaheenBot) -> None:
    await bot.add_cog(NetworkCog(bot))
