"""Weekly clan digest: top rating gains, top chatters, matches played, and
MVP of the Week (docs/DECISIONS.md ADR-070).

Read-only except for rotating the weekly chat-XP counter it reads —
services.chat_gamification's level curve is the model for "a derived value
computed from a stored counter," this is the model for "a stored counter
that periodically resets."
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from database.repositories.chat_activity_repository import ChatActivityRepository
from database.repositories.match_repository import MatchRepository
from database.repositories.member_player_link_repository import MemberPlayerLinkRepository
from database.repositories.ranking_snapshot_repository import RankingSnapshotRepository

_TOP_N = 3


@dataclass(frozen=True)
class RatingGain:
    discord_id: int
    player_name: str
    rating_gain: int


@dataclass(frozen=True)
class TopChatter:
    discord_id: int
    weekly_xp: int


@dataclass(frozen=True)
class WeeklyDigest:
    rating_gains: tuple[RatingGain, ...]
    top_chatters: tuple[TopChatter, ...]
    matches_played: int
    mvp_discord_id: int | None
    mvp_reason: str | None


class WeeklyDigestService:
    def __init__(self, session: AsyncSession) -> None:
        self._links = MemberPlayerLinkRepository(session)
        self._ranking = RankingSnapshotRepository(session)
        self._chat = ChatActivityRepository(session)
        self._matches = MatchRepository(session)

    async def build_and_rotate(self, guild_id: int, *, since: datetime) -> WeeklyDigest:
        """Builds the digest, then zeroes the weekly chat-XP counters it
        just read so next week starts empty. Not transactional with the
        Discord post that follows — same "best-effort community content,
        not a source of truth" posture as achievement/milestone
        announcements elsewhere in this codebase: a failed post doesn't
        roll the counters back.
        """
        rating_gains = await self._rating_gains(guild_id, since)
        chatters = await self._chat.list_top_weekly(guild_id, limit=_TOP_N)
        top_chatters = tuple(
            TopChatter(discord_id=row.discord_id, weekly_xp=row.weekly_xp) for row in chatters
        )
        matches_played = await self._matches.count_confirmed_since(guild_id, since)
        mvp_discord_id, mvp_reason = _pick_mvp(rating_gains, top_chatters)

        await self._chat.reset_weekly(guild_id)

        return WeeklyDigest(
            rating_gains=rating_gains[:_TOP_N],
            top_chatters=top_chatters,
            matches_played=matches_played,
            mvp_discord_id=mvp_discord_id,
            mvp_reason=mvp_reason,
        )

    async def _rating_gains(self, guild_id: int, since: datetime) -> tuple[RatingGain, ...]:
        gains: list[RatingGain] = []
        for _member, player, discord_id in await self._links.list_active_for_guild(guild_id):
            snapshots = [
                s for s in await self._ranking.list_since(player.id, since) if s.rating is not None
            ]
            if len(snapshots) < 2:
                continue
            gain = snapshots[-1].rating - snapshots[0].rating  # type: ignore[operator]
            if gain > 0:
                gains.append(
                    RatingGain(
                        discord_id=discord_id, player_name=player.player_name, rating_gain=gain
                    )
                )
        gains.sort(key=lambda g: g.rating_gain, reverse=True)
        return tuple(gains)


def _pick_mvp(
    rating_gains: tuple[RatingGain, ...], top_chatters: tuple[TopChatter, ...]
) -> tuple[int | None, str | None]:
    """Biggest rating gain wins; a quiet week for ranked play falls back to
    the top chatter. A completely quiet week (neither) has no MVP.
    """
    if rating_gains:
        top = rating_gains[0]
        return top.discord_id, f"+{top.rating_gain} rating this week"
    if top_chatters:
        top_chatter = top_chatters[0]
        return top_chatter.discord_id, f"{top_chatter.weekly_xp} chat XP this week"
    return None, None
