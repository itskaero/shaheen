# Permission Model

BRAWLISTAN's permission model (docs/DECISIONS.md ADR-109). The SHAHEEN-era
model of gated categories, rank roles and an Ally/Trial verification ladder
is described in ADR-060 to ADR-097 and is retired.

## Who sets permissions

**The owner does, by hand.** `/setup` never changes a permission:
- roles are created with **no permissions**;
- categories and channels are created with **no permission overwrites**, so a
  channel inherits its category's settings;
- an existing role's permissions, colour and display flags are never
  "repaired"; `/setup` only renames it;
- an existing channel's overwrites are never edited.

Configure each category in Discord's Server Settings once (for example, make
SUPPORT → #report staff-only and START HERE → #announcements read-only), and
re-running `/setup` won't undo it.

## Roles

`bot.constants.ROLES` is the single source of truth; this list is for
reference.

| Role | Meaning | Assigned by |
|---|---|---|
| Founder | Project owner and leadership | Owner, by hand (the old SHAHEEN Leader role, renamed) |
| Admin | Leadership | Owner, by hand |
| Moderator | Moderation staff | Owner, by hand |
| Team Captain | Captains a team | Owner/staff, by hand |
| Contributor | Helps build BRAWLISTAN | Owner/staff, by hand |
| Verified | Staff confirmed they own their linked Brawlhalla account | The bot (`/verify`) |
| Player | Has a linked Brawlhalla account | The bot (`/link` or a website claim) |

There are no rank-specific roles. The bot keeps Player and Verified in step
with the database on every snapshot tick, adding and removing them; every
other role is manual.

Two roles are yours to create and pick, not part of `/setup`:
- **The join/approved roles** (`/access roles`, ADR-123), for example Guest.
  The bot gives them on join and catches up anyone it missed (ADR-126).
- **The Coach role** (`/coach setup`, ADR-126). You give it by hand; the bot
  only reads who holds it to build the coach directory.

## Command authorization

Checks live in `bot/checks/permissions.py` and are by role name plus a
permanent fallback, because the roles don't exist until `/setup` creates
them.

- **`/setup` (run, roles, status, verify, restructure, reset):** guild owner,
  `BOT_OWNER_ID`, the native Administrator permission, or Founder/Admin.
  `/access roles|approval|status|sync`, `/coach setup` and `/sync` use the same check.
- **Staff commands** (`/warn`, `/warnings`, `/clearwarnings`, `/kick`, `/ban`,
  `/unban`, `/timeout`, `/untimeout`, `/purge`, `/lock`, `/unlock`,
  `/slowmode`, `/nickname`, `/verify`, `/spotlight`, `/emoji *`,
  `/pakistan add|remove`, `/approval`, tournament management): the same fallback, or
  Founder/Admin/Moderator.
- **Team rosters** (`/team add`, `/team remove`): staff, or the captain of
  that team (the member whose linked Brawlhalla account is the team's
  captain, ADR-114). `/team create` and `/team captain` are staff only.
- **Coaching** (`/coach requests`, `/coach profile`): members holding the
  Coach role set with `/coach setup` (ADR-126). A request's Accept/Decline
  buttons answer only for the coach asked, or staff.
- **Everything else** (`/link`, `/profile`, `/level`, `/help`, `/team info`,
  `/team leave`, `/coach list`, `/coach request` and so on): any member.

The checks decide who can *invoke* a command; they never grant the bot a
Discord permission it lacks. `/kick` still fails with a clear error if the
bot's role lacks Kick Members.

## The bot's own permissions

Never Administrator. Invite the bot with only:

| Permission | Used by |
|---|---|
| Manage Roles | `/setup` (create/rename roles), Player/Verified sync, join role and `/approval` (ADR-123) |
| Manage Channels | `/setup` (create/rename/move channels), `/lock`, `/slowmode`, `/setup restructure` |
| View Channels, Send Messages, Embed Links, Attach Files, Read Message History | Posts, cards, launch messages |
| Add Reactions | Reaction-based flows |
| Manage Messages | `/purge` |
| Moderate Members | `/timeout`, `/untimeout` |
| Kick Members, Ban Members | `/kick`, `/ban`, `/unban` |
| Manage Nicknames | `/nickname` |
| Manage Expressions | `/emoji` |

The bot's role must sit above Player and Verified in the role list so it can
assign them; `/setup` places the roles it manages just below the bot's own
role.

## General principles

- Least privilege, for members and for the bot.
- `@everyone` never gets administrative permissions.
- Never rely on channel names for authorization.
