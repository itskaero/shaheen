"""/admin status (docs/DECISIONS.md ADR-129): the report, what needs
attention, and the embed."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot.content.status_embeds import build_status_embed
from database.models.ranking_snapshot import RankingSnapshot
from database.repositories.brawlhalla_player_repository import BrawlhallaPlayerRepository
from database.repositories.ranking_snapshot_repository import RankingSnapshotRepository
from database.session import session_scope
from services.status_service import BotFacts, StatusService, SystemStatus, format_age

NOW = datetime(2026, 10, 15, 12, tzinfo=UTC)
INTERVAL = timedelta(hours=6)
HEALTHY_BOT = BotFacts(gateway_ms=80, uptime=timedelta(hours=3), loops={"ranking snapshot": True})


def _status(**overrides: object) -> SystemStatus:
    values: dict[str, object] = {
        "now": NOW,
        "bot": HEALTHY_BOT,
        "database_ok": True,
        "database_ms": 4,
        "schema_revision": "0027",
        "last_snapshot_at": NOW - timedelta(hours=1),
        "tracked_players": 40,
        "snapshot_interval": INTERVAL,
    }
    values.update(overrides)
    return SystemStatus(**values)  # type: ignore[arg-type]


async def _add_reading(
    session_factory: async_sessionmaker[AsyncSession], captured_at: datetime
) -> None:
    async with session_scope(session_factory) as session:
        player = await BrawlhallaPlayerRepository(session).upsert(
            brawlhalla_player_id=7, player_name="P7", region=None
        )
        await RankingSnapshotRepository(session).add(
            RankingSnapshot(
                brawlhalla_player_id=player.id,
                captured_at=captured_at,
                rating=1500,
                peak_rating=1500,
                tier="Gold",
                wins=1,
                games=2,
                season=42,
            )
        )


# --- what needs attention -------------------------------------------------


def test_a_healthy_system_has_no_problems() -> None:
    assert _status().problems() == []


def test_an_unreachable_database_comes_first() -> None:
    problems = _status(database_ok=False, database_ms=None, last_snapshot_at=None).problems()
    assert problems[0] == "The database is unreachable."
    # An unreachable database doesn't also claim "no snapshot yet".
    assert not any("No ranking snapshot" in p for p in problems)


def test_a_snapshot_is_late_after_two_missed_intervals() -> None:
    assert _status(last_snapshot_at=NOW - INTERVAL * 2).problems() == []
    late = _status(last_snapshot_at=NOW - INTERVAL * 2 - timedelta(minutes=1)).problems()
    assert any("12h 1m old" in p for p in late)


def test_no_snapshot_yet_is_reported() -> None:
    assert _status(last_snapshot_at=None).problems() == ["No ranking snapshot has been taken yet."]


def test_a_stopped_loop_and_slow_services_are_reported() -> None:
    bot = BotFacts(gateway_ms=900, uptime=timedelta(minutes=5), loops={"access catch-up": False})
    problems = _status(bot=bot, database_ms=450).problems()
    assert problems == [
        "The database is slow (450 ms).",
        "The access catch-up loop isn't running.",
        "Discord latency is high (900 ms).",
    ]


def test_format_age() -> None:
    assert format_age(timedelta(seconds=42)) == "42s"
    assert format_age(timedelta(minutes=5)) == "5m"
    assert format_age(timedelta(hours=6)) == "6h"
    assert format_age(timedelta(hours=7, minutes=3)) == "7h 3m"
    assert format_age(timedelta(days=3, hours=2)) == "3d 2h"
    assert format_age(timedelta(seconds=-5)) == "0s"


# --- the check against a database ------------------------------------------


async def test_check_on_an_empty_database(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    status = await StatusService(session_factory).check(
        now=NOW, bot=HEALTHY_BOT, snapshot_interval=INTERVAL
    )
    assert status.database_ok
    assert status.database_ms is not None
    assert status.schema_revision is None  # create_all, no Alembic table
    assert status.last_snapshot_at is None
    assert status.tracked_players == 0


async def test_check_reads_the_latest_snapshot(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _add_reading(session_factory, NOW - timedelta(hours=30))
    await _add_reading(session_factory, NOW - timedelta(hours=2))

    status = await StatusService(session_factory).check(
        now=NOW, bot=HEALTHY_BOT, snapshot_interval=INTERVAL
    )
    assert status.snapshot_age == timedelta(hours=2)
    assert status.tracked_players == 1
    assert status.problems() == []


async def test_check_reports_an_unreachable_database_without_raising() -> None:
    class Broken:
        def __call__(self) -> object:
            raise ConnectionRefusedError("db down")

    status = await StatusService(Broken()).check(  # type: ignore[arg-type]
        now=NOW, bot=HEALTHY_BOT, snapshot_interval=INTERVAL
    )
    assert not status.database_ok
    assert status.problems()[0] == "The database is unreachable."


# --- the embed -------------------------------------------------------------


def test_embed_for_a_healthy_system() -> None:
    embed = build_status_embed(_status())
    assert "All systems normal" in (embed.description or "")
    names = [f.name for f in embed.fields]
    assert names == ["Bot", "Database", "Rankings", "Background loops"]


def test_embed_lists_problems_when_down() -> None:
    embed = build_status_embed(_status(database_ok=False, database_ms=None))
    assert "Something is down" in (embed.description or "")
    attention = next(f for f in embed.fields if f.name == "⚠️ Needs attention")
    assert "unreachable" in (attention.value or "")
