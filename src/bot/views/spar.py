"""Persistent "looking for a sparring partner" kiosk (docs/DECISIONS.md
ADR-058) — a standing panel in #ranked with 1v1/2v2 buttons.

Deliberately not a new system: clicking a button runs the exact same
announce_scrim() flow /scrim already uses (bot/cogs/competition.py) — a
real Scrim row, a join-embed posted to #scrims, auto side-matching — just
reachable without typing the command. bot/cogs/setup.py posts this panel
once, idempotently, in launch mode; ShaheenBot.setup_hook() re-registers
the view globally on every process start so the buttons keep working
across restarts.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import discord

from bot.cogs.competition import announce_scrim
from bot.views.base import PersistentView
from core.exceptions import ShaheenError
from database.models.match import MatchKind

if TYPE_CHECKING:
    from bot.client import ShaheenBot


class SparKioskView(PersistentView):
    @discord.ui.button(
        label="Looking for a 1v1",
        style=discord.ButtonStyle.primary,
        emoji="🥊",
        custom_id="shaheen:spar_kiosk:1v1",
    )
    async def spar_1v1(self, interaction: discord.Interaction, _button: discord.ui.Button) -> None:
        await self._announce(interaction, MatchKind.ONE_V_ONE)

    @discord.ui.button(
        label="Looking for a 2v2",
        style=discord.ButtonStyle.primary,
        emoji="👥",
        custom_id="shaheen:spar_kiosk:2v2",
    )
    async def spar_2v2(self, interaction: discord.Interaction, _button: discord.ui.Button) -> None:
        await self._announce(interaction, MatchKind.TWO_V_TWO)

    async def _announce(self, interaction: discord.Interaction, match_kind: MatchKind) -> None:
        member = interaction.user
        if not isinstance(member, discord.Member) or interaction.guild is None:
            raise ShaheenError("This only works inside the Shaheen server.")

        bot = cast("ShaheenBot", interaction.client)
        await interaction.response.defer(ephemeral=True)
        await announce_scrim(bot, interaction, member, match_kind, ephemeral_confirmation=True)
