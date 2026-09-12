"""Pure embed-construction tests for the /suggest builders
(docs/DECISIONS.md ADR-070). No Discord/DB needed.
"""

from __future__ import annotations

from bot.content.engagement_embeds import (
    build_suggestion_confirmation_embed,
    build_suggestion_embed,
)


def test_suggestion_embed_carries_no_author_info() -> None:
    embed = build_suggestion_embed("Add a #memes-of-the-week channel")
    assert embed.description == "Add a #memes-of-the-week channel"
    assert embed.author.name is None


def test_suggestion_confirmation_embed_mentions_channel() -> None:
    embed = build_suggestion_confirmation_embed(channel_mention="<#123>")
    assert "<#123>" in embed.description
