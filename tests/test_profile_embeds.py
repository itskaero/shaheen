"""build_profile_embed / build_legends_embed — pure embed-construction
tests (docs/DECISIONS.md ADR-067). No Discord/DB needed: these are plain
functions building discord.Embed objects from already-fetched data.
"""

from __future__ import annotations

from datetime import UTC, datetime

from bot.content.profile_embeds import build_legends_embed, build_profile_embed
from database.models.achievement import Achievement
from database.models.brawlhalla_player import BrawlhallaPlayer
from database.models.chat_activity import ChatActivity
from integrations.brawlhalla.models import LegendStat, PlayerRankedResponse, PlayerStatsResponse

PLAYER = BrawlhallaPlayer(brawlhalla_player_id=12345, player_name="Reko Rex", region="us-e")
STATS = PlayerStatsResponse(brawlhalla_id=12345, name="Reko Rex", level=42, games=100, wins=60)


def _field(embed, name: str) -> str | None:
    for field in embed.fields:
        if field.name == name:
            return field.value
    return None


def test_profile_embed_shows_region_rank_alongside_global_rank() -> None:
    ranked = PlayerRankedResponse(
        brawlhalla_id=12345,
        name="Reko Rex",
        tier="Diamond",
        rating=1800,
        peak_rating=1900,
        wins=60,
        games=100,
        global_rank=500,
        region_rank=12,
        region="us-e",
    )
    embed = build_profile_embed(
        display_name="Reko",
        avatar_url=None,
        player=PLAYER,
        stats=STATS,
        ranked=ranked,
        joined_at=None,
        chat_activity=None,
        achievements=[],
    )
    assert _field(embed, "Global Rank") == "#500"
    assert _field(embed, "Region Rank") == "#12"


def test_profile_embed_omits_region_rank_when_unset() -> None:
    ranked = PlayerRankedResponse(
        brawlhalla_id=12345, name="Reko Rex", tier="Gold", rating=1200, peak_rating=1300
    )
    embed = build_profile_embed(
        display_name="Reko",
        avatar_url=None,
        player=PLAYER,
        stats=STATS,
        ranked=ranked,
        joined_at=None,
        chat_activity=None,
        achievements=[],
    )
    assert _field(embed, "Region Rank") is None


def test_profile_embed_derives_chat_level_live_from_xp() -> None:
    """Regression guard: the stored `level` column on ChatActivity is only
    updated on a detected level-up (bot/cogs/engagement.py) and can go
    stale — the embed must always derive the level from xp itself, never
    trust the column, same rule as /level and the website's Community
    Activity table (docs/DECISIONS.md ADR-065/066).
    """
    activity = ChatActivity(guild_id=1, discord_id=1, xp=150, level=1)  # stale stored level
    embed = build_profile_embed(
        display_name="Reko",
        avatar_url=None,
        player=PLAYER,
        stats=STATS,
        ranked=None,
        joined_at=None,
        chat_activity=activity,
        achievements=[],
    )
    value = _field(embed, "Chat Rank")
    assert value is not None
    assert "Level 2" in value  # level_for_xp(150) == 2, not the stale stored 1
    assert "Hatchling" in value


def test_profile_embed_omits_chat_rank_with_no_activity() -> None:
    embed = build_profile_embed(
        display_name="Reko",
        avatar_url=None,
        player=PLAYER,
        stats=STATS,
        ranked=None,
        joined_at=None,
        chat_activity=None,
        achievements=[],
    )
    assert _field(embed, "Chat Rank") is None


def test_profile_embed_shows_achievement_count_and_names() -> None:
    achievements = [
        (Achievement(key="first_link", name="First Contact", description="..."), datetime.now(UTC)),
        (Achievement(key="games_100", name="Centurion", description="..."), datetime.now(UTC)),
    ]
    embed = build_profile_embed(
        display_name="Reko",
        avatar_url=None,
        player=PLAYER,
        stats=STATS,
        ranked=None,
        joined_at=None,
        chat_activity=None,
        achievements=achievements,
    )
    value = _field(embed, "Achievements (2)")
    assert value is not None
    assert "First Contact" in value
    assert "Centurion" in value


def test_profile_embed_omits_achievements_field_when_none_earned() -> None:
    embed = build_profile_embed(
        display_name="Reko",
        avatar_url=None,
        player=PLAYER,
        stats=STATS,
        ranked=None,
        joined_at=None,
        chat_activity=None,
        achievements=[],
    )
    assert not any(field.name.startswith("Achievements") for field in embed.fields)


def test_profile_embed_links_to_website_profile() -> None:
    embed = build_profile_embed(
        display_name="Reko",
        avatar_url=None,
        player=PLAYER,
        stats=STATS,
        ranked=None,
        joined_at=None,
        chat_activity=None,
        achievements=[],
    )
    value = _field(embed, "Full Profile")
    assert value is not None
    assert "player.html?id=12345" in value


def test_legends_embed_includes_damage_and_falls() -> None:
    stats = PlayerStatsResponse(
        brawlhalla_id=12345,
        name="Reko Rex",
        legends=[
            LegendStat(
                legend_id=1,
                legend_name_key="bodvar",
                games=10,
                wins=5,
                kos=20,
                damagedealt=15000,
                falls=8,
            )
        ],
    )
    embed = build_legends_embed(display_name="Reko", player=PLAYER, stats=stats)
    assert embed.description is not None
    assert "15,000 DMG" in embed.description
    assert "8 falls" in embed.description
