# 🦅 Shaheen Bot

Custom Discord bot and future backend for **Shaheen**, a Pakistan-based
Brawlhalla clan.

**بلندیوں کی جانب — Higher Together**

## Status

Private / in development. Implemented so far:
- Phase 1 — foundation + `/setup` (launch mode also posts a self-assign
  opt-in roles panel to `#roles` — docs/DECISIONS.md ADR-058)
- Phase 2 — Brawlhalla identity: `/link`, `/unlink`, `/profile`, `/rank`,
  `/stats`, `/legends`
- Phase 3 — clan: scheduled rating/Legend snapshots, `/leaderboard`,
  `/achievements`, `/history`, Hall of Fame + milestone announcements
- Phase 4 — competition: `/challenge`, `/scrim`, `/match`, `/report`
  (with opponent confirm/dispute), `/matches`, `/tournament` (single-
  elimination brackets, 1v1 and 2v2). Launch mode also posts a standing
  spar kiosk to `#ranked` — its buttons run the same flow as `/scrim`
  (ADR-058)
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
- Phase 7 — deeper website data: player profiles now show legend mastery
  and match history (`GET /players/{id}/legends`, `.../matches`); a new
  tournament list + live bracket viewer (`GET /tournaments`,
  `GET /tournaments/{id}`, `tournaments.html` / `tournament.html`)
  (docs/DECISIONS.md ADR-051). One abstracted, restrained nod to Pakistani
  truck art as a homepage divider (ADR-052).
- Post-launch fixes (docs/DECISIONS.md ADR-059): `/link` takes an initial
  snapshot immediately, so a new member shows up on `/leaderboard` and the
  website right away instead of waiting for the next scheduled snapshot;
  every text channel now gets `/setup run mode:launch` starter content,
  each post fail-safe against a missing permission or deleted channel; the
  website's API calls time out with a clear "waking up" message instead of
  hanging forever; `/profile` is now a full one-look card (win-rate,
  global rank, region, member-since); Hall of Fame milestone/achievement
  posts include a branded generated image (`src/services/image_service.py`,
  Pillow, no external AI API).
- Phase 8 — moderation + chat gamification (docs/DECISIONS.md ADR-065): a
  restricted `#mod-log` channel plus `/warn`, `/warnings`, `/clearwarnings`,
  and staff-gated `/kick`/`/ban`/`/timeout`/`/purge` wrappers, everything
  logged with an audit trail. Message-based chat XP/leveling with
  Brawlhalla-themed rank titles (Hatchling → ... → Valhallan), `/level`,
  `/chatboard`, and a privacy-filtered "Community Activity" leaderboard on
  the website (`GET /community/activity` — linked members only, shown by
  Brawlhalla player name, never Discord identity — ADR-040). Per-member
  join/leave now post a branded welcome/goodbye card (reusing the owner's
  template art, ADR-062's text-effect stack) to `#welcome`, and new
  members auto-get the Guest role on arrival.

## Getting started

```bash
cp .env.example .env   # fill in DISCORD_TOKEN, GUILD_ID, DATABASE_URL, BRAWLHALLA_API_KEY
uv sync
docker compose up -d db
uv run alembic upgrade head
uv run pytest
uv run python src/main.py
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

## Deploying to production

Four pieces, deployed in this order (each depends on the one before it).
The bot and the website **share one Postgres database** — that's the
piece that ties the whole system together.

### 0. Discord + Brawlhalla prerequisites

1. **Discord bot:** [Discord Developer Portal](https://discord.com/developers/applications)
   → New Application → Bot tab → Reset Token, save it (`DISCORD_TOKEN`).
   Under Privileged Gateway Intents, enable **all three**: Presence,
   Server Members, and Message Content (ADR-012 — the bot requests every
   intent). Under OAuth2 → URL Generator, check scopes `bot` and
   `applications.commands`; for bot permissions, grant only what
   `docs/PERMISSIONS.md` actually calls for (Manage Roles, Manage
   Channels, Send Messages, Embed Links, etc. — not Administrator, per
   that doc's own rule). Open the generated URL and invite it to your
   server. Get the server's ID (right-click the server icon → Copy Server
   ID, with Developer Mode on) — that's `GUILD_ID`.
2. **Brawlhalla API key:** request one per `docs/DECISIONS.md` ADR-022
   (`api@brawlhalla.com`, verify current requirements at
   [dev.brawlhalla.com](https://dev.brawlhalla.com/)) — `BRAWLHALLA_API_KEY`.

### 1. Database + API, on Render (free)

In the [Render dashboard](https://dashboard.render.com), New → Blueprint →
point it at this repo. Render reads `render.yaml` and provisions a free
web service (the API) plus a free Postgres database. After the first
deploy:

- Set `DISCORD_TOKEN`, `GUILD_ID`, and `BRAWLHALLA_API_KEY` on the
  `shaheen-api` service (the API process never reads their values, but
  `Settings` requires them present — ADR-041; never commit real secrets).
- Copy the service's public URL (`https://shaheen-api-xxxx.onrender.com`)
  — the website needs it in step 3.
- Open the `shaheen-db` database → copy its **External Database URL**
  (not the internal one — the bot in step 2 connects from outside
  Render's network). The bot needs this as its `DATABASE_URL`.

The free plan sleeps after 15 minutes idle (first request after that is
slow, ~30-60s) and its Postgres database expires after 90 days unless
upgraded — fine for a small clan site, revisit if that stops being true.

### 2. Bot, on Fly.io (free)

The bot holds a persistent connection to Discord, so it can't live on
Render's free tier the way the API does (that tier is request-driven and
sleeps without inbound HTTP, which would drop the bot's connection —
docs/DECISIONS.md ADR-053). Fly.io's free small-VM allowance covers a
single always-on worker like this comfortably, deploying the same
`Dockerfile` the API uses via the checked-in `fly.toml`:

```bash
flyctl auth login
flyctl apps create shaheen-bot   # or your own name — update fly.toml's `app` to match
flyctl secrets set \
  DISCORD_TOKEN=... \
  GUILD_ID=... \
  DATABASE_URL=<the Render External Database URL from step 1> \
  BRAWLHALLA_API_KEY=...
flyctl deploy
```

`flyctl deploy` again any time you push changes. `flyctl logs` tails the
running bot.

### 3. Frontend, on GitHub Pages (free)

One-time setup — repo Settings → Pages → Source: "GitHub Actions". Set
`web/assets/js/config.js`'s `API_BASE_URL` to the Render URL from step 1
and push to `main`; `.github/workflows/pages.yml` deploys `web/`
automatically on every push that touches it (or run it manually from the
Actions tab).

### 4. First run

In Discord, run `/setup run mode:launch` (needs the server owner,
Administrator, or — once it exists — 👑 SHAHEEN LEADER). This provisions
roles/categories/channels and posts the welcome/rules embeds. `/setup
verify` confirms everything matches; `/setup status` shows the last run.
The website will read as empty (0 members, no leaderboard) until members
run `/link` — that's expected, not a bug.

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
