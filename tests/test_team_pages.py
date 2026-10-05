"""Pre-rendered team pages (docs/DECISIONS.md ADR-117): real titles, SEO tags
and the team slug for every team, written automatically by the snapshot run."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("team_pages", ROOT / "scripts" / "team_pages.py")
assert spec and spec.loader
team_pages = importlib.util.module_from_spec(spec)
spec.loader.exec_module(team_pages)

TEMPLATE = (ROOT / "web" / "team.html").read_text(encoding="utf-8")
SHAHEEN = {
    "slug": "shaheen",
    "name": "SHAHEEN",
    "tag": "SHN",
    "country": "PK",
    "logo": "shaheen",
    "is_founding": True,
    "rank": 1,
    "rating": 2184,
    "members": 3,
}


def test_page_carries_the_teams_own_seo_and_slug() -> None:
    page = team_pages.render(TEMPLATE, SHAHEEN)
    assert '<base href="../../" />' in page
    assert "<title>SHAHEEN — Brawlistan Team</title>" in page
    assert "Pakistan&#x27;s founding Brawlhalla team on BRAWLISTAN" in page
    assert (
        '<link rel="canonical" href="https://itskaero.github.io/shaheen/teams/shaheen/" />' in page
    )
    assert "assets/img/teams/shaheen.png" in page
    assert 'data-team-slug="shaheen"' in page
    assert "#1 by team rating, 2,184 power, 3 players" in page


def test_names_are_escaped() -> None:
    page = team_pages.render(TEMPLATE, {**SHAHEEN, "is_founding": False, "name": '<b>"X"</b>'})
    assert "<b>" not in page.split("<body")[0]


def test_main_writes_pages_and_skips_unsafe_slugs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    data = tmp_path / "teams.json"
    data.write_text(json.dumps({"data": [SHAHEEN, {**SHAHEEN, "slug": "../evil"}]}))
    out = tmp_path / "teams"
    (out / "gone").mkdir(parents=True)
    monkeypatch.setattr(team_pages, "DATA", data)
    monkeypatch.setattr(team_pages, "OUT", out)
    team_pages.main()
    assert (out / "shaheen" / "index.html").exists()
    assert (out / "index.html").exists()  # /teams/ -> teams.html
    assert not (out / "gone").exists()
    assert not (tmp_path / "evil").exists()
