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

## Manual verification gate

`CategorySpec.gated` (`bot/constants.py`, docs/DECISIONS.md ADR-069) — the
same shape as `restricted`, inverted: hidden from `@everyone` **and** Guest
(the role auto-assigned on join, ADR-065), visible to every other rank role
(`VERIFIED_ROLES` = everything except Guest). Currently THE NEST, BRAWLHALLA,
and VOICE. SHAHEEN HQ (`#welcome`/`#rules`/`#roles`/`#clan-info`/
`#announcements`) is deliberately **not** gated — a brand-new Guest needs
somewhere to read the rules before they can be verified.

A staff member runs `/verify <member>` (`bot/cogs/moderation.py`) to promote
a Guest to Ally, which is what actually grants access to the gated
categories — mirrors the existing Guest→Trial Shaheen promotion `/link`
already does (`LinkCog._maybe_promote`), just staff-triggered instead of
Brawlhalla-link-triggered. Idempotent: running it on an already-ranked
member is a no-op, not an error.

`/setup run` now always reconciles every channel/category's overwrites —
including clearing them back to "none" — instead of only touching the ones
with a special (`restricted`/`gated`/`staff_only_send`) spec. A manually
added overwrite anywhere the bot manages gets corrected back on the next
`/setup run`, matching ADR-060's original idempotent-repair promise.

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

`/warn`, `/warnings`, `/clearwarnings`, `/kick`, `/ban`, `/timeout`,
`/purge`, `/verify` (`bot/cogs/moderation.py`), and `/spotlight`
(`bot/cogs/clan.py`, docs/DECISIONS.md ADR-070) all require
`require_staff_authorized()` — the same check `/setup` uses: a server
administrator, or a member holding Leader or Moderator. This gates who can
*invoke* the command; it does not grant the bot itself any Discord
permission it doesn't already have — `/kick`/`/ban`/`/timeout` still fail
with a clear error if the bot's own role lacks the matching native
permission.

`/level` and `/chatboard` (`bot/cogs/engagement.py`) have no permission
check — same "any member" posture as `/profile`.
