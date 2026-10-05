"""Pure embed-construction tests for the engagement builders. No
Discord/DB needed. (/suggest retired with ADR-109.)
"""

from __future__ import annotations

from bot.content.engagement_embeds import build_anthem_embed


def test_anthem_embed_links_to_the_music_page() -> None:
    embed = build_anthem_embed(website_url="https://itskaero.github.io/shaheen/music.html")
    assert embed.url == "https://itskaero.github.io/shaheen/music.html"
    assert "https://itskaero.github.io/shaheen/music.html" in embed.fields[0].value
