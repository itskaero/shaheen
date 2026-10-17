"""Looking-for-game (docs/DECISIONS.md ADR-136): the spar card, the Spar Ping
cooldown, the note cleanup, closing a call, and the link panel's rate limit."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from bot.content.competition_embeds import (
    build_scrim_closed_embed,
    build_scrim_embed,
    build_scrim_full_embed,
)
from bot.spar_ping import spar_ping_message
from core.exceptions import ShaheenError
from database.models.legend_snapshot import LegendSnapshot
from database.models.match import MatchKind, MatchSide
from database.models.ranking_snapshot import RankingSnapshot
from database.models.scrim import ScrimStatus
from database.repositories.brawlhalla_player_repository import BrawlhallaPlayerRepository
from services.match_service import MatchService
from services.rate_limit import SlidingWindow
from services.spar_service import NOTE_MAX, SparProfile, SparService, clean_note, ping_allowed
from tests.test_staff_service import GUILD, _link

NOW = datetime(2026, 10, 17, 15, tzinfo=UTC)


def test_clean_note_strips_mentions_links_and_long_text() -> None:
    assert clean_note(None) is None
    assert clean_note("   ") is None
    assert clean_note("FT5   NA\nservers") == "FT5 NA servers"
    assert clean_note("<@123> @everyone come https://x.y/z <@&9> now") == "come now"
    long = clean_note("a" * 200)
    assert long is not None and len(long) == NOTE_MAX and long.endswith("…")


def test_ping_cooldown() -> None:
    assert ping_allowed(None, NOW)
    assert not ping_allowed(NOW - timedelta(minutes=9), NOW)
    assert ping_allowed(NOW - timedelta(minutes=10), NOW)
    # SQLite hands back naive datetimes.
    assert not ping_allowed((NOW - timedelta(minutes=1)).replace(tzinfo=None), NOW)


async def test_claim_ping_once_per_cooldown(session: AsyncSession) -> None:
    service = SparService(session)
    assert await service.spar_role_id(GUILD) is None
    await service.set_spar_role(GUILD, 777)
    assert await service.spar_role_id(GUILD) == 777
    assert await service.claim_ping(GUILD, now=NOW)
    assert not await service.claim_ping(GUILD, now=NOW + timedelta(minutes=5))
    assert await service.claim_ping(GUILD, now=NOW + timedelta(minutes=11))


async def test_profile_shows_rating_and_main_legend(session: AsyncSession) -> None:
    assert await SparService(session).profile(GUILD, 42) is None
    await _link(session, 42, 5734378, "kaero.")
    player = await BrawlhallaPlayerRepository(session).get_by_brawlhalla_id(5734378)
    assert player is not None
    session.add(
        RankingSnapshot(
            brawlhalla_player_id=player.id,
            captured_at=NOW,
            rating=1820,
            peak_rating=1900,
            tier="Platinum 3",
            wins=50,
            games=100,
            region="SEA",
            season=42,
        )
    )
    for key, games in (("ada", 10), ("bodvar", 300)):
        session.add(
            LegendSnapshot(
                brawlhalla_player_id=player.id,
                captured_at=NOW,
                legend_id=len(key),
                legend_name_key=key,
                games=games,
            )
        )
    await session.flush()
    profile = await SparService(session).profile(GUILD, 42)
    assert profile is not None
    assert (profile.player_name, profile.rating, profile.tier) == ("kaero.", 1820, "Platinum 3")
    assert profile.main_legend == "bodvar"


def test_spar_card_shows_profile_slots_note_and_portrait() -> None:
    profile = SparProfile(
        player_name="kaero.",
        brawlhalla_id=5734378,
        rating=1820,
        tier="Platinum 3",
        region="sea",
        main_legend="bodvar",
        city="Lahore",
        team_tag="SHN",
    )
    embed = build_scrim_embed(
        creator_name="kaero",
        kind=MatchKind.ONE_V_ONE,
        side_counts=(1, 0),
        sides=(["kaero"], []),
        profile=profile,
        note="FT5, NA",
        expires_at=NOW,
        site_url="https://brawlistan.example/",
    )
    assert embed.title == "🥊 kaero is looking for a 1v1"
    text = embed.description or ""
    assert "> FT5, NA" in text and "**[SHN] kaero.**" in text and "1,820" in text
    assert "🏙️ Lahore" in text and f"<t:{int(NOW.timestamp())}:R>" in text
    assert [f.value for f in embed.fields] == ["🟢 kaero", "⚪ *open*"]
    assert embed.thumbnail.url == "https://brawlistan.example/assets/img/legend-portraits/bodvar.webp"

    unlinked = build_scrim_embed(creator_name="new", kind=MatchKind.TWO_V_TWO, side_counts=(0, 0))
    assert "not linked" in (unlinked.description or "")
    assert [f.value for f in unlinked.fields] == ["0/2", "0/2"]


def test_full_and_closed_cards() -> None:
    full = build_scrim_full_embed(kind=MatchKind.ONE_V_ONE, sides=(["a"], ["b"]))
    assert [f.value for f in full.fields] == ["a", "b"]
    assert "expired" in (
        build_scrim_closed_embed(creator_name="x", kind=MatchKind.ONE_V_ONE, cancelled=False).title
        or ""
    )


def test_spar_ping_messages() -> None:
    assert "on" in spar_ping_message(True)
    assert "off" in spar_ping_message(False)
    assert "staff" in spar_ping_message(None)


async def test_close_scrim_creator_only_and_once(session: AsyncSession) -> None:
    service = MatchService(session)
    scrim = await service.create_scrim(
        guild_id=GUILD, creator_discord_id=1, creator_joined_at=None, kind=MatchKind.ONE_V_ONE
    )
    await service.join_scrim(scrim_id=scrim.id, discord_id=1, joined_at=None, side=MatchSide.A)
    with pytest.raises(ShaheenError):
        await service.close_scrim(scrim.id, discord_id=2)
    assert await service.close_scrim(scrim.id, discord_id=1)
    assert scrim.status is ScrimStatus.CANCELLED
    assert not await service.close_scrim(scrim.id)  # expiry after a cancel: nothing to do
    with pytest.raises(ShaheenError):
        await service.join_scrim(scrim_id=scrim.id, discord_id=3, joined_at=None, side=MatchSide.B)


async def test_expiry_leaves_a_full_scrim_alone(session: AsyncSession) -> None:
    service = MatchService(session)
    scrim = await service.create_scrim(
        guild_id=GUILD, creator_discord_id=1, creator_joined_at=None, kind=MatchKind.ONE_V_ONE
    )
    await service.join_scrim(scrim_id=scrim.id, discord_id=1, joined_at=None, side=MatchSide.A)
    await service.join_scrim(scrim_id=scrim.id, discord_id=2, joined_at=None, side=MatchSide.B)
    assert not await service.close_scrim(scrim.id)
    assert scrim.status is ScrimStatus.FULL


def test_sliding_window() -> None:
    window = SlidingWindow(limit=2, window=timedelta(minutes=10))
    assert window.allow(1, now=NOW)
    assert window.allow(1, now=NOW + timedelta(minutes=1))
    assert not window.allow(1, now=NOW + timedelta(minutes=2))
    assert window.allow(2, now=NOW + timedelta(minutes=2))  # per key
    assert window.allow(1, now=NOW + timedelta(minutes=10))
