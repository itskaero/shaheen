"""Pure embed-construction tests for the new clan_embeds builders
(docs/DECISIONS.md ADR-068/ADR-070). No Discord/DB needed.
"""

from __future__ import annotations

from bot.content.clan_embeds import (
    build_clan_stats_embed,
    build_leaderboard_embed,
    build_legend_meta_embed,
    build_mvp_announcement_embed,
    build_spotlight_embed,
    build_tier_change_announcement_embed,
    build_weekly_digest_embed,
)
from services.clan_service import ClanStats, LegendMetaEntry


def test_tier_change_embed_promotion_is_upbeat() -> None:
    embed = build_tier_change_announcement_embed(
        display_name="Reko",
        player_name="Reko Rex",
        old_tier="Gold I",
        new_tier="Platinum III",
        promoted=True,
    )
    assert "Promotion" in embed.title
    assert "Gold I" in embed.description
    assert "Platinum III" in embed.description


def test_tier_change_embed_demotion_is_lower_key() -> None:
    embed = build_tier_change_announcement_embed(
        display_name="Reko",
        player_name="Reko Rex",
        old_tier="Diamond I",
        new_tier="Platinum III",
        promoted=False,
    )
    assert "Demotion" in embed.title
    assert "dropped" in embed.description.lower()


def test_legend_meta_embed_lists_entries_with_win_rate() -> None:
    entries = [
        LegendMetaEntry(legend_name_key="bodvar", total_games=40, total_wins=25, player_count=2)
    ]
    embed = build_legend_meta_embed(entries)
    assert embed.description is not None
    assert "Bodvar" in embed.description
    assert "62%" in embed.description or "63%" in embed.description  # 25/40 = 62.5%
    assert "2 member" in embed.description


def test_legend_meta_embed_handles_empty_list() -> None:
    embed = build_legend_meta_embed([])
    assert embed.description is not None
    assert "Not enough" in embed.description


def test_weekly_digest_embed_lists_gains_and_chatters() -> None:
    embed = build_weekly_digest_embed(
        rating_gains=[("Reko", 120), ("Aima", 40)],
        top_chatters=[("Bilal", 300)],
        matches_played=7,
    )
    fields = {field.name: field.value for field in embed.fields}
    assert "Reko" in fields["📈 Top Rating Gains"]
    assert "+120" in fields["📈 Top Rating Gains"]
    assert "Bilal" in fields["💬 Most Active Chatters"]
    assert fields["⚔️ Matches Played"] == "7"


def test_weekly_digest_embed_quiet_week() -> None:
    embed = build_weekly_digest_embed(rating_gains=[], top_chatters=[], matches_played=0)
    assert embed.description is not None
    assert "quiet week" in embed.description.lower()


def test_mvp_announcement_embed_includes_reason() -> None:
    embed = build_mvp_announcement_embed(display_name="Reko", reason="+120 rating this week")
    assert "Reko" in embed.description
    assert "+120 rating this week" in embed.description


def test_spotlight_embed_credits_staff_in_footer() -> None:
    embed = build_spotlight_embed(display_name="Aima", note="Clutch scrim MVP!", staff_name="Kaero")
    assert "Aima" in embed.title
    assert embed.description == "Clutch scrim MVP!"
    assert embed.footer.text is not None
    assert "Kaero" in embed.footer.text


def test_clan_stats_embed_reports_totals_and_spread() -> None:
    stats = ClanStats(
        members_ranked=3,
        total_games=300,
        total_wins=180,
        average_rating=1600,
        median_rating=1550,
        highest=("Kaero", 1900),
        tier_counts=[("Diamond", 2), ("Gold", 1)],
        region_counts=[("SEA", 3)],
        top_legends=[
            LegendMetaEntry(
                legend_name_key="bodvar", total_games=100, total_wins=60, player_count=3
            )
        ],
    )

    embed = build_clan_stats_embed(stats)

    assert _embed_field(embed, "Ranked Members") == "3"
    assert _embed_field(embed, "Combined Wins") == "180 (60%)"
    assert _embed_field(embed, "Average Rating") == "1600"
    # Median sits next to the mean on purpose: one high-rated member drags
    # an average far more than the clan's typical standing moved.
    assert _embed_field(embed, "Median Rating") == "1550"
    assert _embed_field(embed, "Highest Rated") == "Kaero — 1900"
    assert "Diamond" in (_embed_field(embed, "Tier Spread") or "")
    assert "Bodvar" in (_embed_field(embed, "Most-Played Legends") or "")


def test_clan_stats_embed_with_no_snapshots_explains_itself() -> None:
    stats = ClanStats(
        members_ranked=0,
        total_games=0,
        total_wins=0,
        average_rating=None,
        median_rating=None,
        highest=None,
        tier_counts=[],
        region_counts=[],
        top_legends=[],
    )

    embed = build_clan_stats_embed(stats)

    assert embed.description is not None
    assert "/link" in embed.description
    assert embed.fields == []


def _embed_field(embed, name: str) -> str | None:
    for field in embed.fields:
        if field.name == name:
            return field.value
    return None


def test_leaderboard_embed_defaults_to_the_clan_board() -> None:
    embed = build_leaderboard_embed([("Foo", "Gold", 1500)], season=5)
    assert embed.title == "🏆 Shaheen Leaderboard"
    assert embed.footer.text == "Season 5 · 1 member(s) placed"


def test_leaderboard_embed_can_be_the_pakistan_board() -> None:
    embed = build_leaderboard_embed(
        [], title="🇵🇰 Pakistan Leaderboard", empty_hint="add yourself with `/pakistan join`"
    )
    assert embed.title == "🇵🇰 Pakistan Leaderboard"
    assert "/pakistan join" in (embed.description or "")
