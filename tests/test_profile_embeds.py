"""build_profile_embed / build_legends_embed — pure embed-construction
tests (docs/DECISIONS.md ADR-067). No Discord/DB needed: these are plain
functions building discord.Embed objects from already-fetched data.
"""

from __future__ import annotations

from datetime import UTC, datetime

from bot.content.profile_embeds import (
    build_compare_embed,
    build_legends_embed,
    build_profile_embed,
    build_refresh_embed,
)
from database.models.achievement import Achievement
from database.models.brawlhalla_player import BrawlhallaPlayer
from database.models.chat_activity import ChatActivity
from integrations.brawlhalla.models import (
    LegendStat,
    PlayerRankedResponse,
    PlayerStatsResponse,
    RankedLegendStat,
)

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
    value = _field(embed, "Achievements (2/30)")
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


# --- ADR-094: favourite Legend, playstyle, clan role, Discord dates ---------


def test_profile_embed_shows_favourite_legend_and_playstyle() -> None:
    stats = PlayerStatsResponse(
        brawlhalla_id=12345,
        name="Reko Rex",
        legends=[
            LegendStat(
                legend_id=1, legend_name_key="bodvar", games=10, kos=5, damagedealt=1000, falls=30
            ),
            LegendStat(
                legend_id=2, legend_name_key="orion", games=40, kos=60, damagedealt=1000, falls=30
            ),
        ],
    )
    embed = build_profile_embed(
        display_name="Reko",
        avatar_url=None,
        player=PLAYER,
        stats=stats,
        ranked=None,
        joined_at=None,
        chat_activity=None,
        achievements=[],
    )
    assert _field(embed, "Favourite Legend") == "Orion (40 games)"
    assert _field(embed, "Playstyle") == "Aggressive"


def test_profile_embed_omits_favourite_legend_with_no_legends_played() -> None:
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
    assert _field(embed, "Favourite Legend") is None
    assert _field(embed, "Playstyle") is None


def test_profile_embed_shows_clan_role_when_given() -> None:
    embed = build_profile_embed(
        display_name="Reko",
        avatar_url=None,
        player=PLAYER,
        stats=STATS,
        ranked=None,
        joined_at=None,
        chat_activity=None,
        achievements=[],
        clan_role="Moderator",
    )
    assert _field(embed, "Clan Role") == "Moderator"


def test_profile_embed_omits_clan_role_when_absent() -> None:
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
    assert _field(embed, "Clan Role") is None


def test_profile_embed_shows_discord_account_and_guild_dates() -> None:
    embed = build_profile_embed(
        display_name="Reko",
        avatar_url=None,
        player=PLAYER,
        stats=STATS,
        ranked=None,
        joined_at=None,
        chat_activity=None,
        achievements=[],
        discord_created_at=datetime(2020, 3, 1, tzinfo=UTC),
        discord_joined_at=datetime(2023, 7, 1, tzinfo=UTC),
    )
    value = _field(embed, "Discord")
    assert value is not None
    assert "Mar 2020" in value
    assert "Jul 2023" in value


def test_profile_embed_omits_discord_field_when_no_dates_given() -> None:
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
    assert _field(embed, "Discord") is None


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


# --- ADR-084: /compare, /refresh, ranked-legend annotation -------------------


def test_compare_embed_names_who_leads_and_by_how_much() -> None:
    def ranked(rating: int) -> PlayerRankedResponse:
        return PlayerRankedResponse(
            brawlhalla_id=1,
            name="X",
            tier="Diamond",
            rating=rating,
            peak_rating=rating + 20,
            wins=50,
            games=100,
        )

    embed = build_compare_embed(
        left_name="Kaero",
        left_stats=STATS,
        left_ranked=ranked(1800),
        right_name="Rival",
        right_stats=STATS,
        right_ranked=ranked(1650),
    )

    assert embed.description is not None
    assert "Kaero" in embed.title and "Rival" in embed.title
    assert "1800" in embed.description and "1650" in embed.description
    assert embed.footer.text == "Kaero leads by 150 rating."


def test_compare_embed_handles_an_unranked_side() -> None:
    embed = build_compare_embed(
        left_name="Kaero",
        left_stats=STATS,
        left_ranked=None,
        right_name="Rival",
        right_stats=STATS,
        right_ranked=None,
    )

    assert embed.description is not None
    assert "—" in embed.description  # no rating rather than a fabricated 0
    assert embed.footer.text is None


def test_refresh_embed_lists_newly_earned_achievements() -> None:
    embed = build_refresh_embed(
        display_name="Kaero",
        player=PLAYER,
        ranked=None,
        new_achievements=["Century", "Ascendant"],
    )
    assert "Refreshed" in embed.title
    assert _field(embed, "New Achievements") == "Century, Ascendant"


def test_refresh_embed_omits_the_achievements_field_when_nothing_was_earned() -> None:
    embed = build_refresh_embed(
        display_name="Kaero", player=PLAYER, ranked=None, new_achievements=[]
    )
    assert _field(embed, "New Achievements") is None


def test_legends_embed_annotates_ranked_legends() -> None:
    """PlayerRankedResponse.legends was fetched every snapshot since Phase 2
    and thrown away; /legends is the first thing that shows it.
    """
    stats = PlayerStatsResponse(
        brawlhalla_id=12345,
        name="Reko Rex",
        legends=[LegendStat(legend_id=3, legend_name_key="bodvar", games=80, wins=50, kos=120)],
    )
    ranked = PlayerRankedResponse(
        brawlhalla_id=12345,
        name="Reko Rex",
        tier="Diamond",
        rating=1800,
        peak_rating=1900,
        wins=50,
        games=80,
        legends=[
            RankedLegendStat(
                legend_id=3,
                legend_name_key="bodvar",
                rating=1755,
                peak_rating=1790,
                tier="Diamond",
                wins=30,
                games=50,
            )
        ],
    )

    embed = build_legends_embed(display_name="Kaero", player=PLAYER, stats=stats, ranked=ranked)

    assert embed.description is not None
    assert "Ranked: 1755 (Diamond)" in embed.description
    assert "30W-20L" in embed.description


def test_legends_embed_without_ranked_data_is_unchanged() -> None:
    stats = PlayerStatsResponse(
        brawlhalla_id=12345,
        name="Reko Rex",
        legends=[LegendStat(legend_id=3, legend_name_key="bodvar", games=80, wins=50, kos=120)],
    )
    embed = build_legends_embed(display_name="Kaero", player=PLAYER, stats=stats, ranked=None)

    assert embed.description is not None
    assert "Ranked:" not in embed.description
