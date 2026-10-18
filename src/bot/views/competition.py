"""Views for /challenge, /scrim, and /report.

Session-lived only (docs/DECISIONS.md ADR-038) — like ConfirmView, these
don't survive a bot restart.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

import discord

ChallengeResponse = Callable[[discord.Interaction, bool], Awaitable[None]]
ScrimJoin = Callable[[discord.Interaction, str], Awaitable[None]]
ScrimCancel = Callable[[discord.Interaction], Awaitable[None]]
ScrimExpire = Callable[[], Awaitable[None]]
ReportResponse = Callable[[discord.Interaction, bool], Awaitable[None]]


class ChallengeView(discord.ui.View):
    def __init__(
        self, *, opponent_id: int, on_response: ChallengeResponse, timeout: float = 3600
    ) -> None:
        super().__init__(timeout=timeout)
        self._opponent_id = opponent_id
        self._on_response = on_response

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self._opponent_id:
            await interaction.response.send_message(
                "Only the challenged player can respond.", ephemeral=True
            )
            return False
        return True

    def _disable_all(self) -> None:
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.success, emoji="✅")
    async def accept(self, interaction: discord.Interaction, _button: discord.ui.Button) -> None:
        self._disable_all()
        await self._on_response(interaction, True)
        self.stop()

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.danger, emoji="✖️")
    async def decline(self, interaction: discord.Interaction, _button: discord.ui.Button) -> None:
        self._disable_all()
        await self._on_response(interaction, False)
        self.stop()


class ScrimJoinView(discord.ui.View):
    """One "Join" button for 1v1 (auto-assigned side), two for 2v2, and,
    for a spar call (ADR-136), a Cancel only its creator can use. When the
    call times out unanswered, `on_expire` closes it."""

    def __init__(
        self,
        *,
        is_team: bool,
        on_join: ScrimJoin,
        on_cancel: ScrimCancel | None = None,
        on_expire: ScrimExpire | None = None,
        timeout: float = 3600,
    ) -> None:
        super().__init__(timeout=timeout)
        self._on_join = on_join
        self._on_expire = on_expire

        if is_team:
            self.add_item(_JoinSideButton("Join Side A", "A", self._on_join))
            self.add_item(_JoinSideButton("Join Side B", "B", self._on_join))
        else:
            self.add_item(_JoinSideButton("Join", "auto", self._on_join))
        if on_cancel is not None:
            self.add_item(_CancelButton(on_cancel))

    async def on_timeout(self) -> None:
        if self._on_expire is not None:
            await self._on_expire()


class _JoinSideButton(discord.ui.Button):
    def __init__(self, label: str, side: str, on_join: ScrimJoin) -> None:
        super().__init__(label=label, style=discord.ButtonStyle.success, emoji="⚔️")
        self._side = side
        self._on_join = on_join

    async def callback(self, interaction: discord.Interaction) -> None:
        await self._on_join(interaction, self._side)


class _CancelButton(discord.ui.Button):
    def __init__(self, on_cancel: ScrimCancel) -> None:
        super().__init__(label="Cancel", style=discord.ButtonStyle.secondary)
        self._on_cancel = on_cancel

    async def callback(self, interaction: discord.Interaction) -> None:
        await self._on_cancel(interaction)


class ReportConfirmView(discord.ui.View):
    def __init__(
        self, *, allowed_discord_ids: set[int], on_response: ReportResponse, timeout: float = 3600
    ) -> None:
        super().__init__(timeout=timeout)
        self._allowed_discord_ids = allowed_discord_ids
        self._on_response = on_response

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id not in self._allowed_discord_ids:
            await interaction.response.send_message(
                "Only the other side can confirm or dispute this result.", ephemeral=True
            )
            return False
        return True

    def _disable_all(self) -> None:
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.success, emoji="✅")
    async def confirm(self, interaction: discord.Interaction, _button: discord.ui.Button) -> None:
        self._disable_all()
        await self._on_response(interaction, True)
        self.stop()

    @discord.ui.button(label="Dispute", style=discord.ButtonStyle.danger, emoji="⚠️")
    async def dispute(self, interaction: discord.Interaction, _button: discord.ui.Button) -> None:
        self._disable_all()
        await self._on_response(interaction, False)
        self.stop()
