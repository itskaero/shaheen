# Command Specification

## Phase 1 — Setup

### /setup
Interactive server setup wizard.

Requirements:
- administrator/leader permission
- preflight permission checks
- development or launch mode
- confirmation before destructive changes
- idempotent
- final verification report

### /setup status
Show whether expected Shaheen resources exist and whether permissions match.

### /setup verify
Run non-destructive validation and report discrepancies.

## Phase 2 — Identity and Brawlhalla

### /link
Associate a Discord user with a Brawlhalla player ID.
Flow:
1. request ID
2. validate
3. query Brawlhalla
4. show discovered player
5. require confirmation
6. persist relationship
7. assign appropriate role
8. take an initial rating/Legend snapshot (docs/DECISIONS.md ADR-059) —
   without this the member wouldn't appear on `/leaderboard` or the
   website until the next scheduled snapshot, up to
   `SNAPSHOT_INTERVAL_HOURS` later

### /unlink
Remove the active player association after confirmation.

### /profile [user]
One-look profile card: Brawlhalla name/level, games/wins/win-rate, tier/
rating/peak, global rank, region, and clan "member since" date
(docs/DECISIONS.md ADR-059). `/rank`, `/stats`, `/legends` below still
exist as focused single-stat views.

### /rank [user]
Show current ranked information.

### /stats [user]
Show useful player statistics.

### /legends [user]
Show per-Legend statistics.

## Phase 3 — Clan

### /leaderboard
Shaheen internal leaderboard.

### /achievements [user]
Show earned achievements.

### /history [user]
Show stored rating/history snapshots.

## Phase 4 — Competition

### /challenge <user>
Create a clan challenge.

### /scrim
Create/announce a scrim.

### /match
Create or inspect a match.

### /report
Report a match result.

## Standing panels

Not slash commands — persistent, interactive messages `/setup run
mode:launch` posts once and that keep working across bot restarts
(docs/DECISIONS.md ADR-058). See docs/DISCORD_SPEC.md's "Standing panels"
section for which channel gets what.

- **Opt-in role panel** (🎭 roles) — toggle buttons for opt-in pings/tags.
  No slash command equivalent; members click to add/remove.
- **Spar kiosk** (🏆 ranked) — 🥊 1v1 / 👥 2v2 buttons that run the exact
  same flow as `/scrim`, just without typing the command.

Every other text channel also gets a short static intro embed in launch
mode (docs/DECISIONS.md ADR-059) — see docs/DISCORD_SPEC.md's "Standing
panels" section for the full list. A missing permission or a since-
deleted channel can't abort the rest: each channel's post is wrapped in
its own `try/except`, logged and skipped rather than failing the whole
`/setup run`.

## UX requirements

Use Discord slash commands, embeds and buttons/selects where they improve UX.
Messages should be concise, branded and actionable.
Do not expose raw exception messages or external API errors to users.
