# Permission Model

## Role hierarchy

Bilingual "English | Urdu" names, no emoji prefix — docs/DECISIONS.md
ADR-060/ADR-061 (`bot.constants.ROLES` is the single source of truth; this
list is for reference only and can drift, unlike the code):

Leader | سربراہ
Moderator | ناظم
Elite Shaheen | شاہینِ خاص
Shaheen | شاہین
Trial Shaheen | آزمائشی شاہین
Ally | اتحادی
Guest | مہمان
SHAHEEN BOT (Discord's own managed integration role — ADR-018)

The bot's role must be high enough to manage the roles/channels it is expected
to manage.

A separate set of opt-in roles (pings/region/mode tags — see
`bot.constants.SELF_ASSIGN_ROLES`, docs/DECISIONS.md ADR-058) sits below
Guest and is not part of this hierarchy: no permissions, not staff-
assigned, members toggle them themselves via the panel `/setup run
mode:launch` posts to #roles.

🌟 MVP of the Week (`bot.constants.ROLE_MVP`) is also outside this
hierarchy — purely cosmetic, no permissions, held by at most one member at
a time, and rotated automatically by `ClanCog`'s weekly digest job rather
than self-assigned or staff-assigned (docs/DECISIONS.md ADR-070).

## Per-channel send permissions

Beyond the category-level visibility overwrites (restricted categories
hidden from everyone but staff), individual channels can restrict who can
*send* while staying visible to everyone — `ChannelSpec.staff_only_send`
(`bot/constants.py`), applied idempotently by `/setup run` the same way
everything else here is (docs/DECISIONS.md ADR-060). Currently only
`#announcements`: everyone can read it, only Leader/Moderator can post.

## The entrance: Guest sees exactly one channel

`🦅 START HERE` (`category:start_here`) is the only ungated category in the
server (docs/DECISIONS.md ADR-091) — it holds nothing but `#apply`. A
brand-new Guest sees that one channel and nothing else until a moderator
approves their application or runs `/verify`. Before ADR-091, SHAHEEN HQ
(`#welcome`/`#rules`/`#roles`/`#clan-info`/`#announcements`) was public
too; it's now gated like everything else, on the owner's explicit call to
shrink the pre-approval surface to a single channel.

## Manual verification gate

`CategorySpec.gated` (`bot/constants.py`, docs/DECISIONS.md ADR-069) — the
same shape as `restricted`, inverted: hidden from `@everyone` **and** Guest
(the role auto-assigned on join, ADR-065), visible to every other rank role
(`VERIFIED_ROLES` = everything except Guest). Currently SHAHEEN HQ, THE
NEST, BRAWLHALLA, VOICE, and HALL OF RECORDS.

### Two distinct promotion paths, not one (ADR-092)

`/verify <member>` (`bot/cogs/moderation.py`) and an approved `/apply`
application (docs/DECISIONS.md ADR-089) used to land in the same place —
Guest → Ally — making the application form's screening pointless. They now
diverge:

- **`/verify`** grants general **community access**: Guest → Ally via
  `bot/membership.py`'s `grant_member_access`. No form, staff-run, for
  someone who wants to be part of the server without trying out for the
  roster. Idempotent: a no-op on a member who already holds any rank role
  above Guest (`is_already_verified`).
- **An approved `/apply`** grants **clan roster membership**: Guest and/or
  Ally → Trial Shaheen directly via `grant_clan_membership`, skipping Ally
  entirely — the applicant already went through the application's real
  screening (Brawlhalla ID, rank, "why Shaheen"). Gated by
  `is_already_a_clan_member` (true only for `FULL_MEMBER_ROLES`, Trial
  Shaheen and up), not `is_already_verified` — an Ally let in via `/verify`
  can still apply for the roster, since Ally isn't clan membership.

Both paths still only ever add roles a member doesn't already hold, and
both raise `ShaheenError` rather than silently no-op if the target role
(Ally or Trial Shaheen) hasn't been provisioned by `/setup run` yet.

### Approval grants full read+write; only broadcast channels are read-only

An approved Ally gets **full** read+write in every gated category from the
moment they're verified — no separate read-only limbo state
(docs/DECISIONS.md ADR-091, superseding ADR-090's Ally-read-only design).
The one exception is `CategorySpec.readonly` (only meaningful combined with
`gated=True`): every `VERIFIED_ROLE`, staff included, gets
`send_messages=False` / `speak=False` there — for bot-broadcast channels
where a human typing was never the point. Currently `🏆 HALL OF RECORDS`
(`#leaderboard`, `#hall-of-fame`), split out of SHAHEEN ARENA (which stays
`restricted`, staff-only, for `#scrims`/`#tournaments`).

`/link` still requires already holding Ally before it promotes to Trial
Shaheen (`LinkCog._maybe_promote`) — that part of ADR-090 stands. Before
ADR-090, `/link` promoted straight from **Guest**, which let anyone skip
`/apply` entirely by linking their account first.

MODERATION and DEVELOPMENT are unaffected — both stay `restricted`.

`/setup run` now always reconciles every channel/category's overwrites —
including clearing them back to "none" — instead of only touching the ones
with a special (`restricted`/`gated`/`staff_only_send`) spec. A manually
added overwrite anywhere the bot manages gets corrected back on the next
`/setup run`, matching ADR-060's original idempotent-repair promise.

Every channel also carries its own explicit copy of its parent category's
`restricted`/`gated` overwrite (docs/DECISIONS.md ADR-072) — the same thing
Discord's own client does when you create a channel inside a category
("Permissions Synced") — rather than being left with zero overwrites of its
own and relying on Discord's category→channel cascade to apply the
category's restriction. This is what actually locks a brand-new channel
down from the moment it's created.

## General principles

- Use least privilege.
- @everyone should not have administrative permissions.
- Development channels are staff-only.
- Bot administration commands require an explicit admin/leader check.
- Competitive/member commands should be usable by ordinary members where
  appropriate.
- Never rely solely on channel names for authorization.

## Development

DEVELOPMENT category:
- Leader: full access
- Moderator: access where required
- regular members: no access

## Setup

/setup and setup verification:
- Shaheen Leader
- server administrators

Do not grant Administrator permission to the bot merely because it simplifies
implementation. Request only required permissions.

## Moderation

MODERATION category (`#mod-log`): restricted the same way as DEVELOPMENT —
hidden from everyone but `ROLES_WITH_STAFF_ACCESS` (docs/DECISIONS.md
ADR-065).

`/warn`, `/warnings`, `/clearwarnings`, `/kick`, `/ban`, `/unban`,
`/timeout`, `/untimeout`, `/purge`, `/lock`, `/unlock`, `/slowmode`,
`/nickname`, `/verify` (`bot/cogs/moderation.py`), `/emoji sync`
(`bot/cogs/emoji.py`, docs/DECISIONS.md ADR-090), and `/spotlight`
(`bot/cogs/clan.py`, docs/DECISIONS.md ADR-070) all require
`require_staff_authorized()` — the same check `/setup` uses: a server
administrator, or a member holding Leader or Moderator. This gates who can
*invoke* the command; it does not grant the bot itself any Discord
permission it doesn't already have — `/kick`/`/ban`/`/timeout` still fail
with a clear error if the bot's own role lacks the matching native
permission.

`/level` and `/chatboard` (`bot/cogs/engagement.py`) have no permission
check — same "any member" posture as `/profile`.
