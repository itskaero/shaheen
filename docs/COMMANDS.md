# Command Specification

## Phase 1 — Setup

### /setup run [mode]
Creates or reuses the BRAWLISTAN roles and channels (docs/DECISIONS.md
ADR-109): 7 roles, 4 categories, 12 text channels. Idempotent, with a
preview and confirm. It **never sets permissions**: roles are created with
none, channels get no overwrites, and existing roles and channels keep
whatever permissions the owner gave them (role repair only renames). With
`mode:launch` it also posts the welcome, rules and channel intro messages,
once each.

Requirements: guild owner, `BOT_OWNER_ID`, Administrator, or the Founder or
Admin role; the bot needs Manage Roles and Manage Channels.

### /setup roles
Roles only: creates missing roles and reuses existing ones (by the setup
ledger, then by exact name). It never duplicates a role and never grants a
permission. Channels and the setup mode are left alone.

### /setup status
Show whether the expected BRAWLISTAN roles and channels exist.

### /setup verify
Run non-destructive validation and report discrepancies.

### /setup restructure
**Destructive** (ADR-109). Lists every role, category and channel `/setup`
created for the old SHAHEEN layout that BRAWLISTAN no longer uses, then
deletes them after a confirm. Ledger-only: anything the owner made by hand
is never listed or touched, and stored player, ranking and match data is
unaffected. A resource that fails to delete stays listed for the next run.
Channels carried over from SHAHEEN keep their old permission overwrites;
review them afterwards.

### /setup reset
**Destructive** (docs/DECISIONS.md ADR-060) — permanently deletes every
role/category/channel `/setup` has created, then clears the idempotency
ledger so the next `/setup run` rebuilds from scratch. Does not touch
stored member/player/match/achievement data. Separate from `/setup run`
on purpose: `run` stays safe to re-run any time. Two-step confirmation —
a warning screen, then a modal requiring the exact text `DELETE`.

## Phase 2 — Identity and Brawlhalla

### /link [identifier]
Two ways to link (docs/DECISIONS.md ADR-107):
- **`/link` with no identifier** gives you a one-time code (`XXXX-XXXX`, 15
  minutes, single use; asking again replaces it). Open your profile on the
  website, choose **Claim this profile** and enter it.
- **`/link <Brawlhalla or Steam64 ID>`** links straight from Discord, as before.

Either way, an account already linked to (or claimed on the Pakistan board by)
another member is refused: linking is never a takeover. Linking proves you own
the Discord account; staff `/verify` confirms you own the Brawlhalla account.

The direct `/link <ID>` flow:
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

**Pakistan Seasons (ADR-102).** Both boards cover the current season, named
in the footer ("Pakistan Season 1 · Zarb-e-Shaheen · Brawlhalla S42"), with
that season's badge in the corner. Brawlhalla S42 is Pakistan Season 1, and
a new one starts every 13 weeks. The bot announces each new season once in
#announcements with its badge.

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

### /match report <match_id> <result>
Report a match result for the other side to confirm. (Was `/report` until
docs/DECISIONS.md ADR-111 gave `/report` to player reports.)

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

### /verify <user> [revoke] *(staff)*
Mark that a member really owns their linked Brawlhalla account (docs/DECISIONS.md
ADR-107). Staff check it themselves (for example a screenshot of the in-game
profile), then run this. It grants the Verified role once that role exists, and
shows "✓ Verified" on the website. `revoke:true` withdraws it. Logged to the audit
log. (Replaces the SHAHEEN-era `/verify`, which granted clan community access.)

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

### /clear <amount> [user]
Bulk-delete up to `amount` (1–100) recent messages in the current channel,
optionally filtered to one user's messages, and log it. (Was `/purge`
until ADR-111.)

### /lock [channel] [reason]
Set `send_messages=False` for `@everyone` on a channel (defaults to the
current one). A stopgap for raids/incidents that staff run by hand;
`/setup` never touches channel permissions (ADR-109), so `/unlock` when
done.

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

## Phase 10 — BRAWLISTAN network (docs/DECISIONS.md ADR-111)

None of these call the Brawlhalla API: they read what the snapshot loop
stored. Read-only replies are ephemeral.

### /ping
Gateway latency.

### /site
The website, as link buttons (Home, Rankings, Players, Tournaments).

### /rankings [board]
Pakistan's top 10 for `1v1` (default) or `2v2`, or `rising` (this week's
biggest rating gains). Placed players only; an empty board says "Data
unavailable".

### /season
The current Pakistan season: number, name (English and Urdu), Brawlhalla
season, dates and days left, with its card and a **Season page** button to
`seasons.html` (ADR-113).

### /legend <name>
How a Legend is played across every tracked Pakistani player: players,
lifetime games, win rate and popularity rank. Autocompletes names.

### /tournaments
The ten most recent tournaments and their status.

### /looking <mode>
Find a 1v1 sparring partner or a 2v2 game: posts a joinable card in
#looking-for-game (the same flow as `/scrim`). One every 2 minutes per
member.

### /report <reason> [player] [name]
Privately report a player to staff: a Discord member, or a Brawlhalla name
for someone outside the server. Creates a moderation record and posts a card
to #report (or `REPORT_CHANNEL_ID`) with the reporter, the reported player,
the reason, the source, the time and the status. The reason needs 10+
characters, you can't report yourself, and each member can send 3 reports
per 10 minutes. The website's Report Player (Stage 10) creates the same
record.

### /profile — View profile
`/profile` now carries a **View profile** button to the player's page on
the website.

### /announce <title> <message> [ping] *(staff)*
Post a branded announcement to #announcements (or
`ANNOUNCEMENT_CHANNEL_ID`) after a preview and confirm. Pings nobody unless
`ping` is `here` or `everyone`. Audit-logged.

### /feature [user] [brawlhalla_id] [note] [clear] *(staff)*
Set the website's Featured Player to a linked member or a tracked
Brawlhalla account, with an optional note; `clear:true` removes it. The
home page shows it (`GET /featured`) and falls back to the Pakistan #1 when
nobody is featured. Announced in #announcements unless `ANNOUNCE_FEATURED`
is off. Audit-logged.

### /access roles [join_role] [approved_role] [clear] *(Founder/Admin)*
Join access (ADR-123). The **approved role** lets a member into the server;
the **join role** is where new members wait while approval is on. Set either
or both; `clear:True` unsets both (only while approval is off). What each
role can see is your channel setup; the bot never changes permissions.
Refused: @everyone, integration roles, the bot-managed Player/Verified
roles, any role with staff permissions, and roles above the bot's or your
own highest role.

### /access approval <enabled> *(Founder/Admin)*
- **Off** (the default): a new member gets the approved role straight away.
- **On:** a new member gets the join role, and staff let them in with
  `/approval`. Needs both roles set.

Members get their role on join, or once they pass Discord's rules screening
if the server uses it. Turning approval off doesn't move anyone already
waiting; `/approval` them. Audit-logged.

### /access status *(Founder/Admin)*
Both roles, the switch, how many members are waiting, and anything missing
(an unset or deleted role, or the bot lacking Manage Roles).

### /approval <member> *(staff)*
Give a member the approved role and take away the join role. Says so if
they're already approved. Audit-logged.

### /sync *(Founder/Admin)*
Re-sync the bot's slash commands to the server, for example after a deploy
added commands.

### /team info [name]
A team's roster (captain marked 👑), player count, team rating and logo,
with a **Team page** button. Shows your own team when no name is given.
Team rating is the average current-season rating of the team's best three
placed players; with nobody placed it says "Data unavailable".

### /team leave
Leave your team. Your history on it is kept.

### /team tag <show>
Show or hide your team tag, e.g. **[SHN] kaero.**, before your name on the
rankings, Players page, your profile and `/rankings` (ADR-115). On by
default; hiding it keeps you on the team. Visitors can also hide every tag
on the Rankings page with its "Team tags" switch.

### /team add <name> [user] [brawlhalla_id] · /team remove … *(staff or that team's captain)*
Add a player to a team, or remove one. The player is a linked member or a
tracked Brawlhalla account. A player is on at most one team at a time:
someone on another team has to leave (or be removed) first. Rosters hold up
to 20 players. Audit-logged.

### /team create <name> <tag> [description] [colour] [colour2] *(staff)*
Create a team. Tags are 2–6 letters or digits and names must be unique.
`colour` and `colour2` (hex, e.g. `#2ad4ff`) tint the team's holographic
card; without them it uses the BRAWLISTAN emerald and magenta (ADR-117). A
team's logo is added to the website by the site owner (docs/DECISIONS.md
ADR-114: `scripts/team_logos.py`).

### /team clan <name> <clan_id> *(staff)*
Link a team to its in-game Brawlhalla clan (ADR-120). The bot checks the
clan exists and syncs the roster at once; from then on every snapshot tick
keeps it in step: clan members are on the team with their clan rank,
players who left the clan leave the team (only those the sync added), and
the clan's Leader becomes captain if the team has none. `clan_id:0` unlinks.

### /team sync <name> *(staff)*
Pull a linked team's roster from its clan now, and see what changed
(added, moved from another team, left, kept). Ratings follow on the next
snapshot.

### /team captain <name> [user] [brawlhalla_id] *(staff)*
Name a team's captain, who must already be on the roster; the previous
captain becomes a player. A captain can add and remove their own team's
players. This doesn't grant the Team Captain Discord role, which staff give
by hand.

## Automatic posts

Each can be switched off in the environment: `ANNOUNCE_SEASON_START`,
`ANNOUNCE_WEEKLY_DIGEST`, `ANNOUNCE_PAKISTAN_WEEKLY`, `ANNOUNCE_ACHIEVEMENTS`
(rank-ups and milestones in #achievements), `ANNOUNCE_FEATURED`, and
`ANNOUNCE_LEVEL_UPS`, which is **off by default** to keep the server quiet.

An unlocked achievement is posted as the BRAWLISTAN achievement card (the
achievement's badge, its name and the member's name) with a line that pings
the member: "🎉 Congratulations @member! You've unlocked **Champion**. Won a
clan tournament." There's no embed (ADR-124). Peak-rating, tier-change and
level-up posts are unchanged.

## Weekly digest (standing job, not a command)

`ClanCog`'s second scheduled loop (alongside the ranking-snapshot loop,
docs/DECISIONS.md ADR-028) checks daily and posts every Sunday to
`#announcements`: top 3 rating gains this week, top 3 chatters by weekly XP,
and matches played. It also picks an MVP of the Week — biggest rating gain,
falling back to the top chatter in a quiet ranked week — and awards them
the MVP achievement (docs/DECISIONS.md ADR-070; the MVP role retired with
ADR-109). The same loop posts the Pakistan weekly standings to #rankings.

## Account roles (standing job, not a command)

Every snapshot tick mirrors two roles from the database (ADR-109): **Player**
for every member with an active Brawlhalla link, **Verified** for every link
staff confirmed with `/verify`. Members who no longer qualify lose them.
`/link`, `/unlink` and `/verify` also update them immediately.

## Standing panels

Not slash commands — persistent, interactive messages `/setup run
mode:launch` posts once and that keep working across bot restarts
(docs/DECISIONS.md ADR-058). See docs/DISCORD_SPEC.md's "Standing panels"
section for which channel gets what.

- **Spar kiosk** (#looking-for-game) — 🥊 1v1 / 👥 2v2 buttons that run the
  exact same flow as `/scrim`, just without typing the command. (The opt-in
  role panel retired with ADR-109.)

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
