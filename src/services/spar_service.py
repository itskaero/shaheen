"""Looking-for-game support (docs/DECISIONS.md ADR-136).

The rules a spar call follows, kept out of Discord: who's asking (their
linked rating, tier and main Legend for the card), whether the opt-in Spar
Ping role may be pinged yet (one ping per guild per cooldown, so a busy
evening doesn't turn the role into spam), and cleaning the optional note.
Discord-free.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from database.models.brawlhalla_player import BrawlhallaPlayer
from database.repositories.brawlhalla_player_repository import BrawlhallaPlayerRepository
from database.repositories.discord_user_repository import DiscordUserRepository
from database.repositories.guild_settings_repository import GuildSettingsRepository
from database.repositories.legend_snapshot_repository import LegendSnapshotRepository
from database.repositories.member_player_link_repository import MemberPlayerLinkRepository
from database.repositories.ranking_snapshot_repository import RankingSnapshotRepository
from database.repositories.shaheen_member_repository import ShaheenMemberRepository
from database.repositories.team_repository import TeamRepository
from services.cities import CITIES

PING_COOLDOWN = timedelta(minutes=10)
NOTE_MAX = 80
# Mentions and links don't belong in a spar note.
_STRIP = re.compile(r"<[@#][!&]?\d+>|@(everyone|here)|https?://\S+", re.IGNORECASE)


@dataclass(frozen=True)
class SparProfile:
    """What the spar card shows about whoever's looking."""

    player_name: str
    brawlhalla_id: int
    rating: int | None = None
    tier: str | None = None
    rating_2v2: int | None = None
    tier_2v2: str | None = None
    region: str | None = None
    main_legend: str | None = None
    city: str | None = None
    team_tag: str | None = None


def clean_note(text: str | None) -> str | None:
    """One line, no mentions or links, at most NOTE_MAX characters."""
    if not text:
        return None
    note = " ".join(_STRIP.sub("", text).split())
    if len(note) > NOTE_MAX:
        note = note[: NOTE_MAX - 1].rstrip() + "…"
    return note or None


def ping_allowed(
    last_ping_at: datetime | None, now: datetime, cooldown: timedelta = PING_COOLDOWN
) -> bool:
    if last_ping_at is None:
        return True
    last = last_ping_at if last_ping_at.tzinfo else last_ping_at.replace(tzinfo=UTC)
    return now - last >= cooldown


class SparService:
    def __init__(self, session: AsyncSession, *, cooldown: timedelta = PING_COOLDOWN) -> None:
        self._settings = GuildSettingsRepository(session)
        self._discord_users = DiscordUserRepository(session)
        self._members = ShaheenMemberRepository(session)
        self._links = MemberPlayerLinkRepository(session)
        self._players = BrawlhallaPlayerRepository(session)
        self._ranking = RankingSnapshotRepository(session)
        self._legends = LegendSnapshotRepository(session)
        self._teams = TeamRepository(session)
        self._cooldown = cooldown

    async def profile(self, guild_id: int, discord_id: int) -> SparProfile | None:
        """The linked player's card details; None if they haven't linked."""
        player = await self._linked_player(guild_id, discord_id)
        if player is None:
            return None
        season = await self._ranking.current_season()
        latest = await self._ranking.get_latest(player.id, season=season) if season else None
        legends = await self._legends.list_latest_per_legend(player.id)
        main = max(legends, key=lambda legend: legend.games, default=None)
        membership = await self._teams.active_membership(player.id)
        return SparProfile(
            player_name=player.player_name,
            brawlhalla_id=player.brawlhalla_player_id,
            rating=latest.rating if latest else None,
            tier=latest.tier if latest else None,
            rating_2v2=latest.rating_2v2 if latest else None,
            tier_2v2=latest.tier_2v2 if latest else None,
            region=(latest.region if latest else None) or player.region,
            main_legend=main.legend_name_key if main and main.games > 0 else None,
            city=CITIES.get(player.city or ""),
            team_tag=membership[1].tag if membership else None,
        )

    async def spar_role_id(self, guild_id: int) -> int | None:
        settings = await self._settings.get(guild_id)
        return settings.spar_role_id if settings else None

    async def set_spar_role(self, guild_id: int, role_id: int) -> None:
        await self._settings.set_spar_ping(guild_id, role_id=role_id)

    async def claim_ping(self, guild_id: int, *, now: datetime | None = None) -> bool:
        """True (and the cooldown starts) if the Spar Ping role may be pinged now."""
        now = now or datetime.now(UTC)
        settings = await self._settings.get(guild_id)
        if not ping_allowed(settings.spar_last_ping_at if settings else None, now, self._cooldown):
            return False
        await self._settings.set_spar_ping(guild_id, last_ping_at=now)
        return True

    async def _linked_player(self, guild_id: int, discord_id: int) -> BrawlhallaPlayer | None:
        discord_user = await self._discord_users.get_by_discord_id(discord_id)
        if discord_user is None:
            return None
        member = await self._members.get(discord_user_id=discord_user.id, guild_id=guild_id)
        if member is None:
            return None
        link = await self._links.get_active(member.id)
        return await self._players.get_by_id(link.brawlhalla_player_id) if link else None
