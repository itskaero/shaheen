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

### /unlink
Remove the active player association after confirmation.

### /profile [user]
Show Shaheen member + Brawlhalla profile.

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

## UX requirements

Use Discord slash commands, embeds and buttons/selects where they improve UX.
Messages should be concise, branded and actionable.
Do not expose raw exception messages or external API errors to users.
