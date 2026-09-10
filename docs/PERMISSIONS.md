# Permission Model

## Role hierarchy

👑 SHAHEEN LEADER
🛡️ MODERATOR
🏆 ELITE SHAHEEN
🦅 SHAHEEN
🎯 TRIAL SHAHEEN
🤝 ALLY
👀 GUEST
🤖 SHAHEEN BOT

The bot's role must be high enough to manage the roles/channels it is expected
to manage.

A separate set of opt-in roles (pings/region/mode tags — see
`bot.constants.SELF_ASSIGN_ROLES`, docs/DECISIONS.md ADR-058) sits below
👀 GUEST and is not part of this hierarchy: no permissions, not staff-
assigned, members toggle them themselves via the panel `/setup run
mode:launch` posts to #roles.

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
