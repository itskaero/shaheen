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
rating/peak, global + region rank, region, clan "member since" date, chat
rank/level (docs/DECISIONS.md ADR-065), an achievement count with the
latest earned, and a link to the full website profile for what an embed
can't show — rating history and match record (ADR-059, extended in
ADR-067). `/rank`, `/stats`, `/legends` below still exist as focused
single-stat views.

### /rank [user]
Show current ranked information.

### /stats [user]
Show useful player statistics.

### /legends [user]
Show per-Legend statistics: games, wins, KOs, damage dealt, and falls
(ADR-067 — damage/falls already existed in the API response, just wasn't
shown here before).

## Phase 3 — Clan

### /leaderboard
Shaheen internal leaderboard.

### /achievements [user]
Show earned achievements.

### /history [user]
Show stored rating/history snapshots.

### /legendmeta
Clan-wide Legend popularity and win rate — every actively-linked member's
latest per-legend stats aggregated together, filtered to Legends with
enough combined games to be meaningful (docs/DECISIONS.md ADR-068).

### /spotlight <user> <note>
Feature a member in `#announcements` (staff only, `require_staff_
authorized()`) — a manual celebratory callout, no new data model (docs/
DECISIONS.md ADR-070).

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

### /rivalry <member_a> <member_b>
Head-to-head win/loss record between two clan members, from Shaheen's own
tracked confirmed matches — no Brawlhalla API involved (docs/DECISIONS.md
ADR-068).

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

### /verify <user>
Manually verify a new member — promotes Guest to Ally, granting access to
the gated categories (THE NEST, BRAWLHALLA, VOICE) hidden from everyone
until then (docs/DECISIONS.md ADR-069). Not destructive, no confirmation
step. Idempotent: a no-op on a member who already holds any rank role above
Guest. Best-effort DM to the member; logs to `#mod-log` like every other
command in this section.

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

### /suggest <text>
Anonymously post a clan suggestion to `#suggestions`, with 👍/👎 reactions
added automatically for voting (docs/DECISIONS.md ADR-070). No permission
check, same "any member" posture as `/level`.

## Weekly digest (standing job, not a command)

`ClanCog`'s second scheduled loop (alongside the ranking-snapshot loop,
docs/DECISIONS.md ADR-028) checks daily and posts every Sunday to
`#announcements`: top 3 rating gains this week, top 3 chatters by weekly XP,
and matches played. It also picks an MVP of the Week — biggest rating gain,
falling back to the top chatter in a quiet ranked week — and rotates the
🌟 MVP of the Week role onto them, removing it from last week's holder
(docs/DECISIONS.md ADR-070).

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
