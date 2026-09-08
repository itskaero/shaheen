# Discord Server Specification

## Naming philosophy

English channel names are preferred for discoverability.
Urdu is used as a subtitle/description and in branding.

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
