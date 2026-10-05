"""Teams (docs/DECISIONS.md ADR-114): rules for creating teams and managing
rosters, and the numbers the Teams pages show.

No Discord here. The bot passes in who is acting and whether they're staff;
the website reads the same overview and detail. A team's numbers come only
from stored readings, so a team with nobody placed has no team rating
rather than a made-up one.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import ConflictError, NotFoundError, PermissionDeniedError, ShaheenError
from database.models.achievement import Achievement
from database.models.brawlhalla_player import BrawlhallaPlayer
from database.models.ranking_snapshot import RankingSnapshot
from database.models.team import Team, TeamMember
from database.repositories.audit_log_repository import AuditLogRepository
from database.repositories.brawlhalla_player_repository import BrawlhallaPlayerRepository
from database.repositories.legend_snapshot_repository import LegendSnapshotRepository
from database.repositories.member_achievement_repository import MemberAchievementRepository
from database.repositories.member_player_link_repository import MemberPlayerLinkRepository
from database.repositories.ranking_snapshot_repository import RankingSnapshotRepository
from database.repositories.team_repository import TeamRepository
from services.report_service import clean_text

TEAM_RATING_SIZE = 3  # a team's rating is the average of its best 3 placed players
MAX_ROSTER = 20
_NON_SLUG = re.compile(r"[^a-z0-9]+")
_TAG = re.compile(r"^[A-Z0-9]{2,6}$")
_HEX = re.compile(r"^#?([0-9a-fA-F]{6})$")


def hex_colour(value: str | None) -> str | None:
    """'3DF26E' or '#3df26e' -> '#3df26e'; None stays None; anything else is rejected."""
    if value is None or not value.strip():
        return None
    match = _HEX.match(value.strip())
    if match is None:
        raise ShaheenError("Colours are hex codes like #3df26e.")
    return "#" + match.group(1).lower()


def team_slug(name: str) -> str:
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    return _NON_SLUG.sub("-", ascii_name.lower()).strip("-")[:48].strip("-")


def _rating_of(entry: RosterEntry) -> int:
    return (entry.snapshot.rating if entry.snapshot else None) or 0


def team_rating(ratings: Sequence[int | None]) -> int | None:
    """Average of the best TEAM_RATING_SIZE placed ratings; None if nobody's placed."""
    placed = sorted((r for r in ratings if r is not None), reverse=True)[:TEAM_RATING_SIZE]
    return round(sum(placed) / len(placed)) if placed else None


@dataclass
class RosterEntry:
    member: TeamMember
    player: BrawlhallaPlayer
    snapshot: RankingSnapshot | None
    main_legend: str | None


@dataclass
class TeamSummary:
    team: Team
    members: int
    rating: int | None
    best: RosterEntry | None
    # Position among teams with a team rating, best first; None when unrated.
    rank: int | None = None


@dataclass
class SeasonResult:
    season: int
    best: int | None
    average: int | None
    players: int


@dataclass
class TeamDetail:
    summary: TeamSummary
    roster: list[RosterEntry] = field(default_factory=list)
    achievements: list[tuple[str, Achievement, datetime]] = field(default_factory=list)
    seasons: list[SeasonResult] = field(default_factory=list)

    @property
    def captain(self) -> RosterEntry | None:
        return next((e for e in self.roster if e.member.role == "captain"), None)


class TeamService:
    def __init__(self, session: AsyncSession) -> None:
        self._teams = TeamRepository(session)
        self._players = BrawlhallaPlayerRepository(session)
        self._ranking = RankingSnapshotRepository(session)
        self._legends = LegendSnapshotRepository(session)
        self._links = MemberPlayerLinkRepository(session)
        self._achievements = MemberAchievementRepository(session)
        self._audit = AuditLogRepository(session)

    # --- lookups --------------------------------------------------------------

    async def get(self, guild_id: int, name_or_slug: str) -> Team:
        team = await self._teams.find(guild_id, name_or_slug)
        if team is None:
            raise NotFoundError(f"No team called {name_or_slug!r}.")
        return team

    async def all_teams(self, guild_id: int) -> list[Team]:
        return await self._teams.list_for_guild(guild_id)

    async def teams_of(self, guild_id: int, player_ids: list[int]) -> dict[int, Team]:
        return await self._teams.teams_of(guild_id, player_ids)

    # --- management -------------------------------------------------------------

    async def create(
        self,
        *,
        guild_id: int,
        name: str,
        tag: str,
        actor_discord_id: int,
        description: str | None = None,
        accent: str | None = None,
        accent_secondary: str | None = None,
    ) -> Team:
        clean_name = clean_text(name, limit=40)
        clean_tag = clean_text(tag, limit=16).upper().replace(" ", "")  # validated below
        slug = team_slug(clean_name)
        if len(clean_name) < 2 or not slug:
            raise ShaheenError("Give the team a name of at least 2 letters.")
        if not _TAG.match(clean_tag):
            raise ShaheenError("A tag is 2–6 letters or digits, like DE.")
        for existing in await self._teams.list_for_guild(guild_id):
            if existing.slug == slug or existing.tag.upper() == clean_tag:
                raise ConflictError(
                    f"A team called {existing.name} ({existing.tag}) exists already."
                )
        team = await self._teams.add(
            Team(
                guild_id=guild_id,
                slug=slug,
                name=clean_name,
                tag=clean_tag,
                description=clean_text(description, limit=280) if description else None,
                accent=hex_colour(accent),
                accent_secondary=hex_colour(accent_secondary),
            )
        )
        await self._log(guild_id, "team.create", actor_discord_id, f"{team.name} ({team.tag})")
        return team

    async def can_manage(self, team: Team, *, discord_id: int, is_staff: bool) -> bool:
        """Staff manage every team; a captain manages their own (ADR-114)."""
        if is_staff:
            return True
        captain = next(
            (p for m, p in await self._teams.active_members(team.id) if m.role == "captain"),
            None,
        )
        if captain is None:
            return False
        # The captain's player must be linked to this very Discord account.
        links = {
            player.id: did
            for _m, player, did in await self._links.list_active_for_guild(team.guild_id)
        }
        return links.get(captain.id) == discord_id

    async def add_member(
        self,
        team: Team,
        *,
        brawlhalla_id: int,
        actor_discord_id: int,
        is_staff: bool,
        now: datetime | None = None,
    ) -> BrawlhallaPlayer:
        await self._require_manager(team, actor_discord_id, is_staff)
        player = await self._tracked(brawlhalla_id)
        current = await self._teams.active_membership(player.id)
        if current is not None:
            _member, other = current
            if other.id == team.id:
                raise ConflictError(f"{player.player_name} is already on {team.name}.")
            raise ConflictError(
                f"{player.player_name} plays for {other.name}. They need to leave it (or be "
                "removed) first."
            )
        if len(await self._teams.active_members(team.id)) >= MAX_ROSTER:
            raise ShaheenError(f"A roster holds at most {MAX_ROSTER} players.")
        await self._teams.add_member(
            team_id=team.id, player_id=player.id, role="player", joined_at=now or datetime.now(UTC)
        )
        await self._log(
            team.guild_id, "team.add", actor_discord_id, f"{player.player_name} -> {team.name}"
        )
        return player

    async def remove_member(
        self,
        team: Team,
        *,
        brawlhalla_id: int,
        actor_discord_id: int,
        is_staff: bool,
        now: datetime | None = None,
    ) -> BrawlhallaPlayer:
        await self._require_manager(team, actor_discord_id, is_staff)
        player = await self._tracked(brawlhalla_id)
        membership = await self._teams.active_membership(player.id)
        if membership is None or membership[1].id != team.id:
            raise NotFoundError(f"{player.player_name} isn't on {team.name}.")
        await self._teams.close(membership[0], now or datetime.now(UTC))
        await self._log(
            team.guild_id, "team.remove", actor_discord_id, f"{player.player_name} <- {team.name}"
        )
        return player

    async def leave(
        self, *, guild_id: int, player: BrawlhallaPlayer, actor_discord_id: int
    ) -> Team:
        membership = await self._teams.active_membership(player.id)
        if membership is None or membership[1].guild_id != guild_id:
            raise NotFoundError("You're not on a team.")
        member, team = membership
        await self._teams.close(member, datetime.now(UTC))
        await self._log(
            guild_id, "team.leave", actor_discord_id, f"{player.player_name} <- {team.name}"
        )
        return team

    async def set_show_tag(
        self, *, guild_id: int, player: BrawlhallaPlayer, show: bool, actor_discord_id: int
    ) -> Team:
        """A player's own choice to wear their team tag (ADR-115)."""
        membership = await self._teams.active_membership(player.id)
        if membership is None or membership[1].guild_id != guild_id:
            raise NotFoundError("You're not on a team, so there's no tag to show.")
        member, team = membership
        member.show_tag = show
        await self._log(
            guild_id,
            "team.tag",
            actor_discord_id,
            f"{player.player_name} [{team.tag}] {'on' if show else 'off'}",
        )
        return team

    async def set_captain(
        self, team: Team, *, brawlhalla_id: int, actor_discord_id: int
    ) -> BrawlhallaPlayer:
        """Staff only (the cog checks). The captain must already be on the roster;
        the previous captain becomes a player."""
        player = await self._tracked(brawlhalla_id)
        members = await self._teams.active_members(team.id)
        target = next((m for m, p in members if p.id == player.id), None)
        if target is None:
            raise NotFoundError(f"Add {player.player_name} to {team.name} first.")
        for member, _p in members:
            member.role = "captain" if member is target else "player"
        await self._log(
            team.guild_id, "team.captain", actor_discord_id, f"{player.player_name} @ {team.name}"
        )
        return player

    # --- the Teams pages -------------------------------------------------------

    async def overview(self, guild_id: int) -> list[TeamSummary]:
        """Every team: the founding team first, then by team rating, then name."""
        summaries = [
            await self._summary(team, await self._roster(team))
            for team in await self._teams.list_for_guild(guild_id)
        ]
        summaries.sort(
            key=lambda s: (not s.team.is_founding, -(s.rating or 0), s.team.name.lower())
        )
        rated = sorted(
            (s for s in summaries if s.rating is not None), key=lambda s: -(s.rating or 0)
        )
        for position, summary in enumerate(rated, start=1):
            summary.rank = position
        return summaries

    async def detail(self, guild_id: int, slug: str) -> TeamDetail | None:
        team = await self._teams.get_by_slug(guild_id, slug)
        if team is None:
            return None
        roster = await self._roster(team)
        summary = await self._summary(team, roster)
        summary.rank = next(
            (s.rank for s in await self.overview(guild_id) if s.team.id == team.id), None
        )
        detail = TeamDetail(summary=summary, roster=roster)

        members_by_player = {
            player.id: member
            for member, player, _d in await self._links.list_active_for_guild(guild_id)
        }
        for entry in roster:
            shaheen_member = members_by_player.get(entry.player.id)
            if shaheen_member is None:
                continue
            for achievement, at in await self._achievements.list_with_details(shaheen_member.id):
                detail.achievements.append((entry.player.player_name, achievement, at))
        detail.achievements.sort(key=lambda row: row[2], reverse=True)

        per_season: dict[int, list[int]] = {}
        for entry in roster:
            for season, final, _peak, _n in await self._ranking.season_summaries(entry.player.id):
                if final is not None:
                    per_season.setdefault(season, []).append(final)
        detail.seasons = [
            SeasonResult(
                season=season,
                best=max(ratings),
                average=team_rating(ratings),
                players=len(ratings),
            )
            for season, ratings in sorted(per_season.items(), reverse=True)
        ]
        return detail

    # --- internals ---------------------------------------------------------------

    async def _roster(self, team: Team) -> list[RosterEntry]:
        season = await self._ranking.current_season()
        roster = []
        for member, player in await self._teams.active_members(team.id):
            snapshot = (
                await self._ranking.get_latest(player.id, season=season)
                if season is not None
                else None
            )
            legends = await self._legends.list_latest_per_legend(player.id)
            main = max(legends, key=lambda legend: legend.games, default=None)
            roster.append(
                RosterEntry(
                    member=member,
                    player=player,
                    snapshot=snapshot,
                    main_legend=main.legend_name_key if main and main.games > 0 else None,
                )
            )
        # Captain first, then best rating.
        roster.sort(
            key=lambda e: (
                e.member.role != "captain",
                -((e.snapshot.rating if e.snapshot else None) or 0),
                e.player.player_name.lower(),
            )
        )
        return roster

    async def _summary(self, team: Team, roster: list[RosterEntry]) -> TeamSummary:
        ratings = [e.snapshot.rating if e.snapshot else None for e in roster]
        placed = [e for e in roster if e.snapshot and e.snapshot.rating is not None]
        best = max(placed, key=_rating_of) if placed else None
        return TeamSummary(team=team, members=len(roster), rating=team_rating(ratings), best=best)

    async def _tracked(self, brawlhalla_id: int) -> BrawlhallaPlayer:
        player = await self._players.get_by_brawlhalla_id(brawlhalla_id)
        if player is None:
            raise NotFoundError(
                "That player isn't tracked by BRAWLISTAN yet — they need to /link or be added "
                "to the Pakistan rankings first."
            )
        return player

    async def _require_manager(self, team: Team, discord_id: int, is_staff: bool) -> None:
        if not await self.can_manage(team, discord_id=discord_id, is_staff=is_staff):
            raise PermissionDeniedError(
                f"Only staff or {team.name}'s captain can change its roster."
            )

    async def _log(self, guild_id: int, action: str, actor: int, subject: str) -> None:
        await self._audit.add(
            guild_id=guild_id,
            action=action,
            source="discord",
            actor_discord_id=actor,
            subject=subject,
        )
