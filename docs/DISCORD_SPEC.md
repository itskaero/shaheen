# Discord Server Specification

## Naming philosophy

English channel names are preferred for discoverability.
Urdu is used as a subtitle/description and in branding.

Every text channel also carries a bilingual "English | Urdu" **topic**
(`ChannelSpec.topic`, `bot/constants.py`; applied/repaired idempotently by
`/setup run` — docs/DECISIONS.md ADR-061), shown under the channel name in
Discord's UI. Channel *names* stay English-only/emoji-kebab-case — Discord's
stricter name-normalization rules made topics the safe place for Urdu, not
the name itself (ADR-061). Voice channels have no topic field and are
skipped.

## Categories and channels

### 🏯 SHAHEEN HQ
Urdu: شاہین مرکز

- 📢 announcements
- 👋 welcome
- 📜 rules
- 🎭 roles
- 🦅 clan-info

### 🪹 THE NEST
Urdu: آشیانہ

- 💬 general
- 🇵🇰 pakistan-chat
- 😂 memes
- 🎬 clips

### ⚔️ BRAWLHALLA
Urdu: میدانِ براولہلا

- 🎮 brawlhalla
- 🧠 tips-guides
- 🐺 legend-talk
- ⚔️ 1v1
- 👥 2v2
- 🏆 ranked

### 🏟️ SHAHEEN ARENA
Urdu: میدانِ شاہین

Initially hidden/disabled from public users until there is a need.

- ⚔️ scrims
- 🏆 tournaments
- 📊 leaderboard
- 🥇 hall-of-fame

### 🎙️ VOICE
Urdu: آواز

- 🔊 The Nest
- 🎮 Gaming
- ⚔️ Ranked
- 💤 AFK

### 🛠️ DEVELOPMENT

Admin-only initially.

- 🤖 bot-testing
- 🌐 website-testing
- 🧪 commands
- 🐛 bug-reports
- 📝 development-log

## Initial launch behavior

The server may remain private during development. The setup system must support
development mode and later launch mode without destroying existing data.

## Idempotency

Running setup repeatedly must not create duplicate roles/channels/categories.
The bot should identify previously-created resources, verify them, and repair
configuration when safe.

Use stored Discord IDs where possible rather than relying only on names.

## Standing panels (launch mode)

`/setup run mode:launch` posts persistent, interactive panels alongside the
welcome/rules messages (docs/DECISIONS.md ADR-058) — idempotently, like
everything else here:

- **🎭 roles** — the rank-ladder embed (staff-assigned), plus an "🎯 Opt-in
  Roles" panel with toggle buttons for opt-in pings/tags (🔔 Tournament
  Alerts, 📣 Scrim Alerts, 🇵🇰 Pakistan / 🌍 International, 🥊 1v1 Player /
  👥 2v2 Player — see `bot.constants.SELF_ASSIGN_ROLES`). These are not clan
  rank — no permissions, not staff-assigned.
- **🏆 ranked** — a standing "🥊 Looking to Spar?" panel; its buttons run the
  same flow as `/scrim`.

Every other text channel also gets a short static intro embed on launch
(docs/DECISIONS.md ADR-059 — `bot/content/channel_intros.py`; 20 channels,
one builder each, wired into `bot/cogs/setup.py`'s `_launch_messages()`):
📢 announcements, 🦅 clan-info, 💬 general, 🇵🇰 pakistan-chat, 😂 memes,
🎬 clips, 🎮 brawlhalla, 🧠 tips-guides, 🐺 legend-talk, ⚔️ 1v1, 👥 2v2,
⚔️ scrims, 🏆 tournaments, 📊 leaderboard, 🥇 hall-of-fame, 🤖 bot-testing,
🌐 website-testing, 🧪 commands, 🐛 bug-reports, 📝 development-log — i.e.
every text channel `bot.constants.CATEGORIES` defines gets *something*;
only the 4 voice channels get nothing (no text to post). A regression test
(`tests/test_setup_launch_messages.py`) checks this stays true if a new
channel is ever added.
