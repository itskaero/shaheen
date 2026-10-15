"""Coaching (docs/DECISIONS.md ADR-126): a coach directory and coaching
requests. Discord-agnostic, so the website reuses the same rules.

- **Who coaches** is the Coach role in Discord, set by hand. `sync()` mirrors
  its holders into `coaches`: new holders are added, holders who lost the
  role go inactive (their history stays), and each coach's linked Brawlhalla
  account is refreshed.
- **A coach's profile** (specialty, legends, availability, bio, accepting)
  is theirs to edit.
- **Requests**: a member asks a coach for help. A coach can only be asked by
  the same member once at a time, a member has at most three requests open,
  and an unanswered request lapses after a week. The coach (or staff)
  accepts or declines.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import ConflictError, NotFoundError, PermissionDeniedError, ShaheenError
from database.models.brawlhalla_player import BrawlhallaPlayer
from database.models.coaching import Coach, CoachingRequest
from database.models.ranking_snapshot import RankingSnapshot
from database.models.team import Team
from database.repositories.audit_log_repository import AuditLogRepository
from database.repositories.brawlhalla_player_repository import BrawlhallaPlayerRepository
from database.repositories.coaching_repository import CoachingRepository
from database.repositories.guild_settings_repository import GuildSettingsRepository
from database.repositories.member_player_link_repository import MemberPlayerLinkRepository
from database.repositories.ranking_snapshot_repository import RankingSnapshotRepository
from database.repositories.team_repository import TeamRepository
from services.legend_art import normalize_legend_key
from services.report_service import clean_text

MAX_OPEN_PER_STUDENT = 3
REQUEST_LIFETIME = timedelta(days=7)
MAX_LEGENDS = 3
MESSAGE_MIN, MESSAGE_MAX = 10, 280
_LEGEND_SHAPE = re.compile(r"^[a-z][a-z_]{1,23}$")


@dataclass(frozen=True)
class CoachingConfig:
    role_id: int | None = None
    channel_id: int | None = None


@dataclass(frozen=True)
class RoleHolder:
    """A member holding the Coach role, as the bot sees them."""

    discord_id: int
    display_name: str


@dataclass(frozen=True)
class SyncResult:
    added: int = 0
    reactivated: int = 0
    deactivated: int = 0

    @property
    def changed(self) -> bool:
        return bool(self.added or self.reactivated or self.deactivated)


@dataclass(frozen=True)
class CoachEntry:
    """One coach in the directory, with what the website shows."""

    coach: Coach
    player: BrawlhallaPlayer | None
    snapshot: RankingSnapshot | None
    team: Team | None
    sessions: int

    @property
    def legend_keys(self) -> list[str]:
        return parse_legends(self.coach.legends)


def parse_legends(raw: str | None) -> list[str]:
    """Stored "bodvar,lord_vraxx" -> ["bodvar", "lord_vraxx"]."""
    return [key for key in (raw or "").split(",") if key]


def clean_legends(raw: str) -> str | None:
    """Member input ("Bödvar, Lord Vraxx") -> stored keys, validated.
    An empty string clears the list."""
    keys: list[str] = []
    for part in raw.split(","):
        if not part.strip():
            continue
        key = normalize_legend_key(part)
        if not _LEGEND_SHAPE.match(key):
            raise ShaheenError(f"{part.strip()!r} doesn't look like a legend name.")
        if key not in keys:
            keys.append(key)
    if len(keys) > MAX_LEGENDS:
        raise ShaheenError(f"Pick up to {MAX_LEGENDS} legends.")
    return ",".join(keys) or None


def _optional_text(value: str, limit: int) -> str | None:
    return clean_text(value, limit=limit) or None


class CoachingService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = CoachingRepository(session)
        self._settings = GuildSettingsRepository(session)
        self._links = MemberPlayerLinkRepository(session)
        self._players = BrawlhallaPlayerRepository(session)
        self._ranking = RankingSnapshotRepository(session)
        self._teams = TeamRepository(session)
        self._audit = AuditLogRepository(session)

    # --- settings -----------------------------------------------------------

    async def config(self, guild_id: int) -> CoachingConfig:
        settings = await self._settings.get(guild_id)
        if settings is None:
            return CoachingConfig()
        return CoachingConfig(settings.coach_role_id, settings.coaching_channel_id)

    async def set_config(
        self, guild_id: int, *, role_id: int | None, channel_id: int | None, staff_discord_id: int
    ) -> CoachingConfig:
        await self._settings.set_coaching(
            guild_id, coach_role_id=role_id, coaching_channel_id=channel_id
        )
        await self._audit.add(
            guild_id=guild_id,
            action="coaching.setup",
            source="discord",
            actor_discord_id=staff_discord_id,
            subject="coach role and coaching channel",
            detail={"role_id": role_id, "channel_id": channel_id},
        )
        return CoachingConfig(role_id, channel_id)

    # --- the directory ------------------------------------------------------

    async def sync(self, guild_id: int, holders: Sequence[RoleHolder]) -> SyncResult:
        """Mirror the Coach role's holders (idempotent; writes only diffs)."""
        held = {h.discord_id: h for h in holders}
        linked = {
            discord_id: player.id
            for _member, player, discord_id in await self._links.list_active_for_guild(guild_id)
        }
        added = reactivated = deactivated = 0
        known = {c.discord_id: c for c in await self._repo.coaches(guild_id, active_only=False)}
        for discord_id, coach in known.items():
            holder = held.get(discord_id)
            if holder is None:
                if coach.active:
                    coach.active = False
                    deactivated += 1
                continue
            if not coach.active:
                coach.active = True
                reactivated += 1
            name = holder.display_name[:64]
            if coach.display_name != name:
                coach.display_name = name
            if coach.brawlhalla_player_id != linked.get(discord_id):
                coach.brawlhalla_player_id = linked.get(discord_id)
        for discord_id, holder in held.items():
            if discord_id in known:
                continue
            await self._repo.add_coach(
                Coach(
                    guild_id=guild_id,
                    discord_id=discord_id,
                    display_name=holder.display_name[:64],
                    brawlhalla_player_id=linked.get(discord_id),
                    accepting=True,
                    active=True,
                )
            )
            added += 1
        return SyncResult(added, reactivated, deactivated)

    async def coach_of(self, guild_id: int, discord_id: int) -> Coach | None:
        """The member's coach row, if they're an active coach."""
        coach = await self._repo.coach_by_discord(guild_id, discord_id)
        return coach if coach is not None and coach.active else None

    async def directory(self, guild_id: int) -> list[CoachEntry]:
        """Active coaches: accepting first, then most sessions, then rating."""
        coaches = await self._repo.coaches(guild_id)
        sessions = await self._repo.accepted_counts(c.id for c in coaches)
        season = await self._ranking.current_season()
        player_ids = [c.brawlhalla_player_id for c in coaches if c.brawlhalla_player_id]
        teams = await self._teams.teams_of(guild_id, player_ids)
        entries = []
        for coach in coaches:
            player = (
                await self._players.get_by_id(coach.brawlhalla_player_id)
                if coach.brawlhalla_player_id
                else None
            )
            snapshot = (
                await self._ranking.get_latest(player.id, season=season)
                if player is not None and season is not None
                else None
            )
            entries.append(
                CoachEntry(
                    coach=coach,
                    player=player,
                    snapshot=snapshot,
                    team=teams.get(player.id) if player else None,
                    sessions=sessions.get(coach.id, 0),
                )
            )
        entries.sort(
            key=lambda e: (
                not e.coach.accepting,
                -e.sessions,
                -((e.snapshot.rating if e.snapshot else None) or 0),
                e.coach.display_name.lower(),
            )
        )
        return entries

    async def update_profile(
        self,
        coach: Coach,
        *,
        specialty: str | None = None,
        legends: str | None = None,
        availability: str | None = None,
        bio: str | None = None,
        accepting: bool | None = None,
    ) -> Coach:
        """Change what's given; an empty string clears a field."""
        if specialty is not None:
            coach.specialty = _optional_text(specialty, 80)
        if legends is not None:
            coach.legends = clean_legends(legends)
        if availability is not None:
            coach.availability = _optional_text(availability, 80)
        if bio is not None:
            coach.bio = _optional_text(bio, 280)
        if accepting is not None:
            coach.accepting = accepting
        await self._audit.add(
            guild_id=coach.guild_id,
            action="coaching.profile",
            source="discord",
            actor_discord_id=coach.discord_id,
            subject="coach profile updated",
        )
        return coach

    # --- requests -----------------------------------------------------------

    async def request(
        self,
        *,
        guild_id: int,
        coach_discord_id: int,
        student_discord_id: int,
        message: str,
        now: datetime | None = None,
    ) -> tuple[CoachingRequest, Coach]:
        now = now or datetime.now(UTC)
        coach = await self.coach_of(guild_id, coach_discord_id)
        if coach is None:
            raise NotFoundError("That member isn't a coach. `/coach list` shows who is.")
        if coach.discord_id == student_discord_id:
            raise ShaheenError("You can't book a session with yourself.")
        if not coach.accepting:
            raise ConflictError(f"{coach.display_name} isn't taking new students right now.")
        text = clean_text(message, limit=MESSAGE_MAX)
        if len(text) < MESSAGE_MIN:
            raise ShaheenError(
                f"Tell the coach what you'd like help with (at least {MESSAGE_MIN} characters)."
            )
        since = now - REQUEST_LIFETIME
        mine = await self._repo.open_requests(
            guild_id, since=since, student_discord_id=student_discord_id
        )
        if any(r.coach_id == coach.id for r in mine):
            raise ConflictError(
                f"You already have a request open with {coach.display_name}. "
                "Give them a few days to answer."
            )
        if len(mine) >= MAX_OPEN_PER_STUDENT:
            raise ConflictError(
                f"You have {len(mine)} requests waiting. Wait for an answer before asking again."
            )
        request = await self._repo.add_request(
            CoachingRequest(
                guild_id=guild_id,
                coach_id=coach.id,
                student_discord_id=student_discord_id,
                message=text,
                status="open",
                created_at=now,
                updated_at=now,
            )
        )
        await self._audit.add(
            guild_id=guild_id,
            action="coaching.request",
            source="discord",
            actor_discord_id=student_discord_id,
            subject=f"coaching request #{request.id}",
            detail={"coach_id": coach.id},
        )
        return request, coach

    async def mark_posted(self, request: CoachingRequest, message_id: int) -> None:
        request.channel_message_id = message_id

    async def respond(
        self,
        *,
        request_id: int,
        actor_discord_id: int,
        accept: bool,
        is_staff: bool,
        now: datetime | None = None,
    ) -> tuple[CoachingRequest, Coach]:
        """The coach (or staff) accepts or declines an open request."""
        now = now or datetime.now(UTC)
        request = await self._repo.get_request(request_id)
        coach = await self._repo.get_coach(request.coach_id) if request else None
        if request is None or coach is None:
            raise NotFoundError("That coaching request no longer exists.")
        if actor_discord_id != coach.discord_id and not is_staff:
            raise PermissionDeniedError("Only the coach who was asked can answer this request.")
        if request.status != "open":
            raise ConflictError(f"This request was already {request.status}.")
        created = request.created_at
        if created.tzinfo is None:  # SQLite drops the zone
            created = created.replace(tzinfo=UTC)
        if created < now - REQUEST_LIFETIME:
            raise ConflictError("This request lapsed after a week. The student can ask again.")
        request.status = "accepted" if accept else "declined"
        request.responded_at = now
        await self._audit.add(
            guild_id=request.guild_id,
            action="coaching.accept" if accept else "coaching.decline",
            source="discord",
            actor_discord_id=actor_discord_id,
            subject=f"coaching request #{request.id}",
        )
        return request, coach

    async def open_for_coach(
        self, coach: Coach, *, now: datetime | None = None
    ) -> list[CoachingRequest]:
        now = now or datetime.now(UTC)
        return await self._repo.open_requests(
            coach.guild_id, since=now - REQUEST_LIFETIME, coach_id=coach.id
        )
