# Discord Server Specification

The BRAWLISTAN server (docs/DECISIONS.md ADR-109). `bot/constants.py` is the
single source of truth; this page is for reference. The SHAHEEN-era layout
(9 categories, 33 channels, gated access) is described in ADR-058 to ADR-097
and is retired.

## Categories and channels

Small on purpose: twelve text channels in four categories, and no voice
channels.

### START HERE
- **#welcome**: the welcome message, plus a card for each member who joins or
  leaves.
- **#rules**: server rules.
- **#announcements**: new seasons (the season card is posted once per
  season), the weekly digest and staff news.

### BRAWLISTAN
- **#rankings**: the Pakistan weekly standings and climbers. Reuses the
  SHAHEEN #leaderboard channel.
- **#tournaments**: tournament announcements and results.
- **#looking-for-game**: sparring and 2v2 partners, with the spar kiosk
  buttons. Reuses #ranked.

### COMMUNITY
- **#general**
- **#clips**
- **#achievements**: rank-ups, milestones and achievements, posted by the bot.
  Reuses #hall-of-fame.

### SUPPORT
- **#bot-commands**: run bot commands here. Reuses #commands.
- **#report**: player reports and the moderation log. The owner makes it
  staff-only. `REPORT_CHANNEL_ID` / `MOD_LOG_CHANNEL_ID` can point either
  stream elsewhere.

Where a SHAHEEN channel plays the same part, its setup key is reused, so
`/setup run` renames and moves the existing channel (history intact) instead
of creating a new one.

## Roles

Founder, Admin, Moderator, Team Captain, Contributor, Verified, Player. They
are created with no permissions. See docs/PERMISSIONS.md.

## Permissions

`/setup` never sets or changes permissions; the owner configures them by
hand. See docs/PERMISSIONS.md.

## Idempotency

Running setup again never duplicates a role, category or channel:
- **Recorded resources:** setup records the Discord ID of everything it
  creates or adopts (the `provisioned_resources` ledger).
- **Unrecorded resources:** setup adopts an existing one with the same name.
- **Drift:** it repairs only a resource's name, topic and parent category.

`/setup restructure` deletes the ledger-tracked SHAHEEN resources outside
this spec, after a confirm. Anything made by hand is never touched.

## Launch messages

`/setup run mode:launch` posts, once each, the welcome and rules embeds and
a short intro for every other channel (`bot/content/channel_intros.py`).
#looking-for-game also gets the persistent spar kiosk.
`tests/test_setup_launch_messages.py` checks that every text channel in the
spec has launch content.

## Welcome and leave cards

`bot/cogs/engagement.py` posts a branded card to #welcome on join and on
leave. The join caption points at #rules and `/link`. No role is assigned on
join; Player is granted when the member links a Brawlhalla account.
