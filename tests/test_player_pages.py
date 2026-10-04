"""scripts/player_pages.py — per-player SEO pages (docs/DECISIONS.md ADR-106)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("player_pages", ROOT / "scripts/player_pages.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PLAYER = {
    "brawlhalla_id": 5734378,
    "slug": "kaero-5734378",
    "player_name": 'kaero. <"x">',
    "country": "PK",
    "team": "SHAHEEN",
    "rating": 1906,
    "tier": "Platinum 4",
}


def test_render_sets_the_player_title_meta_base_and_id() -> None:
    page = _load().render((ROOT / "web/player.html").read_text(), PLAYER)

    assert '<base href="../../" />' in page
    assert (
        "<title>kaero. &lt;&quot;x&quot;&gt; — Pakistan Brawlhalla Ranking | Brawlistan</title>"
        in page
    )
    assert 'data-player-id="5734378"' in page
    assert (
        '<link rel="canonical" href="https://itskaero.github.io/shaheen/player/kaero-5734378/" />'
        in page
    )
    assert "1,906 rating, Platinum 4, team SHAHEEN, Pakistan" in page
    assert '<"x">' not in page  # names are escaped wherever they land


def test_main_writes_pages_skips_unsafe_slugs_and_prunes_stale(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _load()
    data = tmp_path / "players.json"
    data.write_text(
        json.dumps({"data": [PLAYER, {**PLAYER, "slug": "../../etc", "brawlhalla_id": 1}]})
    )
    out = tmp_path / "player"
    (out / "gone-1").mkdir(parents=True)
    monkeypatch.setattr(module, "DATA", data)
    monkeypatch.setattr(module, "OUT", out)

    module.main()

    assert sorted(p.name for p in out.iterdir()) == ["kaero-5734378"]
    assert (out / "kaero-5734378" / "index.html").read_text().startswith("<!doctype html>")
