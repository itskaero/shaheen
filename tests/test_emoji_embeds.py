"""bot/content/emoji_embeds.py — /emoji sync and /emoji browse
(docs/DECISIONS.md ADR-090/ADR-092).
"""

from __future__ import annotations

from bot.content.emoji_embeds import (
    build_emoji_browse_intro_embed,
    build_emoji_candidate_preview_embed,
    build_emoji_sync_embed,
)
from services.emoji_service import EmojiSyncReport


def test_sync_embed_reports_created_and_skipped() -> None:
    report = EmojiSyncReport(created=["koji_gg"], skipped_existing=["hattori_wp"])
    embed = build_emoji_sync_embed(report)

    fields = {f.name: f.value for f in embed.fields}
    assert fields["🆕 Created"] == "1"
    assert fields["✅ Already present"] == "1"
    assert "koji_gg" in (fields.get("New emoji") or "")


def test_sync_embed_flags_no_room() -> None:
    report = EmojiSyncReport(skipped_no_room=["koji_gg"])
    embed = build_emoji_sync_embed(report)

    fields = {f.name: f.value for f in embed.fields}
    assert fields["🚫 No room"] == "1"
    assert "koji_gg" in (fields.get("Skipped — no free slots") or "")


def test_sync_embed_says_up_to_date_when_nothing_happened() -> None:
    embed = build_emoji_sync_embed(EmojiSyncReport())
    assert any("already on this server" in (f.value or "") for f in embed.fields)


def test_browse_intro_embed_mentions_the_flow() -> None:
    embed = build_emoji_browse_intro_embed()
    assert embed.description is not None
    assert "legend" in embed.description.lower()


def test_candidate_preview_embed_shows_position_and_queue() -> None:
    embed = build_emoji_candidate_preview_embed(legend="wu_shang", index=2, total=13, queue_count=4)

    assert "3/13" in (embed.title or "")
    assert "Wu Shang" in (embed.title or "")
    assert embed.image.url == "attachment://preview.png"
    assert "4" in (embed.footer.text or "")


def test_candidate_preview_embed_notes_an_empty_queue() -> None:
    embed = build_emoji_candidate_preview_embed(legend="koji", index=0, total=26, queue_count=0)
    assert "nothing yet" in (embed.footer.text or "").lower()
