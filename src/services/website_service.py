"""Read-only queries for the public website/API (docs/DECISIONS.md ADR-042).

Discord-agnostic, like every other service (docs/ARCHITECTURE.md). Never
reads or returns Discord identity — see ADR-040: only BrawlhallaPlayer
identity is public-facing here.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from core.brand import MOTTO, NAME, TAGLINE
from database.models.achievement import Achievement
from database.models.brawlhalla_player import BrawlhallaPlayer
from database.models.match import MatchSide, MatchStatus
from database.models.ranking_snapshot import RankingSnapshot
from database.repositories.brawlhalla_player_repository import BrawlhallaPlayerRepository
from database.repositories.chat_activity_repository import ChatActivityRepository
from database.repositories.legend_snapshot_repository import LegendSnapshotRepository
from database.repositories.match_repository import MatchRepository
from database.repositories.member_achievement_repository import MemberAchievementRepository
from database.repositories.member_player_link_repository import MemberPlayerLinkRepository
from database.repositories.ranking_snapshot_repository import RankingSnapshotRepository
from database.repositories.shaheen_member_repository import ShaheenMemberRepository
from database.repositories.tournament_repository import (
    TournamentEntrantRepository,
    TournamentMatchRepository,
    TournamentRepository,
)
from services.chat_gamification import level_for_xp, rank_title_for_level


@dataclass
class ClanInfo:
    name: str
    motto: str
    tagline: str
    member_count: int


@dataclass
class LeaderboardEntry:
    player: BrawlhallaPlayer
    snapshot: RankingSnapshot


@dataclass
class PlayerProfile:
    player: BrawlhallaPlayer
    latest_ranking: RankingSnapshot | None
    achievements: list[tuple[Achievement, datetime]]

    @property
    def global_rank(self) -> int | None:
        """Already captured on every RankingSnapshot (docs/DECISIONS.md
        ADR-066) but never surfaced publicly until now — no new snapshot
        field, just exposing what's already stored.
        """
        return self.latest_ranking.global_rank if self.latest_ranking else None


@dataclass
class LegendMastery:
    legend_name_key: str
    games: int
    wins: int
    kos: int
    damagedealt: int
    falls: int


@dataclass
class MatchResult:
    kind: str
    opponents: list[str]
    won: bool
    confirmed_at: datetime


@dataclass
class BracketEntrant:
    id: int
    seed: int | None
    names: list[str]
    eliminated: bool


@dataclass
class BracketMatch:
    round_number: int
    slot_index: int
    entrant_a: BracketEntrant | None
    entrant_b: BracketEntrant | None
    winner_entrant_id: int | None
    status: str


@dataclass
class TournamentSummary:
    id: int
    name: str
    kind: str
    status: str
    started_at: datetime | None
    completed_at: datetime | None


@dataclass
class TournamentBracket:
    tournament: TournamentSummary
    entrants: list[BracketEntrant]
    matches: list[BracketMatch]


@dataclass
class CommunityActivityEntry:
    player_name: str
    level: int
    rank_title: str
    xp: int


class WebsiteService:
    def __init__(self, session: AsyncSession) -> None:
        self._links = MemberPlayerLinkRepository(session)
        self._members = ShaheenMemberRepository(session)
        self._players = BrawlhallaPlayerRepository(session)
        self._ranking = RankingSnapshotRepository(session)
        self._awards = MemberAchievementRepository(session)
        self._legends = LegendSnapshotRepository(session)
        self._matches = MatchRepository(session)
        self._tournaments = TournamentRepository(session)
        self._entrants = TournamentEntrantRepository(session)
        self._tournament_matches = TournamentMatchRepository(session)
        self._chat_activity = ChatActivityRepository(session)

    async def get_clan_info(self, guild_id: int) -> ClanInfo:
        member_count = await self._members.count_for_guild(guild_id)
        return ClanInfo(name=NAME, motto=MOTTO, tagline=TAGLINE, member_count=member_count)

    async def get_leaderboard(self, guild_id: int, *, limit: int = 10) -> list[LeaderboardEntry]:
        entries: list[LeaderboardEntry] = []
        for _member, player, _discord_id in await self._links.list_active_for_guild(guild_id):
            latest = await self._ranking.get_latest(player.id)
            if latest is not None:
                entries.append(LeaderboardEntry(player=player, snapshot=latest))
        entries.sort(
            key=lambda entry: entry.snapshot.rating if entry.snapshot.rating is not None else -1,
            reverse=True,
        )
        return entries[:limit]

    async def get_community_activity(
        self, guild_id: int, *, limit: int = 10
    ) -> list[CommunityActivityEntry]:
        """Chat-XP leaderboard, filtered to actively-linked members only
        and showing their Brawlhalla player name — never a Discord handle
        (docs/DECISIONS.md ADR-065, holding the same identity boundary as
        every other method here, ADR-040). A member who chats a lot but
        hasn't run /link still earns XP (visible via /chatboard in
        Discord) but doesn't appear on the public site, same as any other
        unlinked member's data.
        """
        entries: list[CommunityActivityEntry] = []
        for _member, player, discord_id in await self._links.list_active_for_guild(guild_id):
            activity = await self._chat_activity.get(guild_id=guild_id, discord_id=discord_id)
            if activity is None or activity.xp == 0:
                continue
            # Derived live from xp, not the stored `level` column — that
            # column is only updated on a detected level-up (bot/cogs/
            # engagement.py), so trusting it here could show a stale
            # value if it and xp ever drift apart. xp is the single
            # source of truth; level_for_xp is cheap and pure.
            level = level_for_xp(activity.xp)
            entries.append(
                CommunityActivityEntry(
                    player_name=player.player_name,
                    level=level,
                    rank_title=rank_title_for_level(level),
                    xp=activity.xp,
                )
            )
        entries.sort(key=lambda entry: entry.xp, reverse=True)
        return entries[:limit]

    async def get_player_profile(self, brawlhalla_player_id: int) -> PlayerProfile | None:
        player = await self._players.get_by_brawlhalla_id(brawlhalla_player_id)
        if player is None:
            return None

        latest = await self._ranking.get_latest(player.id)

        achievements: list[tuple[Achievement, datetime]] = []
        active_link = await self._links.get_active_by_player(player.id)
        if active_link is not None:
            achievements = await self._awards.list_with_details(active_link.shaheen_member_id)

        return PlayerProfile(player=player, latest_ranking=latest, achievements=achievements)

    async def get_player_history(
        self, brawlhalla_player_id: int, *, limit: int = 10
    ) -> list[RankingSnapshot] | None:
        player = await self._players.get_by_brawlhalla_id(brawlhalla_player_id)
        if player is None:
            return None
        return await self._ranking.list_recent(player.id, limit=limit)

    async def get_player_legends(
        self, brawlhalla_player_id: int, *, limit: int = 6
    ) -> list[LegendMastery] | None:
        player = await self._players.get_by_brawlhalla_id(brawlhalla_player_id)
        if player is None:
            return None
        snapshots = await self._legends.list_latest_per_legend(player.id)
        return [
            LegendMastery(
                legend_name_key=s.legend_name_key,
                games=s.games,
                wins=s.wins,
                kos=s.kos,
                damagedealt=s.damagedealt,
                falls=s.falls,
            )
            for s in snapshots[:limit]
        ]

    async def get_player_matches(
        self, brawlhalla_player_id: int, *, limit: int = 10
    ) -> list[MatchResult] | None:
        """Recent CONFIRMED matches for this player (ADR-033/034) — pending,
        disputed, and cancelled matches stay internal, not public results.
        """
        player = await self._players.get_by_brawlhalla_id(brawlhalla_player_id)
        if player is None:
            return None
        link = await self._links.get_active_by_player(player.id)
        if link is None:
            return []

        member_id = link.shaheen_member_id
        results: list[MatchResult] = []
        for match in await self._matches.list_recent_for_member(member_id, limit=limit * 3):
            if match.status != MatchStatus.CONFIRMED or match.winning_side is None:
                continue
            my_side = await self._matches.is_participant(match.id, member_id)
            if my_side is None:
                continue
            opponent_side = MatchSide.B if my_side == MatchSide.A else MatchSide.A
            opponent_participants = await self._matches.participants_on_side(
                match.id, opponent_side
            )
            opponents = await self._resolve_member_names(
                [p.shaheen_member_id for p in opponent_participants]
            )
            results.append(
                MatchResult(
                    kind=match.kind.value,
                    opponents=opponents,
                    won=match.winning_side == my_side,
                    confirmed_at=match.confirmed_at or match.updated_at,
                )
            )
            if len(results) >= limit:
                break
        return results

    async def list_tournaments(self, guild_id: int, *, limit: int = 20) -> list[TournamentSummary]:
        tournaments = await self._tournaments.list_for_guild(guild_id, limit=limit)
        return [
            TournamentSummary(
                id=t.id,
                name=t.name,
                kind=t.kind.value,
                status=t.status.value,
                started_at=t.started_at,
                completed_at=t.completed_at,
            )
            for t in tournaments
        ]

    async def get_tournament_bracket(self, tournament_id: int) -> TournamentBracket | None:
        tournament = await self._tournaments.get(tournament_id)
        if tournament is None:
            return None

        entrant_map: dict[int, BracketEntrant] = {}
        for entrant in await self._entrants.list_for_tournament(tournament_id):
            member_ids = await self._entrants.members_of(entrant.id)
            names = await self._resolve_member_names(member_ids)
            entrant_map[entrant.id] = BracketEntrant(
                id=entrant.id,
                seed=entrant.seed,
                names=names or ["Unknown"],
                eliminated=entrant.eliminated,
            )

        matches = [
            BracketMatch(
                round_number=m.round_number,
                slot_index=m.slot_index,
                entrant_a=entrant_map.get(m.entrant_a_id) if m.entrant_a_id else None,
                entrant_b=entrant_map.get(m.entrant_b_id) if m.entrant_b_id else None,
                winner_entrant_id=m.winner_entrant_id,
                status=m.status.value,
            )
            for m in await self._tournament_matches.list_all(tournament_id)
        ]

        return TournamentBracket(
            tournament=TournamentSummary(
                id=tournament.id,
                name=tournament.name,
                kind=tournament.kind.value,
                status=tournament.status.value,
                started_at=tournament.started_at,
                completed_at=tournament.completed_at,
            ),
            entrants=list(entrant_map.values()),
            matches=matches,
        )

    async def _resolve_member_names(self, shaheen_member_ids: list[int]) -> list[str]:
        """ShaheenMember ids -> their linked Brawlhalla player names.

        Same identity boundary as everywhere else in this service (ADR-040):
        callers only ever learn a Brawlhalla player_name, never anything
        Discord-identifying. A member with no active link (or none at all)
        is silently skipped rather than surfacing an internal id.
        """
        names: list[str] = []
        for member_id in shaheen_member_ids:
            link = await self._links.get_active(member_id)
            if link is None:
                continue
            player = await self._players.get_by_id(link.brawlhalla_player_id)
            if player is not None:
                names.append(player.player_name)
        return names
