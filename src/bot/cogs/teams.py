"""/team — teams in the BRAWLISTAN network (docs/DECISIONS.md ADR-114).

Thin: rules live in services/team_service.py. Staff create teams and name
captains; staff or the team's own captain change its roster; anyone can look
a team up or leave their own. Teams are not Discord roles.
"""

from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from bot.checks.permissions import check_staff_authorized, require_staff_authorized
from bot.client import ShaheenBot
from bot.content.team_embeds import build_team_embed, team_view
from core.exceptions import NotFoundError, ShaheenError
from database.session import session_scope
from services.link_service import LinkService
from services.team_service import TeamService


def _member(interaction: discord.Interaction) -> discord.Member:
    member = interaction.user
    if not isinstance(member, discord.Member):
        raise ShaheenError("This command can only be used inside the BRAWLISTAN server.")
    return member


class TeamsCog(commands.Cog):
    def __init__(self, bot: ShaheenBot) -> None:
        self.bot = bot

    team = app_commands.Group(name="team", description="Teams in the BRAWLISTAN network")

    def _is_staff(self, member: discord.Member) -> bool:
        return check_staff_authorized(member, self.bot.settings.bot_owner_id)

    async def _player_id(
        self, guild_id: int, user: discord.Member | None, brawlhalla_id: int | None
    ) -> int:
        """The Brawlhalla id to act on: a linked member's, or the one given."""
        if user is not None:
            async with session_scope(self.bot.session_factory) as session:
                link = await LinkService(session, self.bot.brawlhalla).get_active_link(
                    guild_id=guild_id, discord_id=user.id
                )
            if link is None:
                raise ShaheenError(f"{user.display_name} hasn't linked a Brawlhalla account.")
            return link[1].brawlhalla_player_id
        if brawlhalla_id is None:
            raise ShaheenError("Pick a member or give a Brawlhalla ID.")
        return brawlhalla_id

    async def _team_names(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        if interaction.guild is None:
            return []
        async with session_scope(self.bot.session_factory) as session:
            teams = await TeamService(session).all_teams(interaction.guild.id)
        needle = current.lower()
        return [
            app_commands.Choice(name=f"{t.name} [{t.tag}]", value=t.slug)
            for t in teams
            if needle in t.name.lower() or needle in t.tag.lower()
        ][:25]

    # --- anyone ------------------------------------------------------------------

    @team.command(name="info", description="A team's roster and rating")
    @app_commands.describe(name="The team (defaults to yours)")
    async def info(self, interaction: discord.Interaction, name: str | None = None) -> None:
        member = _member(interaction)
        await interaction.response.defer(ephemeral=True)
        async with session_scope(self.bot.session_factory) as session:
            service = TeamService(session)
            if name:
                slug = (await service.get(member.guild.id, name)).slug
            else:
                link = await LinkService(session, self.bot.brawlhalla).get_active_link(
                    guild_id=member.guild.id, discord_id=member.id
                )
                mine = await service.teams_of(member.guild.id, [link[1].id]) if link else {}
                if not mine:
                    raise NotFoundError("You're not on a team. Name one to look it up.")
                slug = next(iter(mine.values())).slug
            detail = await service.detail(member.guild.id, slug)
        if detail is None:
            raise NotFoundError("No such team.")
        site = self.bot.settings.site_url
        await interaction.followup.send(
            embed=build_team_embed(detail.summary, detail.roster, site_url=site),
            view=team_view(site, slug),
            ephemeral=True,
        )

    info.autocomplete("name")(_team_names)

    @team.command(name="leave", description="Leave your team")
    async def leave(self, interaction: discord.Interaction) -> None:
        member = _member(interaction)
        await interaction.response.defer(ephemeral=True)
        async with session_scope(self.bot.session_factory) as session:
            link = await LinkService(session, self.bot.brawlhalla).get_active_link(
                guild_id=member.guild.id, discord_id=member.id
            )
            if link is None:
                raise ShaheenError("Link your Brawlhalla account first (/link).")
            left = await TeamService(session).leave(
                guild_id=member.guild.id, player=link[1], actor_discord_id=member.id
            )
            name = left.name
        await interaction.followup.send(f"You've left **{name}**.", ephemeral=True)

    # --- staff or captain --------------------------------------------------------

    @team.command(name="add", description="Add a player to a team (staff or its captain)")
    @app_commands.describe(
        name="The team", user="A linked member", brawlhalla_id="Or a tracked player's ID"
    )
    async def add(
        self,
        interaction: discord.Interaction,
        name: str,
        user: discord.Member | None = None,
        brawlhalla_id: app_commands.Range[int, 1, 10**12] | None = None,
    ) -> None:
        member = _member(interaction)
        await interaction.response.defer(ephemeral=True)
        bid = await self._player_id(member.guild.id, user, brawlhalla_id)
        async with session_scope(self.bot.session_factory) as session:
            service = TeamService(session)
            team = await service.get(member.guild.id, name)
            player = await service.add_member(
                team, brawlhalla_id=bid, actor_discord_id=member.id, is_staff=self._is_staff(member)
            )
            message = f"**{player.player_name}** joined **{team.name}**."
        await interaction.followup.send(message, ephemeral=True)

    add.autocomplete("name")(_team_names)

    @team.command(name="remove", description="Remove a player from a team (staff or its captain)")
    @app_commands.describe(
        name="The team", user="A linked member", brawlhalla_id="Or a tracked player's ID"
    )
    async def remove(
        self,
        interaction: discord.Interaction,
        name: str,
        user: discord.Member | None = None,
        brawlhalla_id: app_commands.Range[int, 1, 10**12] | None = None,
    ) -> None:
        member = _member(interaction)
        await interaction.response.defer(ephemeral=True)
        bid = await self._player_id(member.guild.id, user, brawlhalla_id)
        async with session_scope(self.bot.session_factory) as session:
            service = TeamService(session)
            team = await service.get(member.guild.id, name)
            player = await service.remove_member(
                team, brawlhalla_id=bid, actor_discord_id=member.id, is_staff=self._is_staff(member)
            )
            message = f"**{player.player_name}** left **{team.name}**."
        await interaction.followup.send(message, ephemeral=True)

    remove.autocomplete("name")(_team_names)

    # --- staff -------------------------------------------------------------------

    @team.command(name="create", description="Create a team (staff)")
    @app_commands.describe(name="Team name", tag="2–6 letter tag, e.g. DE", description="One line")
    @require_staff_authorized()
    async def create(
        self,
        interaction: discord.Interaction,
        name: app_commands.Range[str, 2, 40],
        tag: app_commands.Range[str, 2, 6],
        description: app_commands.Range[str, 1, 280] | None = None,
    ) -> None:
        member = _member(interaction)
        await interaction.response.defer(ephemeral=True)
        async with session_scope(self.bot.session_factory) as session:
            team = await TeamService(session).create(
                guild_id=member.guild.id,
                name=name,
                tag=tag,
                description=description,
                actor_discord_id=member.id,
            )
            message = (
                f"Created **{team.name} [{team.tag}]**. Add players with `/team add`, then name "
                "a captain with `/team captain`. Send the logo to the site owner to add it."
            )
        await interaction.followup.send(message, ephemeral=True)

    @team.command(name="captain", description="Name a team's captain (staff)")
    @app_commands.describe(
        name="The team", user="A linked member", brawlhalla_id="Or a tracked player's ID"
    )
    @require_staff_authorized()
    async def captain(
        self,
        interaction: discord.Interaction,
        name: str,
        user: discord.Member | None = None,
        brawlhalla_id: app_commands.Range[int, 1, 10**12] | None = None,
    ) -> None:
        member = _member(interaction)
        await interaction.response.defer(ephemeral=True)
        bid = await self._player_id(member.guild.id, user, brawlhalla_id)
        async with session_scope(self.bot.session_factory) as session:
            service = TeamService(session)
            team = await service.get(member.guild.id, name)
            player = await service.set_captain(team, brawlhalla_id=bid, actor_discord_id=member.id)
            message = (
                f"👑 **{player.player_name}** captains **{team.name}** and can now add and "
                "remove its players."
            )
        await interaction.followup.send(message, ephemeral=True)

    captain.autocomplete("name")(_team_names)


async def setup(bot: ShaheenBot) -> None:
    await bot.add_cog(TeamsCog(bot))
