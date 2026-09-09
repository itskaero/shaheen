# 🦅 Shaheen Bot

Custom Discord bot and future backend for **Shaheen**, a Pakistan-based
Brawlhalla clan.

**بلندیوں کی جانب — Higher Together**

## Status

Private / in development. Implemented so far:
- Phase 1 — foundation + `/setup`
- Phase 2 — Brawlhalla identity: `/link`, `/unlink`, `/profile`, `/rank`,
  `/stats`, `/legends`
- Phase 3 — clan: scheduled rating/Legend snapshots, `/leaderboard`,
  `/achievements`, `/history`, Hall of Fame + milestone announcements
- Phase 4 — competition: `/challenge`, `/scrim`, `/match`, `/report`
  (with opponent confirm/dispute), `/matches`, `/tournament` (single-
  elimination brackets, 1v1 and 2v2)
- Phase 5 — website: read-only, unauthenticated FastAPI JSON API sharing
  the bot's services/repositories/database — `GET /clan`,
  `GET /leaderboard`, `GET /players/{brawlhalla_id}`,
  `GET /players/{brawlhalla_id}/history`, `GET /health`
- Phase 6 — public frontend: a static website (`web/`) — home, clan,
  leaderboard, and player profile/rating-history pages — that calls the
  Phase 5 API directly from the browser. Free to host: the site on GitHub
  Pages, the API + database on Render's free tier. A dark, neon-glow
  esports-team-site look (docs/DECISIONS.md ADR-047/048/049) built around
  the clan's own Discord art: an animated crest-logo hero, a scrolling
  ticker marquee, gradient shine text, cursor-spotlight cards, angular
  neon buttons/badges, tier-colored rank badges, player avatars. The
  homepage is a scroll-triggered landing page with live animated stat
  counters (docs/DECISIONS.md ADR-050), and the player rating-history
  chart has gridlines, a peak-rating overlay, and a hover tooltip.

## Getting started

```bash
cp .env.example .env   # fill in DISCORD_TOKEN, GUILD_ID, DATABASE_URL, BRAWLHALLA_API_KEY
uv sync
docker compose up -d db
uv run alembic upgrade head
uv run pytest
uv run python -m src.main
```

Or run everything in Docker: `docker compose up --build`.

To run the website API on its own:

```bash
uv run uvicorn api.app:app --app-dir src --reload
```

(Docker Compose also starts it as the `web` service, on port 8000.)

The site uses two pieces of the clan's own Discord art (docs/DECISIONS.md
ADR-047/ADR-048):
- `web/assets/img/banner.jpg` / `.webp` — the wide action-scene banner,
  used as the homepage's `.cinematic-strip` and every inner page's
  `.page-banner`. Swap in an updated one by replacing both files (keep the
  ~2.5:1 width:height ratio) — no other change needed.
- `web/assets/img/logo-full.*` / `logo-icon.*` — the circular crest, used
  as the animated homepage hero (`logo-full`, includes the wordmark) and
  the nav/footer/favicon mark (`logo-icon`, crest only — legible at small
  sizes). Regenerate `favicon-32.png` / `favicon-48.png` /
  `apple-touch-icon.png` from a new crest at 32/48/180px square.

To preview the static frontend locally, point `web/assets/js/config.js`'s
`API_BASE_URL` at your running API (`http://127.0.0.1:8000` by default),
then serve the `web/` folder with any static file server, e.g.
`python3 -m http.server 8080 --directory web`.

## Deploying the website (free hosting)

Two independent, free deployments — see `docs/DECISIONS.md` ADR-045:

1. **API + database, on [Render](https://render.com):** in the Render
   dashboard, New → Blueprint → point it at this repo. Render reads
   `render.yaml` and provisions a free web service plus a free Postgres
   database. After the first deploy, set the `DISCORD_TOKEN`, `GUILD_ID`,
   and `BRAWLHALLA_API_KEY` environment variables on the `shaheen-api`
   service (the API doesn't use their values, but `Settings` requires them
   — never commit real secrets to the repo). Copy the service's public
   `https://shaheen-api-xxxx.onrender.com` URL.

   The free plan sleeps after 15 minutes idle (first request after that is
   slow, ~30-60s) and its Postgres database expires after 90 days unless
   upgraded — fine for a small clan site, revisit if that stops being true.

2. **Frontend, on GitHub Pages:** one-time setup — repo Settings → Pages →
   Source: "GitHub Actions". Set `web/assets/js/config.js`'s
   `API_BASE_URL` to the Render URL from step 1 and push to `main`;
   `.github/workflows/pages.yml` deploys `web/` automatically on every push
   that touches it (or run it manually from the Actions tab).

## Goals

- one-command Discord server setup
- Shaheen-branded onboarding
- Brawlhalla player integration
- clan statistics and history
- competitive clan systems
- future website integration

## Documentation

Start with `CLAUDE.md`, then read:
- `docs/PRODUCT.md`
- `docs/ARCHITECTURE.md`
- `docs/DISCORD_SPEC.md`
- `docs/COMMANDS.md`
- `docs/BRAWLHALLA_API.md`
- `docs/DATABASE.md`
- `docs/SETUP_FLOW.md`
- `docs/PERMISSIONS.md`
- `docs/BRAND.md`
- `docs/ROADMAP.md`
- `docs/DECISIONS.md`
- `docs/DEVELOPMENT.md`
