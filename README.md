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
uv run uvicorn api.app:app --reload
```

(Docker Compose also starts it as the `web` service, on port 8000.)

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
