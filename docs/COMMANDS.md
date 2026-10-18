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

Either way, linking puts you on the Pakistan rankings (ADR-125), unless you
left them earlier with `/pakistan leave`; `/pakistan join` turns them back on.

An account already linked to (or claimed on the Pakistan board by)
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

**Who's on the board (ADR-125):** members who linked (`/link`) or joined
(`/pakistan join`), players staff added, and everyone on a Pakistani team's
roster (teams with country PK; the snapshot tick syncs it). Brawlhalla
reports a server region, never a country, so these are the only signals.

### /pakistan join [identifier]
Your toggle, on. With no identifier it uses your linked account, with no
confirm step. With a Brawlhalla or Steam64 ID it puts that account on, after
a confirm. One entry per member: joining with a different account replaces
the old one. A spot staff or a team roster made for you becomes yours.

### /pakistan leave
Your toggle, off: takes off your entry, or your linked account's entry if a
team roster put it there. It's remembered, so neither `/link` nor the team
sync adds you back; `/pakistan join` does.

### /pakistan add <identifier> *(staff)*
Add any Pakistani player — no Discord membership needed. If they join the
server later, `/pakistan join` with the same ID makes the entry theirs.
Staff-added and self-joined entries are capped at 150 (API quota); team-roster
entries don't count, since their players are snapshotted as roster players anyway.

### /pakistan remove <brawlhalla_id> *(staff)*
Remove a player from the Pakistan leaderboard. Like `/pakistan leave`, it
sticks: the team sync won't add them back.

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
biggest rating gains), or `city` (City Wars, ADR-128: each city's average of
its best 5 placed 1v1 ratings this season). Placed players only; an empty
board says "Data unavailable".

### /city set <city> · /city clear
Represent a Pakistani city on City Wars (ADR-128), picked from a fixed list
(the twin cities share "Islamabad / Rawalpindi"). Needs a linked account;
counts once you're placed this season. Shown on your website profile, the
Rankings page's **Cities** tab and the City Wars page. Audit-logged.

### /clanwars
This week's Clan Wars standings (ADR-131): every team's points, with its top
scorers, then the season table (weeks won) and last week's winner, with a link
to `clanwars.html`.
- **Points:** each team member scores 10 per ranked 1v1 win plus every rating
  point gained this week (a loss costs nothing). From ranked snapshots, never
  self-reported.
- **Team score:** its best five members, so a big roster can't win on numbers
  alone.
- **The week** runs Monday 00:00 to Monday 00:00 PKT, like the quests. A
  finished week is recorded once; the winner posts in #announcements only
  with `ANNOUNCE_CLAN_WARS=true`.
- **Fair play (ADR-136):** rosters lock at the start of the week (a mid-week
  transfer scores for its old team until Monday), and an account needs
  `CLAN_WARS_MIN_GAMES` (10) ranked games from before the week to count;
  newer accounts show struck through, uncounted.
- **Duels:** every week each team also gets one rival (round robin; a bye
  when the team count is odd). The season table shows duel W-D-L.
- **MVP:** the week's top counted scorer, on the verdict and the website.

### /warroom setup <channel> · /warroom off *(Founder/Admin)*
Run a live Clan Wars channel (ADR-136): a pinned scoreboard edited every 15
minutes (standings, this week's duels, City Wars top 3), a post when the lead
changes, a countdown in the final 6 hours on Sunday, and Monday's verdict with
the result card and the MVP (who gets the MVP of the Week achievement, and a
mention only if they're linked). Needs View, Send, Embed Links and Attach
Files in the channel; Manage Messages to pin. `/warroom off` stops it.

### /quests [user]
This week's three quests, with progress bars, and the season level (ADR-128):
play 15 ranked games, win 8, gain 50 rating. Progress comes from your ranked
snapshots (every 6 hours), never self-reported. Each quest is 100 season XP;
level = 1 + XP/100, up to 30, starting again each Brawlhalla season. Weeks
reset Monday 00:00 PKT. Completions post in #achievements only with
`ANNOUNCE_QUESTS=true`.

### /season
The current Pakistan season: number, name (English and Urdu), Brawlhalla
season, dates and days left, with its card and a **Season page** button to
`seasons.html` (ADR-113).

### /legend <name>
How a Legend is played across every tracked Pakistani player: players,
lifetime games, win rate and popularity rank. Autocompletes names.

### /tournaments
The ten most recent tournaments and their status.

### /looking <mode> [note]
Post a spar call in #looking-for-game (ADR-136): a card with your linked
name, clan tag, 1v1/2v2 rating and tier, region, city and your main Legend's
portrait, an optional note (80 characters; mentions and links are stripped),
and open slots. You're already on Side A; others tap **Join**. When it
fills, a thread opens for the players to share a room. You can **Cancel**
it, and it closes itself after 30 minutes. Every call tags the **Spar
Ping** role, at most once every 10 minutes server-wide. One call every 2
minutes per member.

### /sparping
Turn spar pings on or off: gives or takes the opt-in **Spar Ping** role
(no permissions; created the first time anyone turns it on). Same as the 🔔
button on the spar panel.

### /sparpanel · /linkpanel *(Founder/Admin)*
Post a standing panel in the current channel: the looking-for-game panel
(1v1, 2v2, 🔔 Spar pings), or the one-tap link panel for #welcome (link
button → ID → check the player → pick a city → done; 5 lookups per member
per 10 minutes).

### /reactionrole post · add · remove · list *(Founder/Admin)*
Roles members pick by reacting (ADR-137): react to get the role, remove the
reaction to lose it.
- **`post <channel> <title> [description]`** posts a branded panel and replies
  with its link. Panels list their emoji and roles and update themselves.
- **`add <message link> <emoji> <role>`** makes that emoji on any message (a
  panel or not) give the role, and adds the bot's reaction so members only
  tap it. Standard emoji or this server's own; 20 per message; one emoji and
  one role each per message.
- **`remove <message link> <emoji>`** stops it; members keep roles they have.
- **`list`** shows every binding with a link to its message.
- **Safe roles only:** not @everyone, not managed by an integration, below the
  bot's and your own top role, and with no moderation or admin permissions.
  Checked again on every reaction. Changes are audit-logged; deleting the
  message removes its bindings.
- **The bot needs** Manage Roles (its role above the ones it hands out), and
  Add Reactions, Read Message History and View Channel where the message is.

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

Every 10 minutes the bot also catches up members the join handler missed
(it was restarting, or Discord refused the edit), ADR-126. It only gives
the join-time role to members with **no other roles** (Player/Verified
don't count), so staff and hand-picked roles are never touched.

### /access status *(Founder/Admin)*
Both roles, the switch, how many members are waiting, how many hold
neither role, and anything missing: an unset or deleted role, a role at or
above the bot's own (the usual reason members get nothing), or the bot
lacking Manage Roles.

### /access sync *(Founder/Admin)*
Give the join-time role (approved role while approval is off, join role
while it's on) to **every** member who holds neither role, including members
with other roles. Shows the count and asks to confirm. Audit-logged.

### /approval <member> *(staff)*
Give a member the approved role and take away the join role. Says so if
they're already approved. Audit-logged.

### /coach list
The coaches (members holding the Coach role, ADR-126), who's taking
students, their specialty, legends and availability, with a **Coaches page**
button.

### /coach request <coach> <message>
Ask a coach for a session (10–280 characters on what you want help with).
Posts a card in the coaching channel that pings the coach, with
**Accept**/**Decline** buttons only that coach (or staff) can press. One
open request per coach, three open at most; unanswered requests lapse after
7 days. Accepting pings you in the channel; a decline is sent by DM.

### /coach requests *(coaches)*
Your open requests.

### /coach profile [specialty] [legends] [availability] [bio] [accepting] *(coaches)*
Edit your coach card. `legends` takes up to three names, comma-separated;
empty text clears a field; `accepting:False` pauses new requests. You're
listed on the website once your Brawlhalla account is linked.

### /coach setup <role> <channel> *(Founder/Admin)*
The role your coaches hold (given by hand; the bot only reads it) and the
channel requests are posted in. The bot needs Send Messages and Embed Links
there. Audit-logged.

### /sync *(Founder/Admin)*
Re-sync the bot's slash commands to the server, for example after a deploy
added commands.

### /admin status *(Founder/Admin)*
A private health check (ADR-129):
- **Bot:** Discord latency and uptime.
- **Database:** reachable or not, query time, and the schema revision.
- **Rankings:** when the last ranking snapshot was taken, the snapshot
  interval, and how many players are tracked.
- **Background loops:** ranking snapshot, weekly digest, access catch-up and
  coaching sync, each running or stopped.
- **Needs attention:** anything wrong, most serious first. A snapshot older
  than two intervals usually means a bad Brawlhalla API key.

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
  exact same flow as `/looking`, just without typing the command, and a 🔔
  toggle for the Spar Ping role (ADR-136). Repost it with `/sparpanel` to
  get the 🔔 button on an older panel. (The opt-in role panel retired with
  ADR-109.)
- **Link panel** (`/linkpanel`, ADR-136) — one button that links an account
  in a modal, with a city pick.

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
