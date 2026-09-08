# Architecture Decisions

## ADR-001 — Python
Decision: Python 3.12+.

Reason: The project owner already knows Python and Discord bot development.

## ADR-002 — discord.py
Decision: discord.py 2.x.

Reason: Mature Discord Python ecosystem and owner familiarity.

## ADR-003 — PostgreSQL
Decision: PostgreSQL.

Reason: Persistent relational clan/player/history data and future website use.

## ADR-004 — SQLAlchemy + Alembic
Decision: SQLAlchemy 2.x with Alembic migrations.

Reason: Explicit database layer and controlled schema evolution.

## ADR-005 — Brawlhalla integration boundary
Decision: All external Brawlhalla API access is isolated behind an integration
client/service.

Reason: Prevent Discord code from becoming coupled to external API details.

## ADR-006 — Server setup is idempotent
Decision: /setup must be safe to run repeatedly.

Reason: Rapid provisioning and repair are core requirements.

## ADR-007 — One Shaheen bot
Decision: Build Shaheen-specific functionality into one custom bot instead of
depending on multiple generic bots for core functionality.

Reason: Consistent UX and a clean path to Brawlhalla/database/website integration.

## ADR-008 — English-first Discord naming
Decision: Channel names remain primarily English, with Urdu in descriptions,
branding and selected messages.

Reason: Discoverability for Pakistani and international Brawlhalla players.

## ADR-009 — Private development
Decision: The server remains private until the bot and initial web presence are
ready for launch.

Reason: Avoid exposing an unfinished public experience.

## ADR-010 — /setup permission bootstrap
Decision: `/setup` and setup verification are authorized for the Discord guild
owner or any member with the native `Administrator` permission, in addition to
holders of the 👑 SHAHEEN LEADER role once it exists. This is not a temporary
bootstrap-only rule; it stays in effect permanently, because on a brand-new
server the Shaheen Leader role does not exist until `/setup` creates it.

Reason: Without this fallback, `/setup` could never be run for the first time.

## ADR-011 — guild_id stored on persisted state, and a resource-tracking table
Decision: Tables that represent per-guild state store an explicit `guild_id`
column rather than assuming a single implicit guild, so the schema is
multi-guild-ready even though only one guild is operated today. A new entity,
`ProvisionedResource` (guild_id, resource_type, logical_key, discord_id,
last_verified_at, timestamps, unique on guild_id+resource_type+logical_key),
is added to track the Discord IDs of roles/categories/channels created by
`/setup`, and a `GuildSettings` entity (guild_id primary key, setup_mode,
last_setup_at) stores the active development/launch mode per guild. Neither
table was listed in `docs/DATABASE.md`'s conceptual entity list, which focuses
on Phase 2+ member/player data — these two exist specifically to satisfy the
Phase 1 idempotency requirement in `docs/SETUP_FLOW.md`.

Reason: `/setup`'s idempotency contract requires looking resources up by
stored ID before falling back to name matching; nothing in the original
schema could hold those IDs.

## ADR-012 — All Discord intents enabled
Decision: The bot requests all Discord gateway intents, including the
privileged `members`, `presences`, and `message_content` intents. These must
also be enabled for the application in the Discord Developer Portal.

Reason: Owner decision, made to avoid revisiting intent configuration as
member-join welcome flows, role assignment, and later phases need them.

## ADR-013 — Guild-scoped slash command sync
Decision: Application commands are synced to the configured `GUILD_ID` only,
not globally.

Reason: Instant propagation during development; Shaheen operates a single
guild, so global sync's only benefit (multi-server propagation) does not
apply.

## ADR-014 — Phase 1 database scope is setup-only
Decision: Phase 1 migrations create only `provisioned_resources` and
`guild_settings`. `DiscordUser`, `ShaheenMember`, `BrawlhallaPlayer`, and the
other entities in `docs/DATABASE.md` are deferred to the Phase 2 migration
that introduces `/link`, since no Phase 1 command reads or writes them.

Reason: `docs/ROADMAP.md`'s own rule — do not implement a later phase's data
merely because it is documented — applied to the database layer.

## ADR-015 — Setup mode is a command option, persisted per guild
Decision: `/setup run` takes a `mode` option (`development` default |
`launch`). The chosen mode is persisted in `GuildSettings` so `/setup status`
and `/setup verify` can report against the last-applied mode without it being
re-specified.

Reason: `docs/COMMANDS.md` and `docs/SETUP_FLOW.md` require `/setup` to know
its mode but never say where that value comes from.

## ADR-016 — /setup exposed as a command group
Decision: `/setup`, `/setup status`, and `/setup verify` from
`docs/COMMANDS.md` are implemented as the subcommands `/setup run`,
`/setup status`, and `/setup verify` of one `setup` application command
group.

Reason: Discord's slash command schema does not allow a top-level command to
be both directly invocable and a parent of subcommands, so a literal bare
`/setup` cannot coexist with `/setup status` and `/setup verify`.

## ADR-017 — Discord channel/category name literals
Decision: Text and voice channel names use `emoji-kebab-case`, e.g.
`📢-announcements`, matching Discord's own lowercase/hyphen normalization so
stored names stay stable for idempotent name-matching. Category names keep
the emoji-and-title form from `docs/DISCORD_SPEC.md` (e.g. `🏯 SHAHEEN HQ`),
which Discord permits without normalization.

Reason: `docs/DISCORD_SPEC.md` lists conceptual names with spaces; the setup
service needs one literal, deterministic string per resource.

## ADR-018 — Bot's own role is not created by /setup
Decision: The 🤖 SHAHEEN BOT entry in `docs/PERMISSIONS.md`'s hierarchy is
Discord's own managed integration role for the bot, not a role `/setup`
creates. `/setup` locates that existing managed role and verifies/repairs its
position in the hierarchy instead of creating a duplicate.

Reason: Discord auto-creates a managed role for every bot with a role;
creating a second one would be redundant and confusing.

## ADR-019 — uv for packaging and dependency management
Decision: Use `uv` with `pyproject.toml` (`[tool.uv] package = false`, since
Shaheen is an application, not a distributed library) instead of Poetry or
plain pip/requirements.txt.

Reason: Single fast tool for venv, dependency resolution/locking, and running
scripts; good Docker build support; no functional need to publish Shaheen as
an installable package.

## ADR-020 — mypy added in Phase 1
Decision: Configure `mypy` alongside Ruff and pytest from Phase 1 onward,
run in the same quality step `docs/DEVELOPMENT.md` describes.

Reason: `docs/DEVELOPMENT.md` left type checking as "if configured"; catching
typing issues is cheapest before the codebase grows past Phase 1.

## ADR-021 — Welcome/rules/roles messages are static branded embeds
Decision: The welcome/rules/roles messages `/setup` deploys in launch mode
are static, branded embeds (per `docs/BRAND.md`) posted to their respective
channels. Interactive self-service role assignment is not implemented in
Phase 1, since no document specifies which roles should be self-assignable
or the intended interaction.

Reason: Avoid inventing an unspecified UX mechanic; keep Phase 1 scope to
what `docs/ROADMAP.md` actually lists.

## ADR-022 — Brawlhalla API base URL and authentication
Decision: The Brawlhalla integration client uses base URL
`https://api.brawlhalla.com/` and sends an `api_key` query parameter (from
the new `BRAWLHALLA_API_KEY` setting) on every request.

Reason: `dev.brawlhalla.com` itself was unreachable from this environment's
network egress, so this was verified against a community-maintained mirror
of the official client library rather than the live docs, per
`docs/BRAWLHALLA_API.md`'s instruction to verify current documentation.
**This should be re-confirmed against `https://dev.brawlhalla.com/` directly
before relying on it in production** — public sources disagreed on whether
v1.0 still requires a key; the mirrored client's actual request code (which
attaches `api_key` unconditionally) was trusted over an ambiguous search
snippet.

## ADR-023 — /link accepts a Brawlhalla ID or a Steam64 ID
Decision: `/link`'s identifier argument accepts either a raw Brawlhalla
player ID (looked up directly via `/player/{id}/stats`) or a Steam64 ID
(resolved to a Brawlhalla ID via `/search?steamid=`, the only lookup the
API exposes for a non-Brawlhalla-native identifier).

Reason: `docs/COMMANDS.md`'s "request ID" step doesn't say which ID; Steam64
is what most players can actually find (their Steam profile), while some
already know their Brawlhalla ID from third-party trackers.

## ADR-024 — Phase 2 database scope excludes snapshot tables
Decision: The Phase 2 migration adds `DiscordUser`, `ShaheenMember`,
`BrawlhallaPlayer`, and `MemberPlayerLink` only. `RankingSnapshot` and
`LegendSnapshot` are deferred to Phase 3, when `docs/ROADMAP.md` introduces
"scheduled snapshots" as its own item. `/rank`, `/stats`, and `/legends`
read live data from the Brawlhalla API in Phase 2; they do not persist
history yet.

Reason: `docs/ROADMAP.md`'s Phase 2 list is client + `/link` + read
commands only; snapshot storage is explicitly a separate, later roadmap
item, and building it now would be exactly the "later phase" scope creep
`docs/ROADMAP.md`'s own rule warns against.

## ADR-025 — Re-linking replaces the active link after one confirmation
Decision: Running `/link` while a member already has an active
`MemberPlayerLink` shows the existing link alongside the newly-resolved
player and, on confirmation, unlinks the old association (setting
`unlinked_at`) and creates the new one in the same step, rather than
requiring `/unlink` first.

Reason: `docs/COMMANDS.md` doesn't specify this case; requiring two
commands for what is conceptually one action (switching linked accounts)
is worse UX for no safety benefit, since both paths require explicit
confirmation.

## ADR-026 — /link promotes GUEST to TRIAL SHAHEEN only
Decision: On a successful link, if the member currently holds the
👀 GUEST role (or no clan rank role at all), Shaheen assigns
🎯 TRIAL SHAHEEN. Members already holding a higher rank role
(🦅 SHAHEEN, 🏆 ELITE SHAHEEN, 🛡️ MODERATOR, 👑 SHAHEEN LEADER) are left
unchanged — promotion beyond Trial stays a manual staff decision.

Reason: Owner decision — linking is the first step into the clan, not
proof of competitive standing.

## ADR-027 — In-process TTL cache instead of new caching infrastructure
Decision: `BrawlhallaService` keeps a small in-memory, per-process TTL
cache (keyed by endpoint + Brawlhalla ID) instead of introducing Redis or
another cache dependency.

Reason: `docs/BRAWLHALLA_API.md` requires caching and avoiding unnecessary
calls; a single-guild bot with modest command volume doesn't need
distributed caching, and `CLAUDE.md`'s "no major framework/dependency
without justification" rule applies here.

## ADR-028 — Snapshot scheduling: in-process discord.py task loop
Decision: The scheduled snapshot job runs as a `discord.ext.tasks.loop`
owned by a cog, started in `cog_load` and stopped in `cog_unload`, on a
configurable `SNAPSHOT_INTERVAL_HOURS` (default 6). No external scheduler,
queue, or worker process is introduced.

Reason: `CLAUDE.md`'s tech baseline has no job-queue dependency, and a
single-guild bot with a small member count doesn't need one; discord.py
already ships a robust, in-process periodic-task primitive.

## ADR-029 — Snapshots cover both ranked and Legend stats
Decision: Each snapshot cycle writes one `RankingSnapshot` (from
`/player/{id}/ranked`) and one `LegendSnapshot` per played Legend (from
`/player/{id}/stats`.legends) for every member with an active Brawlhalla
link. Rows are append-only, never overwritten (docs/DATABASE.md).

Reason: `docs/DATABASE.md` lists both `RankingSnapshot` and
`LegendSnapshot` as Phase 3 entities and `docs/BRAWLHALLA_API.md`'s
History section asks for "relevant values" generally, not ranked-only.

## ADR-030 — Achievement catalog v1 and where it's evaluated
Decision: v1 ships five achievements, defined in code
(`services/achievements.py`) and seeded into the `achievements` table by
the Phase 3 migration (reference data, not user data):
- `first_link` — linked a Brawlhalla account (awarded immediately by
  `/link`, not the scheduled job)
- `games_100` / `games_500` — lifetime games played crosses 100 / 500
- `tier_platinum` / `tier_diamond_plus` — ranked tier reaches Platinum /
  Diamond or higher

The last four are evaluated once per member per scheduled snapshot cycle,
against the freshly fetched stats, and granted at most once each
(`MemberAchievement` is unique on member+achievement). Achievements are
strictly one-time unlocks; a repeatable event like reaching a new career-
peak rating is a milestone announcement (docs/ROADMAP.md's separate
"milestone announcements" item), not an achievement, and is not stored as
a `MemberAchievement` row.

Reason: Owner decision ("you decide, v1"); this is a small, easy-to-extend
starter set computed entirely from data Shaheen already tracks, with no
invented mechanic beyond what docs/DATABASE.md's `Achievement` /
`MemberAchievement` schema already implies.

## ADR-031 — Ranked tier comparison is a best-effort ordered list
Decision: `tier_platinum`/`tier_diamond_plus` compare the API's free-text
`tier` string (e.g. "Diamond III") against a hardcoded tier-name order
(Tin < Bronze < Silver < Gold < Platinum < Diamond < Diamond+ < Valhallan).
An unrecognized tier string never raises — the achievement is simply not
granted that cycle and is picked up once the name is recognized (e.g.
after the list is updated) or reconciled manually.

Reason: The Brawlhalla API returns tier as display text, not a stable
enum, and this project's own verification of the live API was already
limited (ADR-022) — failing open (skip, don't crash the snapshot job) is
safer than guessing wrong and blocking every player's snapshot.

## ADR-032 — Hall of Fame announcements come from the snapshot job
Decision: Newly-awarded achievements and new career-peak ratings detected
during a snapshot cycle are posted as branded embeds to the
🥇 hall-of-fame channel (looked up via `ProvisionedResource`, same as
`/setup`'s idempotency ledger). If `/setup` hasn't run yet and the channel
isn't provisioned, the snapshot job logs and skips the announcement rather
than failing.

Reason: Ties `docs/ROADMAP.md`'s "achievements", "Hall of Fame", and
"milestone announcements" items together through the mechanism that
already exists (`docs/DISCORD_SPEC.md`'s hall-of-fame channel,
`ProvisionedResource` lookups from Phase 1) instead of inventing a new one.
