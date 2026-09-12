"""Pure embed-construction tests for the new clan_embeds builders
(docs/DECISIONS.md ADR-068/ADR-070). No Discord/DB needed.
"""

from __future__ import annotations

from bot.content.clan_embeds import (
    build_legend_meta_embed,
    build_mvp_announcement_embed,
    build_spotlight_embed,
    build_tier_change_announcement_embed,
    build_weekly_digest_embed,
)
from services.clan_service import LegendMetaEntry


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
