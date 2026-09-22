"""Pure embed-construction tests for the /suggest builders
(docs/DECISIONS.md ADR-070). No Discord/DB needed.
"""

from __future__ import annotations

from bot.content.engagement_embeds import (
    build_anthem_embed,
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


def test_anthem_embed_links_to_the_music_page() -> None:
    embed = build_anthem_embed(website_url="https://itskaero.github.io/shaheen/music.html")
    assert embed.url == "https://itskaero.github.io/shaheen/music.html"
    assert "https://itskaero.github.io/shaheen/music.html" in embed.fields[0].value
