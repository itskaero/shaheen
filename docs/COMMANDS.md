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

### /apply
Apply to join the **clan roster**. Opens a five-field form (Brawlhalla/Steam
ID, region, current rank, why Shaheen, optional referrer) and files it for
staff review (docs/DECISIONS.md ADR-089). The same form opens from the
button in #📝-apply. One open application at a time; declined applicants can
reapply after 14 days. An approved application promotes straight to **Trial
Shaheen**, skipping Ally entirely — this is a different, stricter outcome
than `/verify` below (docs/DECISIONS.md ADR-092). Blocked for anyone who
already holds Trial Shaheen or above; an Ally (let in via `/verify`, not
clan membership) can still apply.

### /application
Check the status of your own application, including any staff note.

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
rating/peak, global + region rank, region, favourite Legend, a derived
playstyle (docs/DECISIONS.md ADR-096 — a heuristic label, not a
Brawlhalla-reported stat), clan "member since" date, chat rank/level
(docs/DECISIONS.md ADR-065), an `earned/total` achievement count with the
latest earned, clan role, Discord account age and this-server join date
(ADR-096 — the only place these show, since nothing in the database
persists per-member Discord timestamps), and a link to the full website
profile for what an embed can't show — rating history and match record
(ADR-059, extended in ADR-067). Its image is a strip of the member's top 3
Legends' portraits (docs/DECISIONS.md ADR-098). `/rank`, `/stats`,
`/legends` below still exist as focused single-stat views.

### /rank [user]
Show current ranked information.

### /stats [user]
Show useful player statistics.

### /legends [user]
Show per-Legend statistics: games, wins, KOs, damage dealt, and falls
(ADR-067 — damage/falls already existed in the API response, just wasn't
shown here before). Each Legend the member has played in ranked is also
annotated with its ranked rating, tier and W/L — data fetched on every
snapshot since Phase 2 and discarded unread until ADR-084. Its image is a
portrait strip of the top 5 Legends (ADR-098).

### /compare <member_a> [member_b]
Side-by-side ranked and lifetime stats for two linked members (ADR-084).
`/rivalry` covers the head-to-head *match record*; this covers stats.
Defaults `member_b` to you.

### /refresh
Pull your own Brawlhalla stats now instead of waiting for the scheduled
snapshot loop (ADR-084). Rate-limited to one refresh per member every 15
minutes, measured off the last stored snapshot so it survives a restart.
Awards any achievements the fresh numbers earned.

### /lookup <identifier>
Check any Brawlhalla player's standing **without linking** — takes a
Steam64 ID or a Brawlhalla player ID (Brawlhalla's API has no username
search), and reports where that rating would slot into Shaheen's ladder:
the rank it would hold and the nearest member above and below with deltas
(ADR-083). Read-only — nothing is stored and no link is created.

## Phase 3 — Clan

### /leaderboard
Shaheen internal leaderboard — linked clan members only (`/link`).

### /pakistan leaderboard
The Pakistan leaderboard (docs/DECISIONS.md ADR-099): Pakistan's ranked
players, clan or not, current season only. 🦅 marks Shaheen members.

### /pakistan join <identifier>
Put your own Brawlhalla account (Brawlhalla or Steam64 ID) on the Pakistan
leaderboard, with a confirm step. One entry per member — joining with a
different account replaces the old one. Opt-in only, clan members included:
Brawlhalla reports a server region, never a country, so nothing is assumed.
Doesn't make you a clan member — that's `/apply`.

### /pakistan leave
Take your own entry off the Pakistan leaderboard.

### /pakistan add <identifier> *(staff)*
Add any Pakistani player — no Discord membership needed. If they join the
server later, `/pakistan join` with the same ID makes the entry theirs.
The board is capped at 150 players (API quota).

### /pakistan remove <brawlhalla_id> *(staff)*
Remove a player from the Pakistan leaderboard.

**Claimed spots (ADR-100).** An entry someone `/pakistan join`ed is
*claimed*; a staff-added one is *unclaimed* until its player joins and
claims it. Claimed players in the top 10 get the 🇵🇰 Pakistan Top 10 role
automatically (re-checked every six-hourly snapshot). Every Sunday the bot
posts the standings in #pakistan-chat, marks unclaimed spots, and pings the
week's biggest claimed climbers. The website's Pakistan tab tags each row
✓ Verified or Unclaimed, with a "Claim this spot" link to the Discord.

### /achievements [user]
Show earned achievements.

### /history [user]
Show stored rating/history snapshots.

### /legendmeta
Clan-wide Legend popularity and win rate — every actively-linked member's
latest per-legend stats aggregated together, filtered to Legends with
enough combined games to be meaningful (docs/DECISIONS.md ADR-068), with a
portrait strip of the top 5 (ADR-098).

### /clanstats
Clan-wide aggregate: combined games and wins, average and median rating,
highest-rated member, tier spread, region split and most-played Legends
(ADR-084). Median sits next to the mean because one high-rated member
drags an average well away from the clan's typical standing.

### /applications
List applications awaiting review (staff only). Each one is also posted to
#📥-applications with Approve / Decline buttons; approving grants member
access and DMs the applicant, declining asks for a reason that is sent with
the decision. An application can only be decided once.

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
Manually grant general **community access** — promotes Guest to Ally,
granting access to the gated categories (THE NEST, BRAWLHALLA, VOICE) hidden
from everyone until then (docs/DECISIONS.md ADR-069). Not clan roster
membership — that's what an approved `/apply` grants instead, promoting
straight to Trial Shaheen (docs/DECISIONS.md ADR-092). Not destructive, no
confirmation step. Idempotent: a no-op on a member who already holds any
rank role above Guest. Best-effort DM to the member; logs to `#mod-log` like
every other command in this section.

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

### /untimeout <user> [reason]
Remove an active timeout early. Not destructive, no confirmation step.

### /unban <user> [reason]
Remove a ban. Not destructive, no confirmation step; a no-op error if the
user wasn't banned.

### /purge <amount> [user]
Bulk-delete up to `amount` recent messages in the current channel,
optionally filtered to one user's messages.

### /lock [channel] [reason]
Set `send_messages=False` for `@everyone` on a channel (defaults to the
current one). A stopgap for raids/incidents, not a `/setup`-managed state —
the next `/setup run` reconciles the channel's overwrites back to its
normal spec and clears the lock (docs/PERMISSIONS.md), so staff should
`/unlock` when done rather than relying on that.

### /unlock [channel]
Undo a `/lock` — clears the `send_messages` overwrite for `@everyone`
rather than forcing it back to `True`, so it doesn't accidentally grant
send access to a channel that's normally staff-only-send.

### /slowmode <seconds> [channel]
Set a channel's slowmode delay (0–21600s; 0 disables it).

### /nickname <user> [nickname] [reason]
Set or reset (omit `nickname`) a member's server nickname.

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

### /anthem
Link to Shaheen's Music Library page on the website (docs/DECISIONS.md
ADR-097). No permission check, ephemeral reply.

## Phase 9 — Emoji pack

Requires `require_staff_authorized()`. See docs/DECISIONS.md ADR-090.

### /emoji sync
Uploads Shaheen's curated legend-expression emoji pack (`src/assets/emoji/`)
to the server. Never overwrites an existing emoji by name — a collision is
reported and skipped, not clobbered. Safe to re-run any time (after adding
files to the pack, or on a guild whose emoji were reset); stops cleanly and
reports which files didn't fit once the server is out of static emoji
slots.

### /emoji browse
Interactive picker (docs/DECISIONS.md ADR-092) over the ~260-crop candidate
pool at `src/assets/emoji_candidates/` — a superset of `/emoji sync`'s fixed
24, covering 16 legends' full sprite sheets, each expression browsable one
at a time. Pick a legend, step through its crops with ◀/▶, **➕ Add** to
queue the one on screen (renaming it first via a modal), **✅ Done** to
upload everything queued through the same `EmojiService` sync path as
`/emoji sync`. Session-only view, 5-minute idle timeout, usable only by
whoever ran the command.

### /emoji clear
**DESTRUCTIVE, admin only** (docs/DECISIONS.md ADR-094 — a tighter gate
than `sync`/`browse`'s staff check). Deletes every custom emoji in the
server, regardless of origin — not just the Shaheen pack, anything staff
ever added by hand too. Two-step confirmation matching `/setup reset`: a
warning screen, then a modal requiring the exact text `DELETE ALL EMOJI`.
Cannot be undone; the pack itself can be restored afterward with
`/emoji sync`, nothing else can.

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
