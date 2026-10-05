"""Write web/teams/<slug>/index.html for every team.

    python3 scripts/team_pages.py

GitHub Pages can't route /teams/:slug, so each team gets a real page ahead of
time (docs/DECISIONS.md ADR-117), the same way players do (ADR-106,
scripts/player_pages.py): web/team.html with a <base> back to the site root,
the team's own title, description, canonical URL and Open Graph/Twitter tags
(its logo as the preview image), and <body data-team-slug> so the page script
knows which team to load.

Reads web/data/teams.json (written by the snapshot workflow just before this
runs). Standard library only. Pages for teams that no longer exist are
removed. A team created since the last run still opens: 404.html sends
/teams/<slug>/ to team.html?t=<slug> until its page is written.
"""

from __future__ import annotations

import html
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
TEMPLATE = WEB / "team.html"
DATA = WEB / "data" / "teams.json"
OUT = WEB / "teams"
SITE_URL = "https://itskaero.github.io/shaheen"
SLUG = re.compile(r"^[a-z0-9-]{1,48}$")
COUNTRIES = {"PK": "Pakistan"}


def _set(page: str, pattern: str, replacement: str) -> str:
    updated, count = re.subn(pattern, lambda _m: replacement, page, count=1)
    if count != 1:
        raise SystemExit(f"team.html no longer has a tag matching {pattern!r}")
    return updated


def _meta(attr: str, key: str, value: str) -> str:
    return f'<meta {attr}="{key}" content="{html.escape(value)}" />'


def describe(team: dict[str, object]) -> tuple[str, str]:
    name = str(team["name"])
    title = f"{name} — Brawlistan Team"
    if team.get("is_founding"):
        lead = f"{name}, Pakistan's founding Brawlhalla team on BRAWLISTAN."
    else:
        country = COUNTRIES.get(str(team.get("country")), "")
        where = f"{country} " if country else ""
        lead = f"{name} [{team.get('tag')}], a {where}Brawlhalla team on BRAWLISTAN."
    facts = [
        f"#{team['rank']} by team rating" if isinstance(team.get("rank"), int) else None,
        f"{team['rating']:,} power" if isinstance(team.get("rating"), int) else None,
        f"{team['members']} players" if isinstance(team.get("members"), int) else None,
    ]
    summary = ", ".join(f for f in facts if f)
    return title, lead + (
        f" {summary[0].upper()}{summary[1:]}." if summary else ""
    ) + " Roster, seasons and results."


def render(template: str, team: dict[str, object]) -> str:
    slug = str(team["slug"])
    url = f"{SITE_URL}/teams/{slug}/"
    title, description = describe(team)
    image = (
        f"{SITE_URL}/assets/img/teams/{team['logo']}.png"
        if isinstance(team.get("logo"), str) and SLUG.match(str(team["logo"]))
        else f"{SITE_URL}/assets/img/brawlistan/og-card.jpg"
    )
    e = html.escape
    social = "\n  ".join(
        [
            _meta("property", "og:url", url),
            _meta("name", "twitter:title", title),
            _meta("name", "twitter:description", description),
        ]
    )
    replacements = (
        (r"<head>", '<head>\n  <base href="../../" />'),
        (r"<title>.*?</title>", f"<title>{e(title)}</title>"),
        (r'<meta name="description" content="[^"]*" />', _meta("name", "description", description)),
        (r'<link rel="canonical" href="[^"]*" />', f'<link rel="canonical" href="{url}" />'),
        (r'<meta property="og:title" content="[^"]*" />', _meta("property", "og:title", title)),
        (
            r'<meta property="og:description" content="[^"]*" />',
            _meta("property", "og:description", description) + "\n  " + social,
        ),
        (r'<meta property="og:image" content="[^"]*" />', _meta("property", "og:image", image)),
        (
            r'<body class="bl" data-page="teams">',
            f'<body class="bl" data-page="teams" data-team-slug="{slug}">',
        ),
    )
    page = template
    for pattern, replacement in replacements:
        page = _set(page, pattern, replacement)
    return page


def main() -> None:
    if not DATA.exists():
        print("No web/data/teams.json yet; nothing to generate.")
        return
    teams = json.loads(DATA.read_text(encoding="utf-8"))["data"]
    template = TEMPLATE.read_text(encoding="utf-8")
    OUT.mkdir(parents=True, exist_ok=True)

    wanted: set[str] = set()
    for team in teams:
        slug = str(team.get("slug", ""))
        if not SLUG.match(slug):
            continue  # never trust a value that becomes a path
        wanted.add(slug)
        target = OUT / slug / "index.html"
        target.parent.mkdir(exist_ok=True)
        target.write_text(render(template, team), encoding="utf-8")

    # /teams/ itself goes to the list page.
    (OUT / "index.html").write_text(
        '<!doctype html><meta charset="utf-8">'
        '<meta http-equiv="refresh" content="0; url=../teams.html">'
        '<link rel="canonical" href="../teams.html"><title>Teams — BRAWLISTAN</title>'
        '<a href="../teams.html">Teams</a>\n',
        encoding="utf-8",
    )
    for stale in OUT.iterdir():
        if stale.is_dir() and stale.name not in wanted:
            shutil.rmtree(stale)
    print(f"Wrote {len(wanted)} team page(s).")


if __name__ == "__main__":
    main()
