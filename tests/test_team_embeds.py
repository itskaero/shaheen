"""/team embeds (docs/DECISIONS.md ADR-114)."""

from __future__ import annotations

from types import SimpleNamespace

from bot.content.team_embeds import build_team_embed, team_url, team_view

SITE = "https://example.test/brawlistan"


def _entry(name: str, rating: int | None, role: str = "player") -> SimpleNamespace:
    snap = SimpleNamespace(rating=rating, tier="Gold") if rating else None
    return SimpleNamespace(
        member=SimpleNamespace(role=role), player=SimpleNamespace(player_name=name), snapshot=snap
    )


def _summary(**team: object) -> SimpleNamespace:
    base = {
        "name": "Delight Esports",
        "tag": "DE",
        "slug": "delight-esports",
        "logo": "delight-esports",
        "description": None,
        "is_founding": False,
    }
    base.update(team)
    return SimpleNamespace(team=SimpleNamespace(**base), members=2, rating=1800)


def test_team_embed_shows_captain_rating_logo_and_link() -> None:
    embed = build_team_embed(
        _summary(),
        [_entry("Cap", 1900, "captain"), _entry("New", None)],
        site_url=SITE,  # type: ignore[arg-type,list-item]
    )
    roster = embed.fields[2].value
    assert roster.splitlines()[0] == "👑 **Cap** — 1900 · Gold"
    assert "**New** — — · Unranked" in roster
    assert embed.thumbnail.url == f"{SITE}/assets/img/teams/delight-esports.png"
    assert embed.url == team_url(SITE, "delight-esports") == f"{SITE}/team.html?t=delight-esports"
    (button,) = team_view(SITE, "delight-esports").children
    assert button.url == f"{SITE}/team.html?t=delight-esports"


def test_founding_team_and_empty_roster() -> None:
    summary = _summary(name="SHAHEEN", tag="SHN", slug="shaheen", is_founding=True)
    summary.rating = None
    embed = build_team_embed(summary, [], site_url=SITE)  # type: ignore[arg-type]
    assert embed.author.name == "Founding team of BRAWLISTAN"
    assert embed.fields[1].value == "Data unavailable"
    assert "/team add" in embed.fields[2].value
