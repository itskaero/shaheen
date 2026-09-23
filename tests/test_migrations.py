"""Alembic upgrade/downgrade round-trip, per docs/DEVELOPMENT.md's testing priorities."""

import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command

REPO_ROOT = Path(__file__).resolve().parents[1]


def _alembic_config() -> Config:
    config = Config(str(REPO_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(REPO_ROOT / "alembic"))
    return config


def test_upgrade_then_downgrade_round_trip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db_path = tmp_path / "migration_test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")
    config = _alembic_config()

    command.upgrade(config, "head")
    assert db_path.exists()

    command.downgrade(config, "base")


def test_0015_restamps_default_season_rows_around_the_s42_reset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """ADR-102: production stamped everything "season 1"; the reset splits it."""
    db_path = tmp_path / "restamp.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")
    config = _alembic_config()
    command.upgrade(config, "0014")

    rows = [
        ("2026-09-10 12:00:00.000000", 1),  # S41
        ("2026-09-22 23:59:59.000000", 1),  # S41, last second
        ("2026-09-23 00:00:00.000000", 1),  # S42, first second
        ("2026-09-23 15:00:00.000000", 1),  # S42
        ("2026-09-10 12:00:00.000000", None),  # unknown season stays unknown
    ]
    with sqlite3.connect(db_path) as conn:
        conn.executemany(
            "INSERT INTO ranking_snapshots"
            " (brawlhalla_player_id, captured_at, wins, games, season, created_at, updated_at)"
            " VALUES (1, ?, 0, 0, ?, '2026-09-23', '2026-09-23')",
            rows,
        )

    command.upgrade(config, "head")

    with sqlite3.connect(db_path) as conn:
        seasons = [s for (s,) in conn.execute("SELECT season FROM ranking_snapshots ORDER BY id")]
    assert seasons == [41, 41, 42, 42, None]
