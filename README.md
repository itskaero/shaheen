# 🦅 Shaheen Bot

Custom Discord bot and future backend for **Shaheen**, a Pakistan-based
Brawlhalla clan.

**بلندیوں کی جانب — Higher Together**

## Status

Private / in development. Phase 1 (foundation + `/setup`) is implemented.

## Getting started

```bash
cp .env.example .env   # fill in DISCORD_TOKEN, GUILD_ID, DATABASE_URL
uv sync
docker compose up -d db
uv run alembic upgrade head
uv run pytest
uv run python -m src.main
```

Or run everything in Docker: `docker compose up --build`.

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
