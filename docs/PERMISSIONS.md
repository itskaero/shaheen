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

## Per-channel send permissions

Beyond the category-level visibility overwrites (restricted categories
hidden from everyone but staff), individual channels can restrict who can
*send* while staying visible to everyone — `ChannelSpec.staff_only_send`
(`bot/constants.py`), applied idempotently by `/setup run` the same way
everything else here is (docs/DECISIONS.md ADR-060). Currently only
`#announcements`: everyone can read it, only Leader/Moderator can post.

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
