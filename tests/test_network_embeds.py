"""Pure builders for the BRAWLISTAN network commands (docs/DECISIONS.md ADR-111)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from bot.content.network_embeds import (
    build_legend_embed,
    build_player_report_embed,
    build_rankings_embed,
    build_season_embed,
    player_url,
    profile_view,
    site_view,
)
from database.models.player_report import PlayerReport
from services.clan_service import LegendMetaEntry
from services.seasons import pakistan_season

SITE = "https://example.test/brawlistan/"


def _row(
    name: str, rating: int | None, rating_2v2: int | None = None, verified: bool = False
) -> SimpleNamespace:
    snapshot = SimpleNamespace(rating=rating, tier="Gold", rating_2v2=rating_2v2, tier_2v2="Silver")
    return SimpleNamespace(
        player=SimpleNamespace(player_name=name), snapshot=snapshot, is_verified=verified
    )


def test_rankings_lists_medals_ratings_and_verification() -> None:
    embed = build_rankings_embed(
        rows=[_row("Khan", 2100, verified=True), _row("Ali", 1900)],  # type: ignore[list-item]
        bracket="1v1",
        season=42,
        site_url=SITE,
    )
    assert embed.description is not None
    assert embed.description.splitlines()[0] == "🥇 **Khan** ✓ — 2100 · Gold"
    assert "🥈 **Ali** — 1900" in embed.description
    assert embed.url == "https://example.test/brawlistan/rankings.html"
    assert "Pakistan Season 1" in (embed.footer.text or "")


def test_rankings_says_data_unavailable_instead_of_inventing_rows() -> None:
    embed = build_rankings_embed(rows=[], bracket="2v2", season=None, site_url=SITE)
    assert "Data unavailable" in (embed.description or "")


def test_2v2_uses_the_2v2_numbers() -> None:
    embed = build_rankings_embed(
        rows=[_row("Pair", 1500, rating_2v2=1700)],  # type: ignore[list-item]
        bracket="2v2",
        season=42,
        site_url=SITE,
    )
    assert "1700 · Silver" in (embed.description or "")


def test_player_links_use_the_site_slug() -> None:
    assert (
        player_url(SITE, "Khan Bhai!", 123)
        == "https://example.test/brawlistan/player/khan-bhai-123/"
    )
    (button,) = profile_view(SITE, "Khan Bhai!", 123).children
    assert button.url == "https://example.test/brawlistan/player/khan-bhai-123/"


def test_site_view_is_link_buttons_only() -> None:
    urls = [b.url for b in site_view(SITE).children]
    assert urls[0] == "https://example.test/brawlistan/index.html"
    assert all(u.startswith("https://example.test/brawlistan/") for u in urls)


def test_season_embed_counts_days_left() -> None:
    season = pakistan_season(42)
    assert season is not None
    embed = build_season_embed(season, now=season.ends_at - timedelta(days=10, hours=1))
    assert "**10** days left" in (embed.description or "")
    assert embed.title == "Pakistan Season 1 · Markhor"


def test_legend_embed_without_data_says_so() -> None:
    embed = build_legend_embed(None, legend_key="bodvar", rank=None)
    assert embed.title == "⚔️ Bodvar in Pakistan"
    assert "Data unavailable" in (embed.description or "")
    entry = LegendMetaEntry(
        legend_name_key="bodvar", total_games=200, total_wins=110, player_count=3
    )
    filled = build_legend_embed(entry, legend_key="bodvar", rank=2)
    assert [f.value for f in filled.fields] == ["3", "200", "55.0%", "#2 across the network"]


def test_report_card_names_the_target_and_hides_nothing_staff_need() -> None:
    report = PlayerReport(
        id=4,
        guild_id=1,
        source="website",
        reporter_discord_id=None,
        reported_discord_id=None,
        reported_brawlhalla_id=99,
        reported_name="Smurf",
        reason="Boosting accounts",
        status="open",
    )
    report.created_at = datetime(2026, 10, 5, tzinfo=UTC)
    embed = build_player_report_embed(report, reporter=None)
    fields = {f.name: f.value for f in embed.fields}
    assert embed.title == "🛡️ Report #4"
    assert fields["Reported"] == "Smurf · Brawlhalla 99"
    assert fields["Reporter"] == "Website visitor"
    assert fields["Source"] == "Website"
    assert fields["Status"] == "Open"
