# Architecture Decisions

## ADR-001 — Python
Decision: Python 3.12+.

Reason: The project owner already knows Python and Discord bot development.

## ADR-002 — discord.py
Decision: discord.py 2.x.

Reason: Mature Discord Python ecosystem and owner familiarity.

## ADR-003 — PostgreSQL
Decision: PostgreSQL.

Reason: Persistent relational clan/player/history data and future website use.

## ADR-004 — SQLAlchemy + Alembic
Decision: SQLAlchemy 2.x with Alembic migrations.

Reason: Explicit database layer and controlled schema evolution.

## ADR-005 — Brawlhalla integration boundary
Decision: All external Brawlhalla API access is isolated behind an integration
client/service.

Reason: Prevent Discord code from becoming coupled to external API details.

## ADR-006 — Server setup is idempotent
Decision: /setup must be safe to run repeatedly.

Reason: Rapid provisioning and repair are core requirements.

## ADR-007 — One Shaheen bot
Decision: Build Shaheen-specific functionality into one custom bot instead of
depending on multiple generic bots for core functionality.

Reason: Consistent UX and a clean path to Brawlhalla/database/website integration.

## ADR-008 — English-first Discord naming
Decision: Channel names remain primarily English, with Urdu in descriptions,
branding and selected messages.

Reason: Discoverability for Pakistani and international Brawlhalla players.

## ADR-009 — Private development
Decision: The server remains private until the bot and initial web presence are
ready for launch.

Reason: Avoid exposing an unfinished public experience.
