"""/pakistan — the Pakistan leaderboard (docs/DECISIONS.md ADR-099).

Stays thin (docs/ARCHITECTURE.md): board rules live in
services/pakistan_board_service.py, identifier resolution reuses /link's
LinkService.resolve_candidate. /link still only ever feeds the clan board.
"""

from __future__ import annotations

import logging

import discord
from discord import app_commands
from discord.ext import commands

from bot.checks.permissions import require_staff_authorized
from bot.client import ShaheenBot
from bot.content.clan_embeds import build_leaderboard_embed, build_pakistan_board_embed
from bot.views.confirm import ConfirmView
from core.exceptions import ShaheenError
from database.models.brawlhalla_player import BrawlhallaPlayer
from database.session import session_scope
from integrations.brawlhalla.errors import BrawlhallaAPIError
from integrations.brawlhalla.models import SearchResult
from services.link_service import LinkService
from services.pakistan_board_service import PakistanBoardService
from services.snapshot_service import SnapshotService

logger = logging.getLogger(__name__)

_TITLE = "🇵🇰 Pakistan Leaderboard"


class PakistanCog(commands.Cog):
    pakistan_group = app_commands.Group(
        name="pakistan", description="Pakistan's Brawlhalla leaderboard"
    )

    def __init__(self, bot: ShaheenBot) -> None:
        self.bot = bot

    async def _resolve(self, identifier: str) -> SearchResult:
        async with session_scope(self.bot.session_factory) as session:
            return await LinkService(session, self.bot.brawlhalla).resolve_candidate(identifier)

    async def _confirm(
        self, interaction: discord.Interaction, candidate: SearchResult, note: str
    ) -> discord.WebhookMessage | None:
        preview = build_pakistan_board_embed(
            title="🇵🇰 Add to the Pakistan Leaderboard?",
            description=(
                f"**{candidate.name}** (Brawlhalla ID `{candidate.brawlhalla_id}`)\n\n{note}"
            ),
        )
        view = ConfirmView(author_id=interaction.user.id)
        message = await interaction.followup.send(
            embed=preview, view=view, ephemeral=True, wait=True
        )
        await view.wait()
        if not view.confirmed:
            await message.edit(content="Cancelled.", embed=None, view=None)
            return None
        return message

    async def _initial_snapshot(self, player: BrawlhallaPlayer) -> None:
        # Same reasoning as /link: appear now, not at the next 6-hourly tick,
        # and never fail the command over a Brawlhalla hiccup.
        try:
            async with session_scope(self.bot.session_factory) as session:
                await SnapshotService(
                    session, self.bot.brawlhalla, season=self.bot.settings.brawlhalla_season
                ).snapshot_player(player)
        except BrawlhallaAPIError as exc:
            logger.warning("Initial Pakistan-board snapshot failed for %s: %s", player.id, exc)

    @pakistan_group.command(name="join", description="Add yourself to the Pakistan leaderboard")
    @app_commands.describe(identifier="Your Brawlhalla player ID or Steam64 ID")
    async def join(self, interaction: discord.Interaction, identifier: str) -> None:
        if interaction.guild is None:
            raise ShaheenError("This command can only be used inside the Shaheen server.")
        await interaction.response.defer(ephemeral=True)

        candidate = await self._resolve(identifier)
        message = await self._confirm(
            interaction,
            candidate,
            "For Pakistan-based players. Being on this board doesn't make you a Shaheen member "
            "— that's `/apply`.",
        )
        if message is None:
            return

        async with session_scope(self.bot.session_factory) as session:
            outcome = await PakistanBoardService(session).join(
                guild_id=interaction.guild.id,
                discord_id=interaction.user.id,
                candidate=candidate,
            )
        await self._initial_snapshot(outcome.player)

        description = f"**{outcome.player.player_name}** is on the Pakistan leaderboard."
        if outcome.replaced_player_name:
            description += f"\n\nReplaced your previous entry, **{outcome.replaced_player_name}**."
        await message.edit(
            content=None,
            embed=build_pakistan_board_embed(title="✅ Added", description=description),
            view=None,
        )

    @pakistan_group.command(name="leave", description="Take yourself off the Pakistan leaderboard")
    async def leave(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            raise ShaheenError("This command can only be used inside the Shaheen server.")
        await interaction.response.defer(ephemeral=True)
        async with session_scope(self.bot.session_factory) as session:
            player = await PakistanBoardService(session).leave(
                guild_id=interaction.guild.id, discord_id=interaction.user.id
            )
        if player is None:
            await interaction.followup.send(
                "You're not on the Pakistan leaderboard.", ephemeral=True
            )
            return
        await interaction.followup.send(
            embed=build_pakistan_board_embed(
                title="Removed", description=f"**{player.player_name}** is off the board."
            ),
            ephemeral=True,
        )

    @pakistan_group.command(
        name="add", description="Add any Pakistani player to the leaderboard (staff)"
    )
    @app_commands.describe(identifier="Their Brawlhalla player ID or Steam64 ID")
    @require_staff_authorized()
    async def add(self, interaction: discord.Interaction, identifier: str) -> None:
        if interaction.guild is None:
            raise ShaheenError("This command can only be used inside the Shaheen server.")
        await interaction.response.defer(ephemeral=True)

        candidate = await self._resolve(identifier)
        message = await self._confirm(
            interaction,
            candidate,
            "They don't need to be in this server. If they join later, `/pakistan join` "
            "with this ID makes the entry theirs.",
        )
        if message is None:
            return

        async with session_scope(self.bot.session_factory) as session:
            player = await PakistanBoardService(session).add(
                guild_id=interaction.guild.id,
                added_by_discord_id=interaction.user.id,
                candidate=candidate,
            )
        await self._initial_snapshot(player)
        await message.edit(
            content=None,
            embed=build_pakistan_board_embed(
                title="✅ Added", description=f"**{player.player_name}** is on the board."
            ),
            view=None,
        )

    @pakistan_group.command(
        name="remove", description="Remove a player from the Pakistan leaderboard (staff)"
    )
    @app_commands.describe(brawlhalla_id="Their Brawlhalla player ID")
    @require_staff_authorized()
    async def remove(self, interaction: discord.Interaction, brawlhalla_id: int) -> None:
        if interaction.guild is None:
            raise ShaheenError("This command can only be used inside the Shaheen server.")
        await interaction.response.defer(ephemeral=True)
        async with session_scope(self.bot.session_factory) as session:
            player = await PakistanBoardService(session).remove(
                guild_id=interaction.guild.id, brawlhalla_id=brawlhalla_id
            )
        if player is None:
            raise ShaheenError(f"Brawlhalla ID `{brawlhalla_id}` isn't on the Pakistan board.")
        await interaction.followup.send(
            embed=build_pakistan_board_embed(
                title="Removed", description=f"**{player.player_name}** is off the board."
            ),
            ephemeral=True,
        )

    @pakistan_group.command(name="leaderboard", description="Show the Pakistan leaderboard")
    async def leaderboard(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            raise ShaheenError("This command can only be used inside the Shaheen server.")
        await interaction.response.defer(ephemeral=True)
        async with session_scope(self.bot.session_factory) as session:
            service = PakistanBoardService(session)
            rows = await service.leaderboard(interaction.guild.id)
            season = await service.current_season()

        entries = [
            (
                f"{'🦅 ' if row.is_clan_member else ''}{row.player.player_name}",
                row.snapshot.tier,
                row.snapshot.rating,
            )
            for row in rows
        ]
        await interaction.followup.send(
            embed=build_leaderboard_embed(
                entries,
                season,
                title=_TITLE,
                empty_hint="add yourself with `/pakistan join`",
                noun="player",
            ),
            ephemeral=True,
        )


async def setup(bot: ShaheenBot) -> None:
    await bot.add_cog(PakistanCog(bot))
