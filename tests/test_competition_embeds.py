"""Pure embed-construction tests for build_rivalry_embed
(docs/DECISIONS.md ADR-068). No Discord/DB needed.
"""

from __future__ import annotations

from bot.content.competition_embeds import build_rivalry_embed


def test_rivalry_embed_shows_win_counts_each_way() -> None:
    embed = build_rivalry_embed(
        name_a="Reko", name_b="Jax", member_a_wins=3, member_b_wins=1, total_matches=4
    )
    fields = {f.name: f.value for f in embed.fields}
    assert fields["Reko"] == "3W"
    assert fields["Jax"] == "1W"
    assert embed.footer.text is not None
    assert "4 confirmed match" in embed.footer.text


def test_rivalry_embed_handles_no_matches_yet() -> None:
    embed = build_rivalry_embed(
        name_a="Reko", name_b="Jax", member_a_wins=0, member_b_wins=0, total_matches=0
    )
    assert embed.description is not None
    assert "haven't played" in embed.description
    assert embed.fields == []
