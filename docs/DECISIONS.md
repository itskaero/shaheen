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

## ADR-033 — Match results require opponent confirmation
Decision: `/report` records the reporter's claimed result but leaves the
`Match` in a `pending_confirmation` state. The opposing side gets a
Confirm/Dispute prompt (only they can respond). Confirm finalizes the
match (`confirmed`); Dispute marks it `disputed` and leaves it for staff
to resolve manually — no automated dispute resolution.

Reason: Owner decision; self-reported results with no confirmation step
are trivially abusable, and `docs/COMMANDS.md` doesn't specify a
confirmation mechanic, so this fills that gap rather than leaving results
unverifiable.

## ADR-034 — Matches support both 1v1 and 2v2, via a Match/side model
Decision: `Match` has exactly two sides (`A`/`B`); each side has one
`MatchParticipant` for 1v1 or two for 2v2. `/challenge <user>` is always
1v1 (its signature only takes one opponent); `/scrim` and `/match create`
support both `1v1` and `2v2`, matching `docs/DISCORD_SPEC.md`'s existing
⚔️ 1v1 / 👥 2v2 channels and the brief's own choice.

Reason: Owner decision; a single side-based model covers both sizes
without a separate 2v2-only schema, and keeps `/report`'s confirm/dispute
flow (ADR-033) identical regardless of team size.

## ADR-035 — Tournaments: an automated single-elimination bracket engine,
with staff manual override
Decision: `docs/ROADMAP.md` lists "tournaments" for Phase 4 but
`docs/COMMANDS.md` defines no `/tournament` command. Built as: registration
via a Join button on an announcement in 🏆 tournaments, `/tournament start`
generates a single-elimination bracket (seeded by registration order,
byes for non-power-of-2 entrant counts) via a pure, unit-tested bracket
generator (`services/bracket.py`). Each bracket match is a `TournamentMatch`
wrapping a normal `Match` — winning it through the same `/report` +
confirm flow (ADR-033) automatically advances the winner to the next
round and, on the final, completes the tournament. Staff (Moderator or
Leader) can force-resolve a stuck or disputed bracket match with
`/tournament resolve`, which advances the bracket the same way a
confirmed report would, without requiring both sides to agree.

Reason: Owner decision ("both" automated and manual). No seeding-fairness
mechanism (e.g. Elo) exists yet, so registration-order seeding is the only
defensible default; double-elimination, byes-with-reseeding, and
multi-tournament concurrency limits are explicitly out of scope for v1.

## ADR-036 — New staff permission tier: Moderator or Leader
Decision: A new check, `require_staff_authorized()`, authorizes the guild
owner, Administrator-permission holders, or anyone holding 🛡️ MODERATOR or
👑 SHAHEEN LEADER. It gates `/tournament create|start|resolve` and
`/match resolve`. This is distinct from `require_setup_authorized()`
(ADR-010), which stays Leader/admin-only for `/setup`.

Reason: `docs/PERMISSIONS.md` gives Moderators real moderation authority
short of full server administration; tournament/dispute management is
that kind of authority, not `/setup`-level access.

## ADR-037 — XPTransaction stays out of scope
Decision: `docs/DATABASE.md`'s `XPTransaction` entity is not implemented.

Reason: `docs/ROADMAP.md`'s Phase 4 list (challenges, scrims, match
records, tournaments, match history) never mentions XP/leveling, so
building it now would be exactly the "later phase" scope creep
`docs/ROADMAP.md`'s own rule warns against.

## ADR-038 — Challenge/scrim/tournament signup views are session-lived
Decision: Accept/Decline and Join-side buttons use a generous but bounded
`discord.ui.View` timeout (1 hour for challenges/scrims, 24 hours for
tournament registration) rather than a persistent, `custom_id`-routed view
that survives a bot restart.

Reason: Consistent with the `ConfirmView` used since Phase 1
(docs/SETUP_FLOW.md); building persistent-view routing infrastructure is
a separate, non-trivial piece of scope no doc asks for yet. A bot restart
mid-signup means re-running the command — acceptable for v1 at Shaheen's
current scale.

## ADR-039 — Phase 5 stack: FastAPI, JSON API only, no auth
Decision: `docs/ROADMAP.md`'s Phase 5 ("shared application/API layer,
public player profiles, clan page, leaderboard, authentication if
required") is built as a FastAPI app under `src/api/`, exposing read-only
JSON endpoints only — no server-rendered HTML pages, no auth on any
endpoint.

Reason: Owner decisions. FastAPI is async, Pydantic-based (already a
baseline dependency), and sits directly on the existing async SQLAlchemy
sessions with no sync/async bridging. JSON-only matches
`docs/ARCHITECTURE.md`'s literal "application/API layer" wording — a
frontend/template stack is unspecified anywhere and stays a separate,
later decision. No auth because every Phase 5 endpoint is read-only public
data (`docs/PRODUCT.md`: "the public identity/statistics layer") and
nothing in scope needs a write endpoint to protect. `fastapi` and
`uvicorn` are added to the dependency baseline; both are commonly-used,
narrowly-scoped additions, not a framework substitution.

## ADR-040 — Public identity is Brawlhalla identity, never Discord identity
Decision: Every Phase 5 endpoint is keyed and labeled by `BrawlhallaPlayer`
(`brawlhalla_player_id`, `player_name`) — Discord user IDs, usernames, and
display names are never read or returned by the API.

Reason: Two independent reasons converge on the same answer: (1) the API
process has no Discord gateway connection, so it cannot resolve a live
display name the way the bot can; (2) a player's Brawlhalla identity is
already public (they chose it in-game), while publishing their Discord
identity on a public website without that being asked for anywhere is a
privacy overreach `docs/PRODUCT.md` doesn't call for.

## ADR-041 — The website reuses the bot's Settings class unchanged
Decision: `src/api/` loads configuration through the same
`core.config.Settings` the bot uses, rather than a web-specific settings
class. A web-only deployment's environment must still provide
`DISCORD_TOKEN` and `BRAWLHALLA_API_KEY` even though the API process never
uses them.

Reason: `CLAUDE.md`: "do not duplicate configuration." In practice bot and
web share one deployment/`.env` (see docker-compose.yml's new `web`
service), so this costs nothing today; splitting `Settings` into
per-process subsets is a real but premature refactor with no current
requirement forcing it.

## ADR-042 — A separate services/website_service.py, not a reused clan_service.py
Decision: Phase 5 reads go through a new `services/website_service.py`
rather than reusing `services/clan_service.py` (Phase 3/4's
Discord-command-shaped queries).

Reason: The two callers want different shapes from the same tables —
`clan_service.py` returns Discord-identity-bearing tuples for cogs to
resolve into mentions/display names; `website_service.py` must never do
that (ADR-040). Forcing one service to serve both would mean the Discord
layer stripping fields back out, or the API layer filtering a Discord
identity it should never have received in the first place. Both still sit
on the exact same repositories and database (docs/ARCHITECTURE.md) — this
splits the orchestration layer, not the data layer.

## ADR-043 — CORS: allow every origin
Decision: `src/api/app.py` adds `CORSMiddleware` with `allow_origins=["*"]`,
`allow_methods=["GET"]`, so any frontend origin (GitHub Pages, a local dev
server, etc.) can call the API from a browser.

Reason: Every endpoint is already public and read-only with no
authentication (ADR-039) — there is no per-origin data to protect, so
maintaining an allowlist of frontend hosting URLs would add operational
friction (redeploy the API every time the frontend moves) for no security
benefit. `allow_methods` is still restricted to `GET` since the API exposes
no write endpoints.

## ADR-044 — Settings normalizes managed-Postgres connection strings
Decision: `core.config.Settings.database_url` has a validator that rewrites
a bare `postgres://` or `postgresql://` URL to `postgresql+asyncpg://`,
leaving any URL that already names a driver (or a non-Postgres scheme like
`sqlite+aiosqlite://`) unchanged.

Reason: Managed Postgres providers used for free hosting (Render, Heroku,
...) hand out connection strings with no driver suffix, but SQLAlchemy's
async engine requires `+asyncpg` explicitly. Normalizing in `Settings`
means a provider's connection string can be pasted into `DATABASE_URL`
as-is instead of every operator needing to remember to edit it by hand.

## ADR-045 — Public frontend: static HTML/CSS/JS on GitHub Pages, API on Render
Decision: The public Shaheen website (`web/`) is a framework-free static
site — plain HTML/CSS/JS, no build step — that calls the existing FastAPI
JSON API (docs/DECISIONS.md ADR-039) client-side with `fetch()`. It deploys
to GitHub Pages via `.github/workflows/pages.yml` on every push to `main`.
The API itself deploys to Render's free tier via the `render.yaml`
Blueprint (a free web service plus a free Postgres database).

Reason: Owner decisions — "you decide" on frontend stack (recommended:
static HTML/CSS/JS, since `CLAUDE.md` asks not to introduce a framework
without justification, and a handful of read-only pages doesn't need one),
GitHub Pages for frontend hosting (already on GitHub, zero new accounts),
Render free tier for the API+DB (documented trade-off: the free web
service sleeps after 15 minutes idle, ~30-60s cold start on the next
request, and the free Postgres database expires after 90 days unless
upgraded — acceptable for a small private clan's first public presence,
revisit if/when the site needs to stay always-warm). The frontend's API
base URL lives in `web/assets/js/config.js`, a plain constant the operator
edits after the first Render deploy — no build tooling needed to point the
static site at a different backend.

## ADR-046 — `uvicorn api.app:app` needs `--app-dir src`
Decision: Every place that runs the API server directly with `uvicorn`
(README.md, `docker-compose.yml`'s `web` service, `render.yaml`) passes
`--app-dir src`.

Reason: Found while smoke-testing the new deployment configs: `src` has no
project-level install (`[tool.uv] package = false`, ADR-019) and is not on
`sys.path` for a plain `uv run uvicorn api.app:app` — only pytest resolves
`api.app` at all, via `pythonpath = ["src"]` in `pyproject.toml`, which is
test-only. Without `--app-dir src`, both the `docker-compose.yml` `web`
service command and the API-only `uv run uvicorn ...` instructions written
in ADR-039's phase were actually broken outside of `pytest` and the Docker
image's own bot entrypoint (`python -m src.main`, which works differently
since `src/__init__.py` makes it an importable package from `/app`). Fixed
at the source in all three places rather than adding a `PYTHONPATH` env
var, since `--app-dir` is uvicorn's own documented mechanism for this.

**Correction (ADR-057):** the bot-entrypoint aside above was wrong. `python
-m src.main` does make `src` itself importable from `/app` (so `src.main`
resolves), but `src/main.py`'s own imports are absolute and un-prefixed —
`from bot.client import ShaheenBot`, `from core.config import
load_settings`, etc. — which need `bot`, `core`, `database`, ... resolvable
as *top-level* packages. Those live inside `src/`, and only `/app` (the
Dockerfile's `WORKDIR`, added by `-m`'s own cwd-on-sys.path rule), not
`/app/src`, was ever on `sys.path`. The bot's Docker CMD was therefore
never actually runnable as written — see ADR-057 for the real fix and how
it went undetected this long.

## ADR-047 — Frontend visual redesign: the clan's own banner art as the theme
Decision: The homepage hero is the clan's actual Discord server banner
(`web/assets/img/banner.{jpg,webp}`, owner-provided), not the previous
generic gradient hero. Inner pages carry the same artwork as a cropped
`.page-banner` strip (falling back to a themed gradient on narrow
viewports, where the banner's 2.5:1 aspect ratio can't crop cleanly
without cutting into its own logotype). The rest of the UI — tier badges,
rank medals, deterministic player avatars, glass-panel cards with a gold
accent line, glow-on-hover — was redesigned around that artwork's palette
and around the data density of stats sites like corehalla.com, rather than
the plainer flat-card layout Phase 6 shipped with.

Reason: Owner feedback — the original design read as generic/lackluster
next to the clan's own branding, and asked for something closer to a
Brawlhalla stats site, "built around the discord server theme." Using the
real banner is the most direct way to make the site feel like *this*
clan's site rather than a template; tier/rank/avatar treatment is standard
UX for a competitive stats site and was previously missing entirely (the
leaderboard was a plain text table). Verified end-to-end with Playwright
screenshots (desktop + mobile, all four pages) before shipping, including
iterating on the banner crop position after the first pass showed the
logotype getting cut off mid-word.

## ADR-048 — The clan's crest is the site's real logo, with a subtle idle animation
Decision: A second owner-provided asset — a circular falcon-crest emblem,
distinct from the wide banner (ADR-047) — replaces the hand-drawn
`favicon.svg` everywhere: the browser favicon (PNG, since the source is
raster art, not a vector I drew), the nav/footer brand mark, and the
homepage hero, which now centers a large version of the full crest+
wordmark lockup (`web/assets/img/logo-full.*`) with a CSS-only entrance
(fade+scale+blur in), a continuous gentle float + glow-pulse, a slowly
rotating conic-gradient glow ring behind it, and a hover spin on the nav
and footer marks. `web/assets/img/logo-icon.*` is a tighter crop (crest
only, no wordmark) used at nav/favicon sizes, where the full lockup's text
would be illegible. All animation is `both`-filled CSS keyframes/
transitions (no JS animation library, no scroll-linked JS), and a
`prefers-reduced-motion: reduce` media query collapses every animation and
transition to near-zero duration site-wide.

The hero image itself sits on the source art's own near-black square
canvas; rather than showing that as a visible rectangle, `.hero-logo-img`
uses a radial `mask-image` to fade the square's edges into the page
background, so the crest reads as a glowing emblem rather than a pasted
photo. The wide banner (ADR-047) stays in place as the `.page-banner`
strips and a new `.cinematic-strip` divider between the hero and the rest
of the homepage — it's scene-setting key art, not the logo, so it moved
out of the hero position rather than being removed.

Reason: Owner feedback asked for a "modern and professional" look with
"beautiful animations of the logo," and provided this second, cleaner
crest asset specifically for it — a wide action-scene banner and a
circular logo mark serve different jobs (atmosphere vs. identity), so
using the crest as the actual logo and reserving the banner for
supporting art matches how esports orgs typically split the two. Pure CSS
for the animation (vs. a JS animation library) matches `CLAUDE.md`'s "no
unjustified dependency" rule and is trivially disabled for
`prefers-reduced-motion`. Verified with Playwright: screenshotted every
page again, and specifically asserted the hero image's bounding box
position differs across two frames ~1.5s apart to confirm the float
animation is actually running rather than just present in the CSS.

## ADR-049 — Dark neon esports-team visual direction
Decision: The website's chrome (backgrounds, typography, buttons, cards,
badges, dividers, nav) moved to a near-black, neon-glow direction modeled
on competitive-gaming org sites, replacing the earlier heraldic/luxury
green-and-gold treatment from ADR-047/048:
- Background: true near-black with animated aurora-glow gradients and a
  faint animated grid-line texture (`body::before`), instead of the
  softer forest-green gradient.
- Type: `Orbitron` (display/wordmark, brand name, big stat numbers) +
  `Rajdhani` (headings, nav, labels) replace `Cinzel`, uppercase and
  letter-spaced throughout, matching how esports orgs typically set type.
- A gradient "shine" sweep on the homepage `<h1>` and a scrolling ticker
  marquee (motto/tagline, looping) — both common on esports team sites,
  implemented as plain CSS/HTML (no library).
- Buttons, the tier-badge chips, and the nav CTA got an angular
  clip-path-cut corner treatment; left off cards/stats/tables so the cut
  stays a deliberate accent rather than covering every box (see "Reason").
- Cards/stats gained a cursor-follow spotlight highlight
  (`web/assets/js/spotlight.js`, ~30 lines: rAF-batched pointermove sets
  `--mx`/`--my`, read by a `radial-gradient` on `::after`) — a vanilla
  CSS/JS take on the reactbits "SpotlightCard" component the owner asked
  to draw from.
- The palette stayed a closed green/gold/(cyan-in-gradients-only) system
  rather than opening up to arbitrary neon hues.

`docs/BRAND.md`'s "Avoid: excessive neon" / "generic gamer clichés" lines
were updated alongside this ADR to say what that means in practice now,
rather than leaving them flatly contradicting a decision that supersedes
them for the website.

Reason: Owner feedback — the previous design "not good," wanted something
closer to real esports team sites and drawing from reactbits (a React
component-animation library) specifically. Two things drove the
implementation choices: (1) `docs/BRAND.md` already named green/gold/black
as Shaheen's identity and explicitly warned against excessive neon and
generic gamer clichés — so neon went in as a glow *treatment* on the
existing brand hues (green primary, gold secondary, cyan only as a third
gradient note) rather than a new arbitrary palette, and the angular-cut
motif stayed scoped to a few components instead of clipping everything,
to avoid tipping into the clichés the doc warns about. (2) reactbits is a
React component library; adding React + a component dependency to a
plain-HTML static site (ADR-045: no framework without justification) to
borrow a handful of visual effects would be exactly the kind of
unjustified dependency `CLAUDE.md` asks to avoid, especially for effects
(cursor spotlight, shine text, marquee) that are each a few lines of
vanilla CSS/JS. So the brief was read as "build these effects," not
"take this dependency" — same visual outcome, no framework migration.
Verified with Playwright end-to-end (desktop + mobile, all four pages);
the spotlight effect was also confirmed by manually dispatching a
`pointermove` event in the page (Playwright's synthesized mouse events
didn't register as pointer events against this sandbox's mismatched
browser/driver build — a test-tooling quirk, not a site bug, since a
manually dispatched `pointermove` updated `--mx`/`--my` immediately, and
real browsers dispatch genuine pointer events on mouse movement).

## ADR-050 — Homepage as a scroll-triggered landing page; a real trend chart
Decision: Two owner-requested upgrades, both zero-dependency:

1. The homepage (`index.html`) now reveals in beats as the visitor
   scrolls, instead of animating everything in at once on load. Each
   section is wrapped in `.reveal`; `web/assets/js/scroll.js` uses an
   `IntersectionObserver` to add `.in-view` (opacity/translateY
   transition) the first time a section enters the viewport. A new "By
   the Numbers" section between the hero and the clan blurb fetches the
   existing `/clan` and `/leaderboard` endpoints (no new API surface) and
   counts its numbers up once the data arrives — decoupled from the
   scroll reveal itself, so a slow connection never leaves the section
   visibly stuck at zero. The `.cinematic-strip` banner gets a subtle
   scroll-linked parallax (`background-position-y` nudged by a fraction
   of scroll distance, rAF-throttled). A bouncing `.scroll-cue` under the
   hero buttons hints that the page continues. Everything routes through
   `ShaheenMotion` (exposed by `scroll.js`) so page-specific scripts (like
   the new stats fetch) can trigger the same count-up without duplicating
   it, and every effect no-ops under `prefers-reduced-motion`.
2. `web/assets/js/sparkline.js` (the rating-history chart) was rebuilt:
   quadratic-curve smoothing instead of straight segments, gridlines with
   y-axis rating labels and x-axis date labels, a dashed peak-rating
   overlay alongside the current-rating line, a mouse/touch hover tooltip
   with a guide line and highlighted point, and an eased draw-in animation
   on first render. Same zero-dependency canvas approach as before, same
   `drawSparkline(canvas, points)` call site in `player.js` — only the
   ~70-line internals changed.

Reason: Owner feedback, verbatim — build a scroll-animation landing page,
and the trend chart "looks simple or old." Both true: the chart was a
straight-line canvas plot with no axes, no interaction, and it fetched
`peak_rating` without ever showing it; the homepage animated everything on
load rather than as the visitor actually moved through the page, which
doesn't read as a landing page so much as a hero with extra sections
bolted on. Neither fix needed a charting library or a scroll-animation
library (CLAUDE.md: no unjustified dependency) — `IntersectionObserver`
and `requestAnimationFrame` cover both.

Caught in review before shipping: the first pass wrote the live member
count directly onto the `.stat` container element returned by
`querySelector('[data-stat="members"]')` instead of its inner `.value`
span, which clobbered the span and the `.label` text the moment the count
resolved. Playwright's automated check dumped the section's rendered HTML
after load specifically to catch this class of bug, not just screenshot
it — caught immediately, fixed to target `.value` explicitly (matching
the pattern the adjacent "Top Rating" stat already used correctly), and
re-verified before commit.

## ADR-051 — Legend mastery, match history, and tournament brackets go public
Decision: Three more slices of data the bot already tracked, previously
invisible on the website, are now exposed read-only:
- `GET /players/{id}/legends` — each Legend's latest snapshot (ADR-029:
  append-only, so "latest per legend" is the lifetime total), sorted by
  games played. New `LegendSnapshotRepository.list_latest_per_legend()`
  (a group-by-max-captured_at subquery join — the same shape SQL uses for
  "latest row per group" generally).
- `GET /players/{id}/matches` — recent **CONFIRMED** matches only
  (ADR-033/034); pending/disputed/cancelled stay internal, not a public
  result. Resolves the opponent side's `MatchParticipant`s to Brawlhalla
  player names via each one's active `MemberPlayerLink`, same identity
  boundary as everywhere else (ADR-040) — never a Discord-identifying
  detail, and a since-unlinked opponent is silently omitted rather than
  showing an internal id.
- `GET /tournaments` and `GET /tournaments/{id}` — a tournament list and a
  full bracket (all `TournamentMatch` rows per round, each entrant's
  linked player name(s), the winner highlighted). New
  `TournamentRepository.list_for_guild()`. A 1v1 entrant resolves to one
  name, a 2v2 entrant to two (joined with "&" client-side); an entrant
  with no linked members displays as "Unknown" rather than nothing.

All three follow the same shape as every other Phase 5+ endpoint: a
`WebsiteService` method returning a plain dataclass, a thin FastAPI router
converting it to a `pydantic` response model, 404 when the player/
tournament doesn't exist. `website_service.py` picked up read-only
instances of `MatchRepository` and the three `Tournament*Repository`
classes already built for the bot's `/challenge`/`/scrim`/`/tournament`
commands (Phase 4) — no new repository write paths, this is exposure only.

Frontend: the player profile page gained a "Legend Mastery" bar list and a
"Match History" result list; two new pages, `tournaments.html` (list) and
`tournament.html` (bracket, grouped by round with the last round labeled
"Final", second-to-last "Semifinals", third-to-last "Quarterfinals" —
otherwise "Round N" — and a CSS-only connector nub between rounds rather
than routed SVG lines, which is the standard low-effort/high-legibility
bracket layout technique).

Reason: Owner ask ("legend mastery + match history + tournament bracket
viewer") — explicitly the bigger-scope items flagged as needing real
backend work when the feature menu was presented, chosen over the
frontend-only Discord-widget option. Verified against a tournament played
to completion through the real `TournamentService`/`MatchService` (not
hand-poked rows) so the bracket data reflects what the bot itself
produces, not just what a test fixture assumes.

## ADR-052 — Truck-art-inspired divider, applied once
Decision: `.divider-truck` — a small repeating floral motif (a muted
rust-red center with gold petals on a thin gold line, `web/assets/css/
style.css`, tileable SVG data-URI) — appears once, as a closing flourish
on the homepage between "Explore" and the footer.

Reason: The owner's answer to "which Pakistani-identity motif next" was
specifically an *abstracted* truck-art divider, not literal truck-art
imagery — truck art is the most globally-recognized distinctly-Pakistani
decorative form, but rendered literally (or repeated everywhere) it tips
into the "generic gamer clichés"/clutter `docs/BRAND.md` warns against.
Restrained to one motif, one placement, muted rather than truck art's
usual riot of colour, and a small closed set of extra hues (rust + the
existing gold) rather than opening the palette further — same spirit as
ADR-049's neon scoping.

## ADR-053 — Bot hosting: Fly.io, not Render, and why it's a separate deploy
Decision: The bot process deploys to Fly.io's free small-VM allowance
(`fly.toml`, same `Dockerfile` as the API, its default CMD), pointed at
the **same** Postgres database as the Render-hosted API (its External
Database URL, not the internal one — the bot connects from outside
Render's network). This is a third, independent deployment alongside
Render (API + DB) and GitHub Pages (frontend) — `docs/DEVELOPMENT.md`'s
`docker compose up --build` remains the single-command option for
self-hosting all three together instead.

Reason: The bot holds a persistent Discord gateway connection — a
long-lived process, not a request/response server. Render's free tier is
request-driven: a free web service spins down after 15 minutes with no
inbound HTTP traffic (ADR-045), which would silently drop the bot's
Discord connection on a timer regardless of how active the Discord server
itself is, since gateway traffic isn't HTTP traffic Render's spin-down
logic sees. Fly.io's free allowance covers one small always-on VM with no
such request-driven spin-down, and needs no new code — `fly.toml` just
points `flyctl` at the repo's existing `Dockerfile`, whose default CMD
already runs the bot (`docker-compose.yml`'s `bot` service does the same
thing locally). A paid Render Background Worker was the alternative
(simplest given the API is already there) but isn't free, so it lost to
the free option per the standing "free hosting" requirement (ADR-045)
unless the owner says otherwise.

Added `.dockerignore` alongside this (`.git`, caches, `tests/`, `docs/`,
`web/`, markdown) — unrelated to correctness (the Dockerfile's `COPY`
list was already selective, not `COPY . .`) but it shrinks and speeds up
every `flyctl deploy`/`docker build` context upload, which matters once
deploys happen from a real dev machine instead of CI.

Addendum: `fly.toml` originally shipped with no `primary_region`. After
the DB/migration fixes in ADR-054 through ADR-056, the first real deploy
attempt reported the bot as not running with no error from `flyctl`
itself — consistent with the known Fly Machines gotcha where an app not
created via `fly launch` can build and push its image successfully while
placing zero Machines, since nothing tells Fly where to place one. Added
`primary_region = "bom"` (Mumbai — the nearest Fly region to a
Pakistan-based clan; change it if you'd rather use a different one).
**Unverified against the real deploy** — this environment has no
`flyctl`/Fly API access to confirm it against the account this bot
actually runs on, so treat it as the first thing to try, not a confirmed
fix; `flyctl status`/`flyctl logs` output is what would confirm it (or
point at something else entirely, e.g. a startup exception in the
container itself).

## ADR-054 — Free-tier Render: migrations run at boot, via a start script, not preDeployCommand
Decision: `render.yaml`'s `shaheen-api` service no longer sets
`preDeployCommand`. Instead, `dockerCommand` points at a small script
baked into the image, `scripts/render-start.sh`, which runs
`uv run alembic upgrade head` and then `exec`s
`uv run uvicorn api.app:app --app-dir src --host 0.0.0.0 --port "$PORT"`
— the container runs `alembic upgrade head` every time it boots (every
deploy, and every wake from the free plan's idle sleep), then starts the
API.

Reason: Render's `preDeployCommand` is a paid-plan feature — the free
`shaheen-api` service (ADR-044's whole point) can't use it; Render's
dashboard rejects it outright. `alembic upgrade head` is idempotent (a
no-op, just a version-table check, when already at head), so running it
on every boot instead of only "before" each deploy costs a few hundred ms
per cold start and is otherwise free of downside.

Correction 1 (same day): the first version of this ADR chained the two
commands with a bare `dockerCommand: uv run alembic upgrade head && uv
run uvicorn ...` and claimed to have verified it locally. That
verification ran the string through `bash -c '...'` — which itself
supplies the shell that interprets `&&` — so it never actually tested
the failure mode. In production `&&` and everything after it were passed
as literal CLI arguments to `alembic`: `alembic: error: unrecognized
arguments: && uv run uvicorn ...`.

Correction 2 (same day): the fix for correction 1 wrapped the chain in
`dockerCommand: sh -c "uv run alembic upgrade head && uv run uvicorn ...
--port $PORT"`, on the theory that Render tokenizes `dockerCommand` and
execs it without a shell (so the fix supplies one explicitly). That
theory turned out to be wrong too — in production this produced
`sh: 1: uv run alembic upgrade head && uv run uvicorn api.app:app
--app-dir src --host 0.0.0.0 --port 10000: not found`, i.e. Render (or
something in its path to the container) handed the *entire* `sh -c
"..."` string to a shell as one opaque command name, rather than
splitting it into `sh`, `-c`, and the script argument the way a real
shell invocation would. Whatever Render's exact tokenization rules are,
guessing at them a third time isn't worth it. Fix: stop asking
`dockerCommand` to parse an inline shell one-liner at all. Move the
chain into `scripts/render-start.sh` (copied into the image, made
executable in the `Dockerfile`) and set `dockerCommand:
./scripts/render-start.sh` — a single plain path with no quotes, no
`&&`, no `$VAR`, so there is nothing left for Render's parsing to split
wrong. The file's own `#!/bin/sh` shebang is what invokes a shell, not
Render.

Verification note: since this environment has no Docker daemon, this was
verified by `execve`-ing the script path directly (`./scripts/render-
start.sh`, not `sh ./scripts/render-start.sh` and not `bash -c '...'`)
against a throwaway sqlite DB — the same mechanism a container uses to
run a `dockerCommand` — confirming all four migrations apply, uvicorn
starts, and `GET /health` returns 200. This doesn't prove Render's exact
tokenization behavior (still unconfirmed after two wrong guesses above),
but it does remove tokenization from the equation: a single unquoted
path has nothing left to mis-split.

## ADR-055 — Alembic normalizes DATABASE_URL to asyncpg too, not just Settings
Decision: `alembic/env.py` now runs `DATABASE_URL` through
`core.config.normalize_database_url` — the same bare-`postgres://`-to-
`postgresql+asyncpg://` rewrite `Settings.database_url` already applied
via a `field_validator` — before handing it to `async_engine_from_config`.
That rewrite was extracted from the validator into a standalone function
so both call sites share one implementation instead of duplicating the
prefix-swap (CLAUDE.md: don't duplicate configuration/business logic).

Reason: with `scripts/render-start.sh` in place (ADR-054), the next
production deploy got past the dockerCommand problem and failed
differently: `ModuleNotFoundError: No module named 'psycopg2'`. Render's
Postgres `connectionString` (wired into `render.yaml` via
`fromDatabase.property: connectionString`) is a bare `postgresql://...`
URL with no driver suffix. The running app already handled this — its
`Settings.database_url` validator rewrites it to
`postgresql+asyncpg://...` — but `alembic/env.py` reads `DATABASE_URL`
straight from the environment and never went through `Settings` at all
(deliberately: migrations need to run in contexts, like CI, that don't
have Discord/Brawlhalla credentials to construct a full `Settings`
object). SQLAlchemy's async engine, given a bare `postgresql://` URL,
falls back to the default sync driver (`psycopg2`) — which isn't
installed (the project only depends on `asyncpg`) — hence the
`ModuleNotFoundError`.

Verified locally by pointing `DATABASE_URL` at a bare
`postgresql://user:pass@nonexistent-host/db` and running
`alembic upgrade head`: before this fix it failed with
`ModuleNotFoundError: No module named 'psycopg2'`; after it, it fails
with `asyncpg`'s own `socket.gaierror: Name or service not known` for the
fake hostname — proving the async/asyncpg driver is what's actually being
used now, without needing a real Postgres server in this environment.
`pytest`/`mypy`/`ruff` all still pass (the sqlite-backed migration flow
from ADR-054's verification is unaffected — sqlite URLs don't match
either `postgres://` prefix, so `normalize_database_url` is a no-op for
them).

## ADR-056 — Migration 0003's achievements seed binds tz-aware timestamps as tz-aware
Decision: `alembic/versions/0003_clan_tables.py`'s `_ACHIEVEMENTS_TABLE` —
the lightweight `sa.table(...)`/`sa.column(...)` pair `op.bulk_insert()`
uses to know how to bind the achievements seed row parameters — declares
`created_at`/`updated_at` as `sa.DateTime(timezone=True)`, matching the
real `achievements` table's columns (also `DateTime(timezone=True)`,
declared a few lines above via `op.create_table`). It previously declared
them as bare `sa.DateTime` (no `timezone=True`).

Reason: with ADR-054 and ADR-055's fixes both live, the next production
deploy got further than either had and failed a third way, this time
inside migration 0003 itself while seeding the achievements catalog:

    asyncpg.exceptions.DataError: invalid input for query argument $4 in
    element #0 of executemany() sequence: datetime.datetime(2026, 9, 9,
    ...) (can't subtract offset-naive and offset-aware datetimes)

`_ACHIEVEMENTS_TABLE`'s bare `sa.DateTime` column type is only used to
tell `op.bulk_insert()` how to *bind* the parameters for that one
`INSERT` — it's a separate, parallel declaration from the real
`op.create_table("achievements", ...)` columns a few lines above, and the
two had drifted out of sync. Bare `sa.DateTime` compiles the bind as
`TIMESTAMP WITHOUT TIME ZONE`; the actual Python value passed
(`now = datetime.now(UTC)`) is timezone-aware. asyncpg's codec for the
no-tz `timestamp` type internally subtracts the bound value against a
naive epoch reference, and an aware value against a naive epoch is
exactly the `TypeError` string asyncpg reports (wrapped as
`asyncpg.exceptions.DataError` by the time SQLAlchemy surfaces it).

Why the earlier local verification (ADR-054, ADR-055) never caught this:
both were checked against a throwaway **sqlite** database, and sqlite's
driver doesn't type-check or distinguish tz-aware vs. naive `DATETIME`
columns at all — it just stores whatever it's given. The bug is specific
to a real Postgres connection via asyncpg, which every sqlite-based
"verified locally" claim in this file up to this point was structurally
unable to exercise. Postgres itself is available in this dev environment
(`postgresql-16`, unused until now) — verification for this fix instead
starts a local Postgres cluster, reproduces the exact reported error
against it on the unfixed migration (confirmed identical, down to the
`$4::TIMESTAMP WITHOUT TIME ZONE` cast in the failing `INSERT`'s SQL),
then confirms the fix migrates cleanly (`alembic upgrade head`, all four
migrations, no error), that the seeded rows land as genuine
`timestamp with time zone` in the database (checked via `psql`), and
re-runs the full `scripts/render-start.sh` (ADR-054) against that same
Postgres instance end to end — migrate, boot uvicorn, `GET /health` →
200 — the first time that script has been verified against Postgres
rather than sqlite. `pytest`/`mypy` still pass; the two pre-existing
`ruff` findings in this file (an unsorted import block, one over-length
line) predate this change and are untouched by it.

## ADR-057 — Bot's Docker CMD runs `src/main.py` as a script, not `-m src.main`
Decision: The `Dockerfile`'s `CMD` (and README's local-dev instructions)
now run the bot as `uv run python src/main.py` — a plain script
invocation — instead of `uv run python -m src.main`.

Reason: on Fly, the container built and deployed with no error (ADR
addendum on ADR-053), but the bot process itself crashed immediately:

    from bot.client import ShaheenBot
    ModuleNotFoundError: No module named 'bot'
    Main child exited normally with code: 1

This has been broken since Phase 1 and was never actually caught, because
nothing before this deploy ever executed the real container process
boundary — `pytest` resolves `bot`/`core`/`database` via
`pythonpath = ["src"]` in `pyproject.toml`, a pytest-only mechanism
unrelated to how a real `python` invocation resolves imports, and
apparently the bot was never run via `docker compose up` (or the repo
root `uv run python -m src.main` from README) in a way that surfaced it
either. `src/main.py` itself uses absolute, un-prefixed imports —
`from bot.client import ShaheenBot`, `from core.config import
load_settings`, etc. — written on the assumption that `src/` is the
import root, matching every other place in this project that treats it
that way: `alembic/env.py` explicitly does
`sys.path.insert(0, ".../src")`, `docker-compose.yml`'s `web` service and
`render.yaml` both pass uvicorn `--app-dir src` (ADR-046), and
`[tool.mypy] mypy_path = "src"`. `-m src.main` doesn't provide that: `-m`
adds only the *current working directory* (the Dockerfile's `WORKDIR`,
`/app`) to `sys.path`, making `src` itself importable as a package
(`src.main`, `src.core.config`, ...) but never adding `/app/src`, so
`bot`, `core`, `database`, etc. stay unresolvable as top-level names. See
the correction appended to ADR-046, which asserted the opposite without
actually testing it.

Running `main.py` as a plain script instead is Python's own documented
behavior for this exact situation: a script invocation (not `-m`)
prepends the script's own directory to `sys.path[0]`, which is `src/`
here — no `PYTHONPATH` env var or explicit `sys.path` surgery in
`main.py` needed, and it's the same fix shape uvicorn's `--app-dir`
already applies for the API half of this project.

Verified by reproducing the exact reported traceback locally
(`uv run python -m src.main` → `ModuleNotFoundError: No module named
'bot'`, byte-for-byte down to the failing import line) and then
confirming the fixed invocation clears it: `uv run python src/main.py`
with fake credentials runs past every internal import all the way to
discord.py's own login call, failing only on this sandbox's own network
egress allowlist (`discord.errors.Forbidden: ... Host not in allowlist:
discord.com`) — evidence the import boundary that was actually broken is
now fixed, not evidence the bot logs into Discord successfully (this
environment can't reach discord.com to test that part). `pytest`/`mypy`
are unaffected (neither invokes `main.py` as a subprocess).
