"""Write web/player/<slug>/index.html for every tracked player.

    python3 scripts/player_pages.py

GitHub Pages can't route /player/:slug, so each player gets a real page
ahead of time (docs/DECISIONS.md ADR-106). It is web/player.html with a
<base> pointing back at the site root, the player's own title, description,
canonical URL and Open Graph/Twitter tags, and <body data-player-id> so the
profile script knows who to load. Search engines and link previews see a
page about that player; visitors get the normal profile.

Reads web/data/players.json (written by the snapshot workflow just before
this runs). Standard library only, so the workflow needs no install step.
Pages for players no longer tracked are removed.
"""

from __future__ import annotations

import html
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
TEMPLATE = WEB / "player.html"
DATA = WEB / "data" / "players.json"
OUT = WEB / "player"
SITE_URL = "https://itskaero.github.io/shaheen"
SLUG = re.compile(r"^[a-z0-9-]{1,64}$")
COUNTRIES = {"PK": "Pakistan"}


def _set(page: str, pattern: str, replacement: str) -> str:
    updated, count = re.subn(pattern, lambda _m: replacement, page, count=1)
    if count != 1:
        raise SystemExit(f"player.html no longer has a tag matching {pattern!r}")
    return updated


def _meta(attr: str, key: str, value: str) -> str:
    return f'<meta {attr}="{key}" content="{html.escape(value)}" />'


def render(template: str, player: dict[str, object]) -> str:
    name = str(player["player_name"])
    slug = str(player["slug"])
    url = f"{SITE_URL}/player/{slug}/"
    title = f"{name} — Pakistan Brawlhalla Ranking | Brawlistan"
    facts = [
        f"{player['rating']:,} rating" if isinstance(player.get("rating"), int) else None,
        str(player["tier"]) if player.get("tier") else None,
        f"team {player['team']}" if player.get("team") else None,
        COUNTRIES.get(str(player.get("country"))),
    ]
    summary = ", ".join(f for f in facts if f)
    description = (
        f"{name}'s Brawlhalla profile on BRAWLISTAN"
        + (f": {summary}." if summary else ".")
        + " Rating history, legends, seasons and achievements."
    )
    e = html.escape
    pid = int(str(player["brawlhalla_id"]))
    replacements = (
        (r"<head>", '<head>\n  <base href="../../" />'),
        (r"<title>.*?</title>", f"<title>{e(title)}</title>"),
        (r'<meta name="description" content="[^"]*" />', _meta("name", "description", description)),
        (r'<link rel="canonical" href="[^"]*" />', f'<link rel="canonical" href="{url}" />'),
        (r'<meta property="og:title" content="[^"]*" />', _meta("property", "og:title", title)),
        (
            r'<meta property="og:description" content="[^"]*" />',
            _meta("property", "og:description", description),
        ),
        (r'<meta property="og:url" content="[^"]*" />', _meta("property", "og:url", url)),
        (r'<meta name="twitter:title" content="[^"]*" />', _meta("name", "twitter:title", title)),
        (
            r'<meta name="twitter:description" content="[^"]*" />',
            _meta("name", "twitter:description", description),
        ),
        (
            r'<body class="bl" data-page="players">',
            f'<body class="bl" data-page="players" data-player-id="{pid}">',
        ),
    )
    page = template
    for pattern, replacement in replacements:
        page = _set(page, pattern, replacement)
    return page


def main() -> None:
    if not DATA.exists():
        print("No web/data/players.json yet; nothing to generate.")
        return
    players = json.loads(DATA.read_text())["data"]
    template = TEMPLATE.read_text()
    OUT.mkdir(parents=True, exist_ok=True)

    wanted: set[str] = set()
    for player in players:
        slug = str(player.get("slug", ""))
        if not SLUG.match(slug):
            continue  # never trust a value that becomes a path
        wanted.add(slug)
        target = OUT / slug / "index.html"
        target.parent.mkdir(exist_ok=True)
        target.write_text(render(template, player))

    for stale in OUT.iterdir():
        if stale.is_dir() and stale.name not in wanted:
            shutil.rmtree(stale)
    print(f"Wrote {len(wanted)} player page(s).")


if __name__ == "__main__":
    main()
