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

### /setup reset
**Destructive** (docs/DECISIONS.md ADR-060) — permanently deletes every
role/category/channel `/setup` has created, then clears the idempotency
ledger so the next `/setup run` rebuilds from scratch. Does not touch
stored member/player/match/achievement data. Separate from `/setup run`
on purpose: `run` stays safe to re-run any time. Two-step confirmation —
a warning screen, then a modal requiring the exact text `DELETE`.

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

### /match create
Log a match directly between named players.

### /match view <match>
Inspect a match's current status.

### /report
Report a match result.

### /matches [user]
Show a Shaheen member's match history.

### /tournament create <name> <kind>
Create a tournament (staff only).

### /tournament register
Register for a tournament.

### /tournament start
Start a tournament and generate the bracket (staff only).

### /tournament bracket <tournament>
Show a tournament's current bracket.

### /tournament resolve
Force-resolve a stuck or disputed bracket match (staff only).

## Phase 8 — Moderation

All commands below require `require_staff_authorized()` (docs/PERMISSIONS.md)
and log to `#mod-log` (docs/DECISIONS.md ADR-065). Destructive actions
(`/clearwarnings`, `/kick`, `/ban`) go through `ConfirmView` first.

### /warn <user> <reason>
Record a warning against a member — best-effort DMs them, posts to
`#mod-log`, confirms to the moderator. Not FK'd through `/link` — a
member can be warned whether or not they've ever linked a Brawlhalla
profile.

### /warnings <user>
List a member's active warnings (reason, issuer, timestamp).

### /clearwarnings <user>
Soft-clears every active warning for a member after confirmation —
rows stay in the table (`active=False`) for the audit trail, nothing is
deleted.

### /kick <user> [reason]
Kick a member after confirmation.

### /ban <user> [reason] [delete_message_days]
Ban a member after confirmation.

### /timeout <user> <minutes> [reason]
Timeout a member for the given duration.

### /purge <amount> [user]
Bulk-delete up to `amount` recent messages in the current channel,
optionally filtered to one user's messages.

## Phase 8 — Chat gamification

No permission check on either command below — same "any member" posture
as `/profile` (docs/DECISIONS.md ADR-065).

### /level [user]
Show a member's chat level, XP, rank title and progress to the next
level. Defaults to the invoking member.

### /chatboard
Show the top 10 most active chatters in the server by chat XP (Discord
-only ranking — the public website's Community Activity section is
privacy-filtered to actively-linked members only, see ADR-065).

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
