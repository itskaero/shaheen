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
