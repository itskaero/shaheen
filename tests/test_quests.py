"""Weekly quests and the season level (docs/DECISIONS.md ADR-128)."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from bot.content.network_embeds import build_quests_embed
from database.models.ranking_snapshot import RankingSnapshot
from database.repositories.brawlhalla_player_repository import BrawlhallaPlayerRepository
from database.repositories.pakistan_board_repository import PakistanBoardRepository
from database.repositories.ranking_snapshot_repository import RankingSnapshotRepository
from services.quest_service import QuestService
from services.quests import MAX_LEVEL, QUESTS, baseline, level, progress, week_bounds

GUILD = 1
# Wednesday 14 Oct 2026, 17:00 PKT. The week began Monday 12 Oct 00:00 PKT,
# which is Sunday 11 Oct 19:00 UTC.
NOW = datetime(2026, 10, 14, 12, tzinfo=UTC)
WEEK_START = datetime(2026, 10, 11, 19, tzinfo=UTC)
GRIND, WIN, CLIMB = QUESTS


def _snap(at: datetime, *, games: int, wins: int, rating: int | None, season: int = 42):
    return RankingSnapshot(
        brawlhalla_player_id=1,
        captured_at=at,
        rating=rating,
        peak_rating=rating,
        wins=wins,
        games=games,
        season=season,
    )


def test_weeks_run_monday_to_monday_pakistan_time() -> None:
    monday, start, end = week_bounds(NOW)
    assert (monday, start, end) == (date(2026, 10, 12), WEEK_START, WEEK_START + timedelta(days=7))
    # Sunday 23:30 PKT still belongs to the previous week; 00:30 PKT Monday doesn't.
    assert week_bounds(WEEK_START - timedelta(minutes=30))[0] == date(2026, 10, 5)
    assert week_bounds(WEEK_START + timedelta(minutes=30))[0] == date(2026, 10, 12)


def test_progress_counts_from_the_last_reading_before_the_week() -> None:
    before = _snap(WEEK_START - timedelta(hours=6), games=100, wins=50, rating=1500)
    early = _snap(WEEK_START + timedelta(hours=6), games=104, wins=52, rating=1510)
    latest = _snap(NOW, games=118, wins=59, rating=1560)
    start = baseline([before, early, latest], week_start=WEEK_START, season=42)
    assert start is before
    assert [progress(q, start, latest) for q in QUESTS] == [18, 9, 60]


def test_a_player_first_seen_mid_week_counts_from_their_first_reading() -> None:
    first = _snap(WEEK_START + timedelta(days=1), games=10, wins=5, rating=1200)
    latest = _snap(NOW, games=14, wins=6, rating=1180)
    start = baseline([first, latest], week_start=WEEK_START, season=42)
    assert start is first
    # A rating drop is no progress, never negative.
    assert [progress(q, start, latest) for q in QUESTS] == [4, 1, 0]


def test_last_seasons_readings_never_count() -> None:
    old = _snap(WEEK_START - timedelta(days=1), games=300, wins=150, rating=1900, season=41)
    new = _snap(NOW, games=12, wins=7, rating=1300, season=42)
    assert baseline([old, new], week_start=WEEK_START, season=42) is new
    assert progress(GRIND, None, new) == 0


def test_levels_cap() -> None:
    assert (level(0), level(99), level(100), level(10**6)) == (1, 1, 2, MAX_LEVEL)


async def _board_player(session: AsyncSession, bid: int) -> int:
    player = await BrawlhallaPlayerRepository(session).upsert(
        brawlhalla_player_id=bid, player_name=f"P{bid}", region=None
    )
    await PakistanBoardRepository(session).add(
        guild_id=GUILD, player_id=player.id, added_by_discord_id=1, owner_discord_id=None
    )
    return player.id


async def _reading(
    session: AsyncSession, player_id: int, at: datetime, *, games: int, wins: int, rating: int
) -> None:
    snap = _snap(at, games=games, wins=wins, rating=rating)
    snap.brawlhalla_player_id = player_id
    await RankingSnapshotRepository(session).add(snap)


async def test_completions_are_recorded_once_and_feed_the_level(session: AsyncSession) -> None:
    grinder = await _board_player(session, 10)
    idle = await _board_player(session, 11)
    await _reading(session, grinder, WEEK_START - timedelta(hours=2), games=0, wins=0, rating=1000)
    await _reading(session, grinder, NOW, games=16, wins=9, rating=1030)
    await _reading(session, idle, NOW, games=40, wins=20, rating=1400)

    service = QuestService(session)
    first = await service.evaluate(GUILD, now=NOW)
    assert sorted((c.player.brawlhalla_player_id, c.quest.key) for c in first) == [
        (10, "grind"),
        (10, "win"),
    ]
    assert await service.evaluate(GUILD, now=NOW) == []  # idempotent

    player = await BrawlhallaPlayerRepository(session).get_by_brawlhalla_id(10)
    assert player is not None
    status = await service.status(player, now=NOW)
    assert (status.xp, status.level, status.week_start) == (200, 3, date(2026, 10, 12))
    assert [(q.quest.key, q.progress, q.done) for q in status.quests] == [
        ("grind", 15, True),
        ("win", 8, True),
        ("climb", 30, False),
    ]
    embed = build_quests_embed(player_name="P10", status=status)
    assert "level **3**" in (embed.description or "")
    assert len(embed.fields) == len(QUESTS) + 1

    # Next week the quests start again, and the season XP stays.
    later = NOW + timedelta(days=7)
    assert await service.evaluate(GUILD, now=later) == []
    next_week = await service.status(player, now=later)
    assert next_week.xp == 200 and not any(q.done for q in next_week.quests)
