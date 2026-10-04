# SHAHEEN → BRAWLISTAN migration map

BRAWLISTAN, *Pakistan's Brawlhalla Network*, grows out of the SHAHEEN clan
platform (docs/DECISIONS.md ADR-103). This is a migration, not a rewrite:
- the Python stack stays (discord.py bot on Fly.io, FastAPI + Postgres on Render, static site on GitHub
  Pages);
- SHAHEEN becomes the **Founding Team**;
- nothing useful is deleted.

This file is the checklist the stages work through. Each stage ships on its own (tested, merged,
deployable) and updates the status column here.

## Owner decisions

| Question | Decision |
|---|---|
| Bot / backend stack | Keep Python (discord.py, FastAPI, Postgres). No Node rewrite. |
| Bot hosting | Stays on Fly.io: Render's free tier sleeps and would drop the Discord gateway connection (ADR-053). The API stays on Render. |
| Public data | The existing `web/data/*.json` snapshots, written by `.github/workflows/snapshot.yml` from the API. Postgres stays the source of truth. |
| Discord server | Full restructure to the brief's 7 roles and 12 channels. No rank roles. The bot never sets channel permissions. Old bot-created roles and channels are deleted behind a confirm step. |
| Season order | Unchanged: Season 1 Zarb-e-Shaheen (Brawlhalla S42), Season 2 Sarfaroshi, … (ADR-102). |
| Visual reference | The owner's DesignLab screenshots (sidebar app window over a landscape, glass panels, list/grid toggle, member cards, event timeline, mobile icon rail) and the BRAWLISTAN graffiti-falcon logo. |
| `npm test / lint / build` | `pytest` / `ruff check` + `mypy` / the Pages deploy. There's no Node toolchain. |

## Old → new

| SHAHEEN | BRAWLISTAN | Stage |
|---|---|---|
| Homepage (`index.html`, `landing.html`) | Brawlistan home: hero, Pakistan Top 10, Rising, Current Season, Featured Player, Legend Meta, Latest Tournament, Community, Founding story | 1 |
| Clan roster / clan board (`/link`) | Players directory; the clan board becomes the SHAHEEN team page | 3, 7 |
| Pakistan board (`/pakistan …`, ADR-099/100) | **Pakistan Rankings**, the primary page | 2 |
| Clan tournaments (`tournaments.html`, `/tournament`) | Tournaments timeline (Upcoming / Live / Completed); brackets stay but aren't extended | 8 |
| Clan achievements | Player and season achievements | 9 |
| Legend meta / mastery | Legend statistics page | 9 |
| Shaheen / Pakistan Seasons (ADR-102) | Brawlistan Seasons page; same 13 badges and order | 6 |
| `/link` (direct) | `/link` code + website claim; staff `/verify` | 4 |
| Discord server (21 roles, 33 channels, permission overwrites) | 7 roles, 12 channels, no overwrites | 5 |
| SHAHEEN brand | Founding Team; BRAWLISTAN is the site brand | 1, 7 |

## Discord restructure (stage 5)

**Roles kept or created:** Founder, Admin, Moderator, Team Captain, Contributor, Verified, Player.
- All are created with no permissions; the owner grants them by hand.
- Same-named existing roles are reused, never duplicated.

**Channels** (no permission overwrites):

| Category | Channels |
|---|---|
| START HERE | #welcome, #rules, #announcements |
| BRAWLISTAN | #rankings, #tournaments, #looking-for-game |
| COMMUNITY | #general, #clips, #achievements |
| SUPPORT | #bot-commands, #report |

Where an old channel plays the same part, its logical key is reused so the channel and its history
survive: welcome, rules, announcements, tournaments, general, clips. hall_of_fame becomes #achievements;
commands becomes #bot-commands.

**Removed by `/setup restructure`.** It touches only resources in the `ProvisionedResource` ledger, after
a confirm.

- **Roles:**
  - Leader, Elite Shaheen, Shaheen, Trial Shaheen, Ally, Guest;
  - MVP of the Week, Core Member, Pakistan Top 10;
  - the rank roles: Rising Shaheen, Gold, Platinum, Diamond, Valhallan;
  - Tournament Alerts, Scrim Alerts, Pakistan, International, 1v1 Player, 2v2 Player.
  - Moderator is kept: same name.
- **Categories:** SHAHEEN HQ, THE NEST, BRAWLHALLA, SHAHEEN ARENA, HALL OF RECORDS, VOICE, MODERATION,
  DEVELOPMENT, and every channel inside them not listed above.

**Code that depended on removed roles or channels** (each retired or remapped in stage 5):

| Code | Depends on | Outcome |
|---|---|---|
| `bot/checks/permissions.py` | Leader, Moderator | Remapped to Founder / Admin / Moderator; Discord-permission fallback kept |
| `bot/membership.py`, `cogs/link.py`, `content/embeds.py`, `content/profile_embeds.py` | Trial, Ally, Guest, Shaheen, Elite | Clan membership states retired; linking grants **Player** |
| `cogs/application.py` (`/apply`, #apply, #applications) | Trial/Shaheen roles, apply channels | Retired (clan recruitment) |
| `services/rank_roles.py`, `cogs/clan.py` `_sync_rank_roles` | rank roles | Retired; the brief rules out rank roles |
| `cogs/clan.py` `_sync_pakistan_top_role`, `pakistan_board_service.top_role_earners` | Pakistan Top 10 | Role sync retired; the board, claims and weekly post stay |
| `cogs/clan.py` MVP rotation | MVP of the Week | Retired; the weekly digest stays |
| `cogs/engagement.py` | Core Member, Guest | Core Member grant retired; chat XP stays |
| `bot/views/roles.py` self-assign view, #roles | alert/region/mode roles | Retired |
| `services/setup_service.py` | Guest (everyone overwrites) | Overwrites removed entirely |
| Posts to #hall-of-fame, #pakistan-chat, #mod-log, #leaderboard | old channels | #achievements, #rankings, `MOD_LOG_CHANNEL_ID` / #report |

Data in Postgres (players, links, snapshots, achievements, matches, tournaments, Pakistan board) is
untouched by the restructure.

## Status

| Stage | Scope | Status |
|---|---|---|
| 0 | This map, ADR-103 | done |
| 1 | Brand, design system, app shell, home | done (ADR-104) |
| 2 | Rankings | done (ADR-105) |
| 3 | Players + profiles | done (ADR-106) |
| 4 | Linking + verification | done (ADR-107) |
| 5 | Discord restructure + bot commands | |
| 6 | Seasons page | |
| 7 | Teams | |
| 8 | Tournaments | |
| 9 | Legends + statistics | |
| 10 | Reporting, PWA, SEO, README | |
