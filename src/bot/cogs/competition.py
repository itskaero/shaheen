"""/challenge, /scrim, /match, /report, /matches, /tournament.

Stays thin (docs/ARCHITECTURE.md): all persistence/state-machine logic
lives in services/match_service.py and services/tournament_service.py.

Message visibility rule: a response is ephemeral unless it carries a view
someone other than the invoker must see and click (challenge accept/decline,
scrim sign-up, report confirm/dispute) or it's a public announcement
(scrim/tournament creation) — everything else stays ephemeral, matching
Phase 2/3's read commands.
"""

from __future__ import annotations

import logging
from typing import Literal

import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy.ext.asyncio import AsyncSession

from bot.checks.permissions import require_staff_authorized
from bot.client import ShaheenBot
from bot.content.competition_embeds import (
    build_bracket_embed,
    build_challenge_embed,
    build_challenge_result_embed,
    build_match_embed,
    build_match_history_embed,
    build_report_outcome_embed,
    build_report_preview_embed,
    build_scrim_embed,
    build_scrim_full_embed,
    build_tournament_created_embed,
)
from bot.views.competition import ChallengeView, ReportConfirmView, ScrimJoinView
from core.exceptions import ShaheenError
from database.models.match import MatchKind, MatchSide
from database.models.provisioned_resource import ResourceType
from database.models.tournament import TournamentMatch
from database.repositories.match_repository import MatchRepository
from database.repositories.provisioned_resource_repository import ProvisionedResourceRepository
from database.repositories.shaheen_member_repository import ShaheenMemberRepository
from database.repositories.tournament_repository import (
    TournamentEntrantRepository,
    TournamentMatchRepository,
    TournamentRepository,
)
from database.session import session_scope
from services.match_service import MatchService
from services.tournament_service import TournamentService

logger = logging.getLogger(__name__)

_KIND_MAP: dict[str, MatchKind] = {"1v1": MatchKind.ONE_V_ONE, "2v2": MatchKind.TWO_V_TWO}
_SIDE_MAP: dict[str, MatchSide] = {"A": MatchSide.A, "B": MatchSide.B}


class CompetitionCog(commands.Cog):
    def __init__(self, bot: ShaheenBot) -> None:
        self.bot = bot

    # --- /challenge -----------------------------------------------------

    @app_commands.command(name="challenge", description="Challenge another member to a 1v1")
    @app_commands.describe(opponent="Who to challenge")
    async def challenge(self, interaction: discord.Interaction, opponent: discord.Member) -> None:
        member = _require_member(interaction)
        if opponent.bot:
            raise ShaheenError("You can't challenge a bot.")

        await interaction.response.defer()
        async with session_scope(self.bot.session_factory) as session:
            challenge = await MatchService(session).create_challenge(
                guild_id=member.guild.id,
                challenger_discord_id=member.id,
                challenger_joined_at=member.joined_at,
                opponent_discord_id=opponent.id,
                opponent_joined_at=opponent.joined_at,
            )
            challenge_id = challenge.id

        async def on_response(view_interaction: discord.Interaction, accepted: bool) -> None:
            async with session_scope(self.bot.session_factory) as inner_session:
                service = MatchService(inner_session)
                if accepted:
                    await service.accept_challenge(challenge_id)
                else:
                    await service.decline_challenge(challenge_id)
            await view_interaction.response.edit_message(
                embed=build_challenge_result_embed(
                    accepted=accepted, opponent_name=opponent.display_name
                ),
                view=None,
            )

        view = ChallengeView(opponent_id=opponent.id, on_response=on_response)
        await interaction.followup.send(
            embed=build_challenge_embed(
                challenger_name=member.display_name, opponent_name=opponent.display_name
            ),
            view=view,
        )

    # --- /scrim -----------------------------------------------------------

    @app_commands.command(name="scrim", description="Announce a scrim for members to join")
    @app_commands.describe(kind="1v1 or 2v2")
    async def scrim(self, interaction: discord.Interaction, kind: Literal["1v1", "2v2"]) -> None:
        member = _require_member(interaction)
        match_kind = _KIND_MAP[kind]

        await interaction.response.defer()
        async with session_scope(self.bot.session_factory) as session:
            scrim = await MatchService(session).create_scrim(
                guild_id=member.guild.id,
                creator_discord_id=member.id,
                creator_joined_at=member.joined_at,
                kind=match_kind,
            )
            scrim_id = scrim.id

        async def on_join(view_interaction: discord.Interaction, side: str) -> None:
            joiner = view_interaction.user
            if not isinstance(joiner, discord.Member):
                return
            async with session_scope(self.bot.session_factory) as inner_session:
                service = MatchService(inner_session)
                if side in _SIDE_MAP:
                    resolved_side = _SIDE_MAP[side]
                else:
                    resolved_side = await service.resolve_scrim_side(scrim_id)
                result = await service.join_scrim(
                    scrim_id=scrim_id,
                    discord_id=joiner.id,
                    joined_at=joiner.joined_at,
                    side=resolved_side,
                )

            if result.match is not None:
                await view_interaction.response.edit_message(
                    embed=build_scrim_full_embed(kind=match_kind), view=None
                )
            else:
                await view_interaction.response.edit_message(
                    embed=build_scrim_embed(
                        creator_name=member.display_name,
                        kind=match_kind,
                        side_counts=result.side_counts,
                    )
                )

        view = ScrimJoinView(is_team=match_kind is MatchKind.TWO_V_TWO, on_join=on_join)
        embed = build_scrim_embed(
            creator_name=member.display_name, kind=match_kind, side_counts=(0, 0)
        )
        target_channel = await self._provisioned_channel(member.guild, "channel:scrims")
        if target_channel is not None:
            await target_channel.send(embed=embed, view=view)
            await interaction.followup.send(f"Scrim announced in {target_channel.mention}.")
        else:
            await interaction.followup.send(embed=embed, view=view)

    # --- /report ------------------------------------------------------------

    @app_commands.command(name="report", description="Report a match result")
    @app_commands.describe(match_id="The match ID", result="Did you win or lose?")
    async def report(
        self, interaction: discord.Interaction, match_id: int, result: Literal["win", "loss"]
    ) -> None:
        member = _require_member(interaction)
        await interaction.response.defer(ephemeral=True)

        async with session_scope(self.bot.session_factory) as session:
            service = MatchService(session)
            match = await service.report_result(
                match_id=match_id,
                guild_id=member.guild.id,
                reporter_discord_id=member.id,
                reporter_won=result == "win",
            )
            confirming_side = await service.confirming_side(match)
            opposing_ids = (
                await MatchRepository(session).discord_ids_on_side(match_id, confirming_side)
                if confirming_side is not None
                else []
            )

        await interaction.followup.send("Your report has been submitted.", ephemeral=True)

        async def on_response(view_interaction: discord.Interaction, confirmed: bool) -> None:
            async with session_scope(self.bot.session_factory) as inner_session:
                service = MatchService(inner_session)
                if confirmed:
                    resolved_match = await service.confirm_result(
                        match_id=match_id,
                        guild_id=member.guild.id,
                        confirmer_discord_id=view_interaction.user.id,
                    )
                    await self._maybe_advance_tournament(
                        inner_session, match_id, resolved_match.winning_side
                    )
                else:
                    await service.dispute_result(
                        match_id=match_id,
                        guild_id=member.guild.id,
                        disputer_discord_id=view_interaction.user.id,
                    )
            await view_interaction.response.edit_message(
                embed=build_report_outcome_embed(confirmed=confirmed), view=None
            )

        claim = "won" if result == "win" else "lost"
        view = ReportConfirmView(allowed_discord_ids=set(opposing_ids), on_response=on_response)
        channel = interaction.channel
        if isinstance(channel, discord.TextChannel):
            await channel.send(
                embed=build_report_preview_embed(reporter_name=member.display_name, claim=claim),
                view=view,
            )

    # --- /matches -------------------------------------------------------------

    @app_commands.command(name="matches", description="Show a Shaheen member's match history")
    @app_commands.describe(user="Whose history to show (defaults to you)")
    async def matches(
        self, interaction: discord.Interaction, user: discord.Member | None = None
    ) -> None:
        member = _require_member(interaction)
        target = user or member
        await interaction.response.defer(ephemeral=True)

        async with session_scope(self.bot.session_factory) as session:
            history = await MatchService(session).get_match_history(
                guild_id=member.guild.id, discord_id=target.id
            )

        embed = build_match_history_embed(display_name=target.display_name, matches=history)
        await interaction.followup.send(embed=embed, ephemeral=True)

    # --- /match -----------------------------------------------------------

    match_group = app_commands.Group(name="match", description="Create or inspect a match")

    @match_group.command(name="create", description="Log a match directly between named players")
    @app_commands.describe(
        kind="1v1 or 2v2",
        a1="Side A player 1",
        b1="Side B player 1",
        a2="Side A player 2 (2v2 only)",
        b2="Side B player 2 (2v2 only)",
    )
    async def match_create(
        self,
        interaction: discord.Interaction,
        kind: Literal["1v1", "2v2"],
        a1: discord.Member,
        b1: discord.Member,
        a2: discord.Member | None = None,
        b2: discord.Member | None = None,
    ) -> None:
        member = _require_member(interaction)
        match_kind = _KIND_MAP[kind]
        side_a = [(a1.id, a1.joined_at), *([(a2.id, a2.joined_at)] if a2 else [])]
        side_b = [(b1.id, b1.joined_at), *([(b2.id, b2.joined_at)] if b2 else [])]

        await interaction.response.defer(ephemeral=True)
        async with session_scope(self.bot.session_factory) as session:
            match = await MatchService(session).create_match(
                guild_id=member.guild.id, kind=match_kind, side_a=side_a, side_b=side_b
            )

        await interaction.followup.send(
            f"Match #{match.id} created. Report it with `/report match_id:{match.id}`.",
            ephemeral=True,
        )

    @match_group.command(name="view", description="Inspect a match's current status")
    @app_commands.describe(match_id="The match ID")
    async def match_view(self, interaction: discord.Interaction, match_id: int) -> None:
        _require_member(interaction)
        await interaction.response.defer(ephemeral=True)

        async with session_scope(self.bot.session_factory) as session:
            match_repo = MatchRepository(session)
            match = await match_repo.get(match_id)
            if match is None:
                raise ShaheenError("That match doesn't exist.")
            side_a_ids = await match_repo.discord_ids_on_side(match_id, MatchSide.A)
            side_b_ids = await match_repo.discord_ids_on_side(match_id, MatchSide.B)

        guild = interaction.guild
        side_a_names = [_display_name(guild, discord_id) for discord_id in side_a_ids]
        side_b_names = [_display_name(guild, discord_id) for discord_id in side_b_ids]
        embed = build_match_embed(match=match, side_a_names=side_a_names, side_b_names=side_b_names)
        await interaction.followup.send(embed=embed, ephemeral=True)

    # --- /tournament ------------------------------------------------------

    tournament_group = app_commands.Group(name="tournament", description="Manage clan tournaments")

    @tournament_group.command(name="create", description="Create a tournament (staff only)")
    @app_commands.describe(name="Tournament name", kind="1v1 or 2v2")
    @require_staff_authorized()
    async def tournament_create(
        self, interaction: discord.Interaction, name: str, kind: Literal["1v1", "2v2"]
    ) -> None:
        member = _require_member(interaction)
        await interaction.response.defer()

        async with session_scope(self.bot.session_factory) as session:
            tournament = await TournamentService(session).create_tournament(
                guild_id=member.guild.id,
                name=name,
                kind=_KIND_MAP[kind],
                creator_discord_id=member.id,
                creator_joined_at=member.joined_at,
            )

        embed = build_tournament_created_embed(tournament=tournament)
        target_channel = await self._provisioned_channel(member.guild, "channel:tournaments")
        if target_channel is not None:
            await target_channel.send(embed=embed)
            await interaction.followup.send(
                f"Tournament #{tournament.id} announced in {target_channel.mention}."
            )
        else:
            await interaction.followup.send(embed=embed)

    @tournament_group.command(name="register", description="Register for a tournament")
    @app_commands.describe(
        tournament_id="The tournament ID", partner="Your teammate (2v2 tournaments only)"
    )
    async def tournament_register(
        self,
        interaction: discord.Interaction,
        tournament_id: int,
        partner: discord.Member | None = None,
    ) -> None:
        member = _require_member(interaction)
        await interaction.response.defer(ephemeral=True)

        discord_ids = [(member.id, member.joined_at)]
        if partner is not None:
            if partner.id == member.id:
                raise ShaheenError("You can't register with yourself as a partner.")
            discord_ids.append((partner.id, partner.joined_at))

        async with session_scope(self.bot.session_factory) as session:
            await TournamentService(session).register(
                tournament_id=tournament_id, guild_id=member.guild.id, discord_ids=discord_ids
            )

        await interaction.followup.send("You're registered!", ephemeral=True)

    @tournament_group.command(
        name="start", description="Start a tournament and generate the bracket (staff only)"
    )
    @app_commands.describe(tournament_id="The tournament ID")
    @require_staff_authorized()
    async def tournament_start(self, interaction: discord.Interaction, tournament_id: int) -> None:
        _require_member(interaction)
        await interaction.response.defer()

        async with session_scope(self.bot.session_factory) as session:
            tournament = await TournamentService(session).start_tournament(tournament_id)
            embed = await self._build_bracket_embed(session, tournament_id)

        content = f"🏆 **{tournament.name}** has started!"
        await interaction.followup.send(content=content, embed=embed)

    @tournament_group.command(name="bracket", description="Show a tournament's current bracket")
    @app_commands.describe(tournament_id="The tournament ID")
    async def tournament_bracket(
        self, interaction: discord.Interaction, tournament_id: int
    ) -> None:
        _require_member(interaction)
        await interaction.response.defer(ephemeral=True)

        async with session_scope(self.bot.session_factory) as session:
            embed = await self._build_bracket_embed(session, tournament_id)

        await interaction.followup.send(embed=embed, ephemeral=True)

    @tournament_group.command(
        name="resolve", description="Force-resolve a stuck or disputed bracket match (staff only)"
    )
    @app_commands.describe(tournament_match_id="The bracket match ID", winner="Which side won")
    @require_staff_authorized()
    async def tournament_resolve(
        self, interaction: discord.Interaction, tournament_match_id: int, winner: Literal["A", "B"]
    ) -> None:
        member = _require_member(interaction)
        await interaction.response.defer(ephemeral=True)

        async with session_scope(self.bot.session_factory) as session:
            result = await TournamentService(session).resolve_bracket_match(
                tournament_match_id=tournament_match_id,
                guild_id=member.guild.id,
                resolver_discord_id=member.id,
                winning_side=_SIDE_MAP[winner],
            )

        message = "Tournament completed!" if result.tournament_completed else "Bracket advanced."
        await interaction.followup.send(message, ephemeral=True)

    # --- Shared helpers -----------------------------------------------------

    async def _provisioned_channel(
        self, guild: discord.Guild, logical_key: str
    ) -> discord.TextChannel | None:
        async with session_scope(self.bot.session_factory) as session:
            resource = await ProvisionedResourceRepository(session).get(
                guild_id=guild.id, resource_type=ResourceType.CHANNEL, logical_key=logical_key
            )
        if resource is None:
            return None
        channel = guild.get_channel(resource.discord_id)
        return channel if isinstance(channel, discord.TextChannel) else None

    async def _maybe_advance_tournament(
        self, session: AsyncSession, match_id: int, winning_side: MatchSide | None
    ) -> None:
        if winning_side is None:
            return
        service = TournamentService(session)
        bracket_match = await service.get_bracket_match_for(match_id)
        if bracket_match is None:
            return  # this Match isn't part of a tournament
        await service.advance_from_match(bracket_match, winning_side=winning_side)

    async def _build_bracket_embed(
        self, session: AsyncSession, tournament_id: int
    ) -> discord.Embed:
        tournament = await TournamentRepository(session).get(tournament_id)
        if tournament is None:
            raise ShaheenError("That tournament doesn't exist.")

        bracket_repo = TournamentMatchRepository(session)
        entrant_repo = TournamentEntrantRepository(session)
        members_repo = ShaheenMemberRepository(session)
        guild = self.bot.get_guild(tournament.guild_id)

        rounds: dict[int, list[tuple[TournamentMatch, str, str]]] = {}
        for bracket_match in await bracket_repo.list_all(tournament_id):
            a_label = await self._entrant_label(
                entrant_repo, members_repo, guild, bracket_match.entrant_a_id
            )
            b_label = await self._entrant_label(
                entrant_repo, members_repo, guild, bracket_match.entrant_b_id
            )
            rounds.setdefault(bracket_match.round_number, []).append(
                (bracket_match, a_label, b_label)
            )

        return build_bracket_embed(tournament=tournament, rounds=rounds)

    async def _entrant_label(
        self,
        entrant_repo: TournamentEntrantRepository,
        members_repo: ShaheenMemberRepository,
        guild: discord.Guild | None,
        entrant_id: int | None,
    ) -> str:
        if entrant_id is None:
            return "TBD"
        member_ids = await entrant_repo.members_of(entrant_id)
        names = []
        for shaheen_member_id in member_ids:
            discord_id = await members_repo.get_discord_id(shaheen_member_id)
            names.append(_display_name(guild, discord_id) if discord_id else "Unknown")
        return " & ".join(names) if names else "TBD"


def _require_member(interaction: discord.Interaction) -> discord.Member:
    member = interaction.user
    if not isinstance(member, discord.Member) or interaction.guild is None:
        raise ShaheenError("This command can only be used inside the Shaheen server.")
    return member


def _display_name(guild: discord.Guild | None, discord_id: int) -> str:
    if guild is None:
        return f"<@{discord_id}>"
    member = guild.get_member(discord_id)
    return member.display_name if member else f"<@{discord_id}>"


async def setup(bot: ShaheenBot) -> None:
    await bot.add_cog(CompetitionCog(bot))
