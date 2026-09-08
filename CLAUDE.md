# Shaheen Bot — Claude Code Instructions

## Mission

Build Shaheen Bot as the core Discord application for Shaheen, a Pakistan-based
Brawlhalla clan. The project starts private with one member and must be designed
so it can grow into a full clan platform and later power a Shaheen website.

## Owner context

The project owner knows Python and Discord bot development. Prefer clear,
idiomatic Python over unnecessary abstractions. Explain important architectural
choices, but do not teach basic Python unless requested.

## Current priorities

1. Production-quality Discord server provisioning.
2. Clean Shaheen branding and onboarding.
3. Brawlhalla integration foundation.
4. Persistent clan/player data.
5. Architecture that can later expose the same data to a website.

## Technology baseline

- Python 3.12+
- discord.py 2.x
- PostgreSQL
- SQLAlchemy 2.x
- Alembic
- httpx
- Pydantic where useful
- pytest
- Ruff for lint/format
- Docker for repeatable deployment

Do not introduce a major framework or dependency without justification.

## Architecture rules

Keep these boundaries:

Discord UI/commands -> application services -> repositories/integrations

Discord commands must not contain raw SQL or direct Brawlhalla HTTP calls.
Brawlhalla API details must be isolated behind an integration client/service.
Database access must be isolated behind repositories/services.
Business rules must remain usable without Discord so the future website/API can
reuse them.

## Development behavior

Before coding:
- Read all docs in /docs.
- Inspect the existing repository.
- Identify contradictions or missing decisions.
- Produce a concise implementation plan.

Do not rewrite working code unnecessarily.
Do not add speculative features from later roadmap phases.
Do not duplicate configuration or business logic.
Prefer small, testable modules.

For every significant feature:
- implement
- add/update tests
- update documentation if behavior changed
- run relevant checks

## Safety

Never log Discord tokens, database passwords, API secrets, or other credentials.
Never commit .env files or secrets.
Validate all user input.
Use least-privilege Discord permissions.

## Definition of done

A feature is not done merely because the code runs. It should be:
- configurable
- testable
- logged appropriately
- permission-aware
- idempotent where applicable
- documented
- compatible with the existing architecture

## Product principle

Shaheen should feel like a real emerging esports clan, not a generic
multi-purpose Discord bot.
