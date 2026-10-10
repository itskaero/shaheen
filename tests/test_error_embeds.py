"""The staff copy of an unexpected command error (docs/DECISIONS.md ADR-126)."""

from __future__ import annotations

from bot.content.error_embeds import build_error_report_embed, describe_error, error_reference


def test_reference_is_short_and_varies() -> None:
    refs = {error_reference() for _ in range(20)}
    assert all(len(r) == 6 for r in refs) and len(refs) > 1


def test_description_is_type_and_first_line_only_and_redacted() -> None:
    error = RuntimeError("GET https://api.example/x?api_key=SECRET123 failed\nsecond line")
    text = describe_error(error)
    assert text.startswith("RuntimeError: GET")
    assert "SECRET123" not in text and "second line" not in text
    assert describe_error(ValueError()) == "ValueError"
    assert len(describe_error(ValueError("x" * 1000))) == 300


def test_report_embed_names_the_command_and_reference() -> None:
    embed = build_error_report_embed(
        command="access roles", reference="abc123", error=KeyError("k"), user_id=5
    )
    assert embed.title == "⚠️ Command error · abc123"
    fields = {f.name: f.value for f in embed.fields}
    assert fields == {"Command": "`/access roles`", "Member": "<@5>"}
