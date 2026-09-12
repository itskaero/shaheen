"""Pure embed-construction tests for the new clan_embeds builders
(docs/DECISIONS.md ADR-068). No Discord/DB needed.
"""

from __future__ import annotations

from bot.content.clan_embeds import build_legend_meta_embed, build_tier_change_announcement_embed
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
