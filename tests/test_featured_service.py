"""The Featured Player (docs/DECISIONS.md ADR-111)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import NotFoundError
from database.models.ranking_snapshot import RankingSnapshot
from database.repositories.brawlhalla_player_repository import BrawlhallaPlayerRepository
from database.repositories.ranking_snapshot_repository import RankingSnapshotRepository
from services.featured_service import FeaturedService

GUILD = 1


async def test_only_tracked_players_can_be_featured(session: AsyncSession) -> None:
    with pytest.raises(NotFoundError):
        await FeaturedService(session).set(
            guild_id=GUILD, brawlhalla_id=404, note=None, staff_discord_id=1
        )


async def test_feature_and_clear(session: AsyncSession) -> None:
    player = await BrawlhallaPlayerRepository(session).upsert(
        brawlhalla_player_id=10, player_name="Kaero", region="ASIA"
    )
    await RankingSnapshotRepository(session).add(
        RankingSnapshot(
            brawlhalla_player_id=player.id,
            captured_at=datetime.now(UTC),
            rating=2100,
            peak_rating=2200,
            tier="Diamond",
            wins=1,
            games=2,
            season=42,
        )
    )
    service = FeaturedService(session)
    assert await service.current(GUILD) is None

    await service.set(
        guild_id=GUILD, brawlhalla_id=10, note="  Won the\nweekly cup ", staff_discord_id=1
    )
    featured = await service.current(GUILD)
    assert featured is not None
    assert featured.player.player_name == "Kaero"
    assert featured.note == "Won the weekly cup"
    assert featured.latest is not None and featured.latest.rating == 2100

    await service.clear(guild_id=GUILD, staff_discord_id=1)
    assert await service.current(GUILD) is None
