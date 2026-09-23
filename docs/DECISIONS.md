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

## ADR-058 — Persistent panels: self-assign roles and a spar kiosk
Decision: Two new standing, restart-surviving panels, both posted
idempotently by `/setup run mode:launch` (extending the existing
welcome/rules/roles message deployment — ADR-021, ADR-054's pattern
reused, not duplicated):

- **Self-assign roles** (`bot/views/roles.py`, `#roles`): a new
  `bot.constants.SELF_ASSIGN_ROLES` tuple — 🔔 Tournament Alerts, 📣 Scrim
  Alerts, 🇵🇰 Pakistan, 🌍 International, 🥊 1v1 Player, 👥 2v2 Player —
  appended to the end of `ROLES` (lowest position, no permissions, not in
  `ROLES_WITH_STAFF_ACCESS`) so `/setup` creates/verifies/positions them
  through the exact same idempotent role machinery as the rank ladder,
  with none of its authority. A toggle-button panel lets members add/
  remove these themselves; the rank ladder itself stays staff-assigned
  (ADR-021 already covered why — nothing about that changes).
- **Spar kiosk** (`bot/views/spar.py`, `#ranked`): two buttons, 🥊 1v1 and
  👥 2v2, that run the *exact* `/scrim` flow (a real `Scrim` row via
  `MatchService`, a join-embed posted to `#scrims`, auto side-matching) —
  not a separate announcement system. `/scrim`'s command body was
  extracted into a module-level `announce_scrim()` function in
  `bot/cogs/competition.py` so both entry points share one
  implementation (CLAUDE.md: don't duplicate business logic) rather than
  the kiosk reimplementing scrim creation.

Reason: owner request — an interactive, self-service roles channel and a
standing "looking for a spar" post, in the channels members would actually
look. `/scrim` already existed and does what a "post for spar" should do
(join button, side auto-matching, tracked in the DB); the kiosk is a
lower-friction *entry point* into it, not a new feature.

**Persistent-view infrastructure, introduced here for the first time**:
`bot/views/competition.py`'s views (Confirm/Challenge/Scrim-join/Report)
are deliberately session-lived (bounded timeout, no custom_id routing —
ADR-038, which explicitly deferred building persistent-view
infrastructure as "a separate, non-trivial piece of scope no doc asks for
yet"). That's still correct for those — a challenge or scrim signup is a
one-shot interaction, not something that needs to survive a restart. A
standing channel panel is different in kind: it must keep working
indefinitely without being re-posted. New `bot/views/base.py`'s
`PersistentView` (`timeout=None`, mirrors `ShaheenBot._on_app_command_error`
for a view's own `on_error`) is the shared base for both new views;
`ShaheenBot.setup_hook()` calls `self.add_view(...)` for one instance of
each on every process start — discord.py then routes any interaction
whose `custom_id` matches to that registered view regardless of which
specific message (or bot restart) it's attached to, which is why the
panel-posting code can create fresh view instances per `/setup run`
without worrying about which one ends up "live" (idempotent posting keeps
`_already_posted` from duplicating the *message*; global registration is
what keeps the *buttons* working either way).

**Import-cycle note**: `bot/views/spar.py` imports `announce_scrim` from
`bot/cogs/competition.py`, and `bot/client.py` imports `bot/views/spar.py`
to register it — so `bot/cogs/competition.py`'s existing
`from bot.client import ShaheenBot` (used only for a constructor type
hint) had to move behind `if TYPE_CHECKING:` to avoid a real circular
import at runtime. Safe because every module here already uses
`from __future__ import annotations` (PEP 563), so annotations were
already never evaluated at runtime.

Verified: `tests/test_constants.py` (new) checks `SELF_ASSIGN_ROLES`
structurally — unique logical_keys/names across all of `ROLES`, no
permissions, not in `ROLES_WITH_STAFF_ACCESS`, positioned after every rank
role. `mypy`/`ruff`/the full `pytest` suite (140 existing tests) all still
pass. Confirmed the import-cycle fix actually resolves by importing
`bot.client`, `bot.cogs.setup`, `bot.cogs.competition`, `bot.views.roles`,
and `bot.views.spar` together in one process (this failed before the
`TYPE_CHECKING` change, with a real `ImportError`). Then, against a
freshly-migrated sqlite database, ran `ShaheenBot.setup_hook()`'s actual
body up to (not including) `tree.sync()` — which needs a real Discord API
call this sandbox can't make — confirming both persistent views register
(`len(bot.persistent_views) == 2`) and all five cogs load without error,
including the modified `setup.py` and `competition.py`. Separately
instantiated both views directly and printed their buttons' `custom_id`/
`label`/`emoji` to confirm all 8 buttons (6 role toggles + 2 kiosk) render
as intended and no `custom_id` collides with another. This doesn't prove
Discord actually accepts these interactions end-to-end (no network access
from this environment), consistent with every other bot-side verification
in this document.

## ADR-059 — Post-launch batch: leaderboard-at-link, channel content, fail-safety, generated imagery, /profile depth

Decision: five related fixes/additions, shipped together after the first
real usage surfaced them.

**1. Leaderboard shows a member immediately after `/link`.**
`SnapshotService._snapshot_one` (private) is now public
`SnapshotService.snapshot_member` — `run_for_guild` calls it exactly as
before; `bot/cogs/link.py`'s `link()` command additionally calls it once,
directly, right after a successful link, in its own `try/except
BrawlhallaAPIError` (mirroring `link_service.py`'s existing "region is a
nice-to-have" pattern — a snapshot hiccup must never fail `/link`
itself). Reason: `LinkService.link()` never created a `RankingSnapshot`;
only the scheduled `SnapshotService.run_for_guild` job did (interval =
`SNAPSHOT_INTERVAL_HOURS`, 6h default), and both `ClanService.leaderboard`
and `WebsiteService.get_leaderboard` skip any player with zero snapshots
— so a freshly-linked member was invisible on both leaderboards for up to
6 hours. No new snapshot-creation logic was written; the existing method
was reused as-is, just renamed to be callable from outside `run_for_guild`.

**2. The website no longer hangs on "Loading…" forever.** No unhandled
backend exception was found for this (`WebsiteService.get_clan_info` only
does a `COUNT(*)`, unrelated to the snapshot issue above) — the real gap
was `web/assets/js/api.js`'s `get()` having no request timeout, so a
Render free-tier cold start (README already documents ~30-60s) or a
genuinely hung request both looked identical to "broken" for as long as
the user waited. Added an `AbortController`-based ~50s timeout with a
clear "waking up" message on timeout specifically, and a short
first-load hint on every page's static loading text (clan/leaderboard/
tournament/tournaments/player). Also gave `create_engine`
(`src/database/session.py`) a `connect_args={"timeout": 10}` for
`postgresql+asyncpg` URLs only (sqlite, used by the whole test suite, is
untouched) — a defensive backstop so an unreachable DB fails fast with a
real error instead of hanging the request the frontend's new timeout is
racing against.

**3. Every text channel gets `/setup run mode:launch` content, and a
channel-send failure can't abort the rest.** `bot/constants.py` defines
24 text channels (plus 4 voice, which never get messages); before this,
`bot/cogs/setup.py` only populated 4 (welcome/rules/roles/ranked). Added
one embed builder per remaining channel in new `bot/content/
channel_intros.py`, and extended `_LAUNCH_MESSAGE_CHANNELS` plus a new
module-level `_launch_messages()` (extracted out of
`_deploy_launch_messages` specifically so `tests/
test_setup_launch_messages.py` can assert every text `ChannelSpec` in
`CATEGORIES` has an entry, without needing a live guild). Each channel's
send is now wrapped in `try/except discord.HTTPException`, logged and
skipped rather than aborting the whole method — a missing permission or
a since-deleted channel no longer takes out every other channel's
content. (A manually *deleted message*, as opposed to a deleted channel,
was already safe before this: `_already_posted`'s history-based title
search just doesn't find it and correctly re-posts on the next
`/setup run`.)

**4. Server-themed generated imagery, via Pillow, not an AI image API.**
No AI image service is configured anywhere in this project (only
Discord/Brawlhalla keys exist) — asked, and the owner confirmed
"use own tools," i.e. generate procedurally rather than adding a new
external API/key/cost. New `src/services/image_service.py`
(Discord-agnostic, no Discord import) renders a branded green-to-gold
diagonal-gradient PNG card from `bot/palette.py`'s existing colors, with
a title/subtitle centered using Pillow's own bundled scalable default
font (`ImageFont.load_default(size=...)`, Pillow >= 10.1) rather than a
bundled or system font file — the Dockerfile's `python:3.12-slim` base
has no fonts installed, so a system-font path would break in production;
shipping a font asset was unnecessary scope for a first pass when Pillow
already bundles one. `ClanCog._announce` (hall-of-fame achievement/
milestone posts) attaches the card via `discord.File`; a render failure
falls back to the plain embed rather than losing the announcement.

**5. `/profile` expanded to be a real one-look card.** It showed only 3
fields (Brawlhalla name, games/wins, one combined rank line); `/rank`,
`/stats`, `/legends` covered the rest as separate commands. Asked, and
the owner said fold detail into `/profile` itself rather than keep it
minimal. `build_profile_embed` (`bot/content/profile_embeds.py`) now
also shows win-rate %, global rank, region (same data `/rank` already
fetches), and — the one field genuinely unsurfaced anywhere before —
"Member Since" from `ShaheenMember.joined_at`. `bot/cogs/profile.py`'s
`_require_link` now returns `(ShaheenMember, BrawlhallaPlayer)` instead
of just the player so `/profile` can reach `joined_at`; `/rank`/`/stats`/
`/legends` are otherwise unchanged (still useful for a quick single-stat
check — this is additive, not a removal).

Reason (all five): traced from actual owner-reported symptoms by three
parallel Explore agents against the real code (not guessed), with two
genuinely ambiguous scope questions — imagery approach, `/profile` depth
— put to the owner before implementation rather than assumed.

Verified: `uv run mypy src` (93 files) and `uv run ruff check src tests`
both clean. Full `pytest` suite green — 153 tests, up from 140 at the
start of this batch: `tests/test_snapshot_service.py` gained a direct
`snapshot_member` test (the public-rename call shape `bot/cogs/link.py`
now uses); new `tests/test_setup_launch_messages.py` (3 tests) asserts
every text channel in `CATEGORIES` has launch content, the tuple/dict
stay in sync, and every embed has a title (required for `_already_posted`
to work); new `tests/test_image_service.py` (3 tests) checks
`render_milestone_card` returns a valid, correctly-sized PNG, including
with long and empty strings. Manually rendered and viewed a sample
milestone card to confirm it's legible and on-brand, not just
"doesn't crash." Ran the same `setup_hook()`-body smoke test as ADR-058
(add_view + load_extension for all 5 cogs) against a freshly-migrated
sqlite DB post-`uv sync` (picking up the new Pillow dependency) to
confirm nothing in this batch broke bot startup. Did not verify against
a live Render/Discord deployment — same caveat as every other
verification in this document; this sandbox has no network access to
either.

## ADR-060 — Bilingual role names, per-channel send permissions, generated imagery redesign, /setup reset

Decision: four related changes, all from the same owner request, after
seeing their own hand-made roles (screenshot) sitting alongside the
bot's auto-created ones with completely different naming.

**1. Role names: "English | Urdu", no emoji, matching the owner's own
hand-made roles.** `bot/constants.py`'s `ROLE_LEADER`, `ROLE_ELITE`,
`ROLE_SHAHEEN` now use the exact Urdu the owner's screenshot confirmed
("Leader | سربراہ", "Elite Shaheen | شاہینِ خاص", "Shaheen | شاہین").
`ROLE_MODERATOR`, `ROLE_TRIAL`, `ROLE_ALLY`, `ROLE_GUEST` are English-only
for now — the owner's screenshot also showed a "Brawler | جنگجو" role
that doesn't map cleanly onto any existing rank, and guessing Urdu for a
real, live server risks getting it wrong. Both are open questions back to
the owner (see the end of this entry), not guessed at.

Every place that had the old names as hardcoded literal strings — most
importantly `bot/content/embeds.py`'s `build_roles_embed()` and
`build_rules_embed()`, and `bot/content/profile_embeds.py`'s promotion
message — was rewritten to reference `bot.constants.ROLE_*` instead of
duplicating the string. That duplication is exactly what let the display
text go stale the first time (the embed still said "SHAHEEN LEADER"
etc. with the old emoji, unrelated to whatever the constant said);
referencing the constant directly makes that class of drift impossible
going forward. Renaming only touches each `RoleSpec.name` — `logical_key`
values are untouched, so `/setup run` picks up the new names as an
ordinary REPAIR action on existing roles, no migration needed.

**2. Per-channel send permissions, layered on the existing category
overwrite pattern.** New `ChannelSpec.staff_only_send: bool = False`
(`bot/constants.py`) — `#announcements` is the first (only, for now) use:
`@everyone` can still view the channel but not send in it, only
`ROLES_WITH_STAFF_ACCESS` can. Implemented as `SetupService.
_channel_overwrites`, a near-exact mirror of the existing `_category_
overwrites` (same shape, same re-applied-every-pass-not-just-repair
behavior so a manually changed Discord permission gets corrected back).
`_apply_channels` now takes `role_by_key` (already computed earlier in
`apply()`, just threaded through) to resolve staff roles into actual
`discord.Role` objects for the overwrite dict.

The owner's other ask here — "bots limited to bot channel" — turned out,
on asking, to mean *other* bots' permissions, a Discord server-config
concern for whichever bot that turns out to be, not something Shaheen's
own code enforces (Shaheen's commands already work everywhere by design,
and it has no visibility into what other bots exist on the server to
scope this generically for). No code change for that part.

**3. Generated imagery redesign: gradient direction, and a faded crest
watermark.** ADR-059's gold-accented diagonal gradient is now a vertical
green-mid-shade-to-dark-shade gradient (`bot.palette.FOREST_GREEN` down
to a computed 28%-brightness version of it), per the owner's explicit
color direction. A faded copy of the clan crest (`logo-icon.png`) is
composited in behind the text as a soft radial-fade watermark (opacity
capped at ~35%, alpha fades to 0 at the edges) — "transparent logo" read
most sensibly as *faded into the background*, since no alpha-channel
source asset exists for the crest (it's a single flat RGB PNG with
gradient shading baked into the artwork itself, not a clean-edged subject
a naive color-key cutout could isolate without looking ragged); faking a
hard cutout badly seemed worse than a tasteful blend using the asset as
it actually is.

The crest asset itself had to move: it lived only at `web/assets/img/
logo-icon.png`, and the bot's `.dockerignore` deliberately excludes
`web/` entirely (only the static frontend needs it — ADR-053's reasoning
for keeping the bot and website deploys separate). A copy now lives at
`src/assets/img/logo-icon.png`, which ships automatically since the
Dockerfile's `COPY src/ ./src/` already copies everything under `src/` —
no Dockerfile change needed, just getting the file inside the directory
that's already copied. `_faded_logo()` returns `None` (not an exception)
if the asset is ever missing, so a card still renders — without the
watermark — rather than losing the whole announcement over it.

**4. `/setup reset` — a new, separately-confirmed, genuinely destructive
command.** Explicitly NOT folded into `/setup run`, which stays the safe,
idempotent, never-deletes-anything command people re-run routinely for
repairs/verification (asked the owner directly given the risk of
permanently losing channel history; they confirmed a separate command).
`SetupService.reset()` deletes every Discord role/category/channel
`/setup` has ever created for the guild (walks `ProvisionedResource.
list_for_guild`, deletes channels/categories first then roles, each
deletion independently guarded so one failure — a missing permission, a
resource already gone — doesn't abort the rest) and then clears the
ledger (`ProvisionedResourceRepository.delete_for_guild`, new) so the
next `/setup run` treats everything as needing fresh creation. It does
**not** touch stored member/player/match/achievement data — only Discord
structure and the idempotency ledger.

Confirmation is two steps, not one: `/setup reset` first shows a plain-
language warning embed with a "Continue to confirm" button
(`_ResetWarningView`, author-locked like the existing `ConfirmView`);
that button's click is what's allowed to call `interaction.response.
send_modal(...)` (Discord requires a modal to be the *direct* response to
the interaction that triggers it, so it can't be shown straight off the
slash command if a warning screen comes first) — the modal
(`_ResetConfirmModal`) requires typing the literal text `DELETE` before
anything is deleted. Both live in `bot/cogs/setup.py` rather than
`bot/views/`, since they're single-purpose and tightly coupled to this
one command, unlike the reusable views in `bot/views/`.

Verified: `uv run mypy src` (93 files) and `ruff check src tests` clean.
Full `pytest` suite green — 158 tests (up from 153): new tests confirm
`#announcements` is `staff_only_send` (`tests/test_constants.py`),
`ProvisionedResourceRepository.delete_for_guild` clears only the target
guild's rows (`tests/test_provisioned_resource_repository.py`), the crest
asset resolves under `src/` not `web/` and `_faded_logo` actually caps
its alpha (`tests/test_image_service.py`). Generated and viewed a sample
card to confirm the new gradient direction and watermark read correctly,
not just "doesn't crash" — legible text, visible-but-subtle crest. Ran
the same `setup_hook()`-body + `SetupCog.setup_group.commands` smoke test
as ADR-058/059 to confirm all 5 cogs still load and `/setup reset` is
registered as a fourth subcommand alongside `run`/`status`/`verify`.
Did not exercise `SetupService.reset()`'s actual Discord deletion calls
or the modal flow end-to-end — this project has no Discord-mocking test
harness for any cog/service that makes live Discord calls (consistent
with every other `setup_service.py`/cog method, none of which are unit
tested either), and this sandbox has no network access to a real guild.

**Open questions back to the owner, not guessed at:** the exact Urdu for
Moderator/Trial (or does "Brawler | جنگجو" replace Trial Shaheen?)/Ally/
Guest, and whether channel names (not just role names) should also go
bilingual — that's a separate, larger question given Discord channel
names are lowercase-and-hyphenated (spaces become hyphens) and it's
unconfirmed whether Urdu script plus a "|" separator survives that
normalization cleanly; docs/DISCORD_SPEC.md's original English-first
channel-naming call (ADR-008) was left as-is pending that answer rather
than guessed at for ~20 channels on a live server.

## ADR-061 — Remaining role Urdu, bilingual channel topics, esports brand fonts for generated imagery

Decision: two follow-ups to ADR-060, both from the owner's request to
"generate Urdu for everything so I can confirm" and to use "a good
esports theme or focused font for images."

**1. The last four role names now carry Urdu.** `ROLE_MODERATOR`,
`ROLE_TRIAL`, `ROLE_ALLY`, `ROLE_GUEST` in `bot/constants.py` move from
English-only to the same "English | Urdu" pattern as `ROLE_LEADER`/
`ROLE_ELITE`/`ROLE_SHAHEEN` (ADR-060): "Moderator | ناظم", "Trial
Shaheen | آزمائشی شاہین", "Ally | اتحادی", "Guest | مہمان". Proposed in
plan mode for the owner's review before writing, rather than guessed at
silently, given a role name is live server state. The Brawler-vs-Trial-
Shaheen question ADR-060 carried over stays open — Trial Shaheen is kept
as its own rank for now; swapping to "Brawler | جنگجو" instead is a
one-line follow-up if the owner still wants that.

**2. All ~23 postable text channels now carry a bilingual topic, not a
bilingual name.** `ChannelSpec.topic` (already a field, previously unset
on every channel) is now set to `"<English> | <Urdu>"` for every text
channel across all six categories. Channel **names** stay English/emoji-
kebab-case, deliberately unchanged — this keeps ADR-008's original
"English channel names" call intact rather than overturning it, because
Discord channel names are auto-lowercased/hyphenated with materially
stricter character handling than role names (which already tolerate
Unicode, spaces, and a literal "|" with no visible problems across four
roles), and this project has no way to test Urdu-plus-pipe survival
against a live Discord guild from this sandbox. The channel **topic**
field has no such normalization — arbitrary Unicode renders as typed — so
it's the zero-risk way to add real Urdu presence everywhere without
gambling with channel identity (and therefore with `ProvisionedResource`
lookups, which are keyed on `logical_key`, not name) on a running server.
No new mechanism needed: `SetupService._apply_channels` already diffs and
repairs `topic` drift for text channels on every `/setup run`. Voice
channels have no topic field in Discord and were skipped.

**3. Generated milestone/achievement images now use the website's own
brand fonts instead of Pillow's bundled default.** `src/services/
image_service.py` replaces `ImageFont.load_default(size=...)` with
`ImageFont.truetype(...)` loads of two bundled OFL-licensed font files —
Orbitron (variable font, `set_variation_by_name("Bold")` selects the bold
instance) for the title, Rajdhani SemiBold (static weight) for the
subtitle — the same two typefaces `web/index.html`/`web/assets/css/
style.css` already use for display/heading text, so the bot's generated
imagery and the website read as one branded system instead of two, and
looks meaningfully more "esports" than a generic sans. `fonts.google.com`
itself is unreachable from this sandbox (proxy 403), so both files were
fetched from Google Fonts' official GitHub mirror
(`raw.githubusercontent.com/google/fonts`, same OFL license, freely
redistributable) instead. The two `.ttf` files live at
`src/assets/fonts/Orbitron-Variable.ttf` and `src/assets/fonts/
Rajdhani-SemiBold.ttf` — inside `src/`, which the Dockerfile's `COPY
src/ ./src/` already copies whole (the same reason `src/assets/img/
logo-icon.png` lives where it does, ADR-060), so no Dockerfile change was
needed. A new `_load_fonts()` helper wraps both `ImageFont.truetype(...)`
calls in a `try/except OSError` that falls back to
`ImageFont.load_default(size=...)` per font — matching `_faded_logo()`'s
existing fail-safe philosophy: a card with the wrong font is fine, a
crash losing the whole announcement is not.

Verified: both font files download over HTTPS through this sandbox's
proxy and load with Pillow; `Orbitron-Variable.ttf` exposes named
instances `Regular`/`Medium`/`SemiBold`/`Bold`/`ExtraBold`/`Black` via
`get_variation_names()`. Rendered and sent the owner a sample milestone
card with the real fonts wired in (not just the standalone verification
script) to confirm the look before and after this change. `uv run ruff
check src tests` / `uv run mypy src` (93 files) clean. Full `pytest`
suite green — 159 tests (up from 157): two new tests in
`tests/test_image_service.py` assert both bundled font files exist under
`src/` (not `web/`, mirroring `test_logo_asset_ships_inside_src`) and
that `_load_fonts()` actually returns `ImageFont.FreeTypeFont` instances
rather than silently falling back to the generic default.
`tests/test_constants.py`'s existing role/channel structural tests
(unique logical keys, unique names, `#announcements` staff-only-send)
still pass unchanged — adding `topic=` values and Urdu to role names
didn't touch any of the invariants those tests check.

## ADR-062 — Generated imagery moves onto the owner's achievement-frame artwork, "bevel & highlight" text treatment

Decision: replace `image_service.py`'s procedurally-generated background
(a flat gradient plus a faded logo watermark — ADR-059/ADR-060) with the
owner's own finished achievement-frame template artwork, styled with a
metallic-gold text treatment chosen from three prototyped options.

**Why a template instead of procedural generation.** The owner supplied a
professionally composed frame (crest, gradient, mountains, Pakistan
motifs, bilingual corner taglines) and wants the bot's generated cards to
look like that piece, not a simpler procedural approximation of it. Before
touching the real service, the text-effect treatment was prototyped in
total isolation — a standalone script outside the repo, three visual
variants sent to the owner for comparison (metallic extrusion, bevel &
highlight, clean glow) — so the owner could pick a direction before any
production code changed. They picked **Bevel & Highlight**.

**What changed in `src/services/image_service.py`:**
- New asset `src/assets/img/achievement_template.png` (the owner's
  template, ~1.9MB) is now the entire card background — `CARD_WIDTH`/
  `CARD_HEIGHT` become the template's own dimensions (1672×941, up from
  the old procedural canvas's 800×300). Lives under `src/` for the same
  reason `logo-icon.png` and the bundled fonts do (Dockerfile's `COPY
  src/ ./src/`, `.dockerignore` excludes `web/` — ADR-060).
- The old `_vertical_gradient`, `_faded_logo`, and `_LOGO_PATH` are gone —
  the template already carries the gradient and crest, so generating them
  separately and layering a watermark on top no longer applies. `render_
  milestone_card(*, title, subtitle)` keeps its exact signature (one call
  site, `bot/cogs/clan.py`) but now composites both strings into a fixed
  safe rectangle inside the template's own empty content area (`_CUTOUT_
  BOX`, confirmed visually against the asset — inset from the gold frame
  and the diamond ornaments), rather than centering them on a blank
  gradient.
- **Text treatment** ("bevel & highlight", `_render_styled_text`): a
  subtle diagonal extrusion (`_extrude`, 4 steps) for carved depth, a thin
  dark stroke ring (`_make_masks` builds inner/outer glyph masks at the
  same canvas offset so a gradient fill and a stroke-only ring stay pixel-
  aligned — the ring is stroke color showing through where the gradient
  layer doesn't reach), a three-stop gold-to-bronze metallic gradient fill
  (`_vertical_gradient_multi`, a generalization of the old two-stop
  gradient to an arbitrary number of stops), a soft top-band highlight
  confined to the glyph shape (`_bevel_highlight`, multiplies a vertical
  fade band against the glyph mask rather than lighting the whole card) for
  the carved-medallion look, and a moderate gold glow. One fixed style,
  reused for both strings — only font/size differ.
- **Long text shrinks instead of overflowing or clipping** (`_fit_font`):
  starts at a generous size and steps down until the rendered text fits
  the safe width, falling back to Pillow's generic default font if a
  bundled font file is ever unreadable (same fail-safe precedent as every
  other font-loading path in this file).
- **No dynamic Urdu.** The prototype proved Urdu renders correctly (raqm
  shapes/joins/reorders it — confirmed in the standalone experiment), but
  `title`/`subtitle` are runtime strings (a Discord display name, an
  achievement's name) with no Urdu translation available at render time —
  there's nothing to translate. Bilingual brand presence stays where it
  already lives: baked into the template artwork's own corner captions.
- **Rendering moved off the event loop.** The new render is real Pillow
  work over a ~1.9MB image — measured at ~0.7s per card (dominated by PNG
  encoding a 1672×941 RGBA composite; `optimize=True` was tried and
  dropped — it cost ~3.8s for a few percent smaller output, not worth
  risking event-loop stalls over). `bot/cogs/clan.py`'s `_announce` now
  calls `render_milestone_card` via `asyncio.to_thread` instead of
  directly; the existing try/except fail-safe (a rendering failure never
  loses the announcement, just falls back to the plain embed) is
  unchanged.

**Known limitation, not addressed here:** neither bundled font (Orbitron,
Rajdhani) has emoji glyphs, so an achievement subtitle that includes an
emoji (e.g. `"🏅 {achievement.name}"`, built in `bot/content/clan_embeds.
py`) renders a missing-glyph box for the emoji in the generated image —
pre-existing since ADR-061 switched off Pillow's default font, not a
regression introduced here. A proper fix (bundling a symbol/emoji-capable
fallback font) is future scope, not blocking this change.

Verified: ran the real `render_milestone_card` (not just the prototype
script) against a short name, a long display-name-plus-achievement-text
pair (confirms `_fit_font` shrinks correctly and nothing overflows the
frame), and empty strings (existing edge-case test) — all three sent to
the owner as rendered PNGs. `uv run ruff check src tests` / `uv run mypy
src` (93 files) clean. Full `pytest` suite green — 160 tests: `tests/
test_image_service.py` rewritten for the new public surface (`_fit_font`,
`_make_masks`, `_TEMPLATE_PATH`) in place of the removed `_faded_logo`/
`_load_fonts`/`_LOGO_PATH`, plus a template-ships-under-`src/` test
mirroring the existing font-asset test. `git status` confirms the
prototype script itself was never part of this repo — it lived and stayed
in the session scratchpad throughout, only the chosen variant's approach
was ported into `image_service.py`.

## ADR-063 — Aggressive site-wide copy pass + animated `join.html` Discord landing page

Decision: sharpen the website's voice from calm/data-first to a confident, competitive
esports tone across all pages (owner request), and add a dedicated, animated landing page
whose only job is converting visitors into Discord members via the real invite
(`https://discord.gg/GTuQaE7WfF`).

**Tone, reconciled with `docs/BRAND.md`'s guardrails.** BRAND.md explicitly warns against
"childish copy" and "generic gamer clichés." The rewrite stays inside those lines —
confident and challenge-driven ("we don't carry dead weight", "ranked by results, not
excuses") rather than juvenile or emoji-spammy — the same reconciliation move ADR-049 made
for "neon" (a glow treatment on the existing palette, not a new one, so it reads as a
competitive-gaming org, not a cliché). Changed: `index.html`'s ticker/hero tagline/"The
Clan" copy, and one punchy intro line each on `clan.html`, `leaderboard.html`,
`player.html`, `tournaments.html`, `404.html`. Left alone: nav link text (Home/Clan/
Leaderboard/Players/Tournaments — needs to stay instantly parseable), every data table,
stat label, and the footer's factual attribution line — "aggressive" is a prose thing,
never something a user needs to parse correctly.

**Real Discord invite wired in.** `web/assets/js/config.js`'s `DISCORD_INVITE_URL` was an
empty placeholder (the nav "Join Discord" CTA has been hidden on every page since it was
built); it's now `https://discord.gg/GTuQaE7WfF`, so the existing `wireDiscordLink()`
(`web/assets/js/api.js`) unhides and points that button site-wide — no JS logic changed,
just the config value it was already waiting on.

**New page: `web/join.html`.** Built the same way every other page in this site is (there's
no shared nav partial — `docs`'s own prior exploration confirmed every page hand-repeats
the header/nav/footer block — so `join.html` follows that exact pattern, and a `Join` link
pointing to it was added to the nav on all 7 existing pages, one identical edit repeated
seven times). Reuses the site's existing motion system entirely — `heroEntrance`/
`heroFloat`/`shine` for the hero, `tickerScroll` for the marquee, `.reveal`/`fadeInUp`/
spotlight-glow for the "Why Join" cards, the existing truck-art divider — no new JS files.
The one genuinely new visual: a `cta-pulse` modifier (a pulsing glow ring, same
`--neon-green` token already used on every other primary button) on the page's Discord CTA,
covered automatically by the stylesheet's existing wildcard
`prefers-reduced-motion` kill-switch (`*, *::before, *::after { animation-duration:
0.001ms !important; ... }`) — no separate opt-out needed for a new animation.

**Second brand asset.** The owner supplied a second, more detailed transparent lockup
(full eagle crest + "SHAHEEN / BRAWLHALLA CLAN" wordmark + the Urdu tagline + "HIGHER
TOGETHER," all baked into the artwork, genuinely transparent background — unlike
`logo-full.png`, which sits on a near-black square canvas that `.hero-logo-img`'s
`mask-image: radial-gradient(...)` fades into the page). Saved as `web/assets/img/
shaheen-lockup.png`/`.webp` (resized from the source 1254×1254 down to 840×840 — plenty
for the display size, keeps the file reasonable), used as `join.html`'s hero visual. A new
`.hero-lockup-img` CSS class reuses `.hero-logo-img`'s float animation but sets
`mask-image: none` and a larger `clamp()` — applying the existing mask to this asset would
have clipped real wingtip artwork the old mask was never designed to touch. Not swapped in
site-wide; `index.html`'s hero and the nav/footer crest keep their existing assets, since
this task was scoped to the new landing page.

**Deploy**: no config needed — `.github/workflows/pages.yml` uploads all of `web/` as
a static artifact on every push to `main` touching `web/**`, so `join.html` and the new
image assets ship automatically.

Verified: served `web/` locally and screenshotted `index.html` and `join.html` with
headless Chromium (this sandbox has no `playwright`/`puppeteer` npm packages installed, so
a minimal from-scratch Chrome DevTools Protocol script was used instead — `Page.navigate`,
wait past the CSS entrance-animation delays, `Page.captureScreenshot`) — confirmed the new
lockup renders with no mask clipping, both Discord CTAs (hero + closing) render with the
pulsing glow, the "Why Join" cards and truck-art divider render correctly, the Urdu motto
line shapes correctly, and `index.html`'s reworked ticker/tagline/"The Clan" copy renders
without breaking layout. Grepped for `href="join.html"` — present on all 7 existing pages
plus `join.html`'s own active nav state (8 total), and `discord.gg/GTuQaE7WfF` — present in
`config.js` and both of `join.html`'s hardcoded CTA hrefs, no typos. No JS/build step exists
for `web/` — nothing to lint/type-check; visual confirmation in a real browser is the
verification, same as prior website-visual ADRs (049/051/053/054/062).

## ADR-064 — Consistent Nastaliq Urdu everywhere it appears + a fresher English typeface pairing

Decision: fix Urdu text rendering inconsistently across the site, and swap the English
heading/body faces (owner feedback: the old pairing "looks stale or outdated").

**The real Urdu bug.** `Noto Nastaliq Urdu` was only ever applied via the `.motto` class,
used exactly once (join.html). Every other Urdu instance — the ticker's Urdu span (5
pages) and the footer's "بلندیوں کی جانب" tagline (all 8 pages) — had no font-family rule
targeting it at all, so it silently fell back to the body font stack (Poppins/system
sans), which has no Nastaliq glyphs — browsers then substitute *some* system Arabic-
capable font, arbitrarily, never the calligraphic face the site was actually going for.
Worse, `404.html` and `tournament.html` didn't even load the `Noto Nastaliq Urdu` font
file in their `<head>`, so even a correct CSS rule couldn't have fixed those two pages.

Fix: every Urdu run is now wrapped in `<span lang="ur">…</span>` (or, for join.html's
motto — a standalone Urdu paragraph — the attribute goes directly on the `<p>`), and one
new global rule picks it up:
```css
[lang="ur"] {
  font-family: "Noto Nastaliq Urdu", serif;
  direction: rtl;
  unicode-bidi: isolate;
}
```
One rule instead of a class-per-spot, so any future Urdu text anywhere on the site gets
the right font automatically just by marking it `lang="ur"` — no CSS change needed. All 8
pages' Google Fonts `<link>` now load `Noto Nastaliq Urdu` (added to the two that were
missing it).

**English pairing.** `Rajdhani` (headings/nav/labels) → **Space Grotesk**; `Poppins`
(body) → **Sora**. `Orbitron` (the big display wordmark) is unchanged — distinctive, not
what read as dated. Both new faces are modern geometric sans faces already common in
current tech/gaming product UI, picked over a bolder "HUD" alternative (Chakra Petch +
Inter) to keep the shift a refresh rather than a different visual language — consistent
with "UI is fine" from the ADR-063 request this follows. `--font-display`/`--font-
heading` custom properties and the `body` font-family were updated in one place each
(`web/assets/css/style.css`); no per-page CSS.

Verified: served `web/` locally, confirmed `fonts.googleapis.com` was actually reachable
this time (retried after an earlier transient SSL failure), and screenshotted
`index.html`/`join.html` with the same headless-Chrome-via-CDP script from ADR-063 —
confirmed Space Grotesk/Sora render on headings/body text, and the Urdu ticker/footer/
motto all render in the calligraphic Nastaliq style rather than a generic fallback.
Grepped `lang="ur"` counts against expected occurrences per page (3 on the 5 ticker
pages, 1 on tournament.html/404.html, 2 on join.html) — all matched. No JS/build step for
`web/`; visual confirmation is the verification, same as every prior website ADR.

## ADR-065 — Moderation commands, Brawlhalla-themed chat gamification, and branded welcome/leave cards

Decision: add a structured, bot-tracked moderation system with an audit trail (owner
request — the bot had zero bot-side moderation commands; `ROLE_MODERATOR` only got native
Discord kick/timeout/purge through Discord's own UI, with no warning system, no log, no
slash-command discoverability), build message-based chat XP/leveling now rather than just
designing it, and replace the one-time static `#welcome` embed with per-member join *and*
leave cards using owner-supplied branded templates.

### Part A — Moderation + `#mod-log`

New restricted category `🛡️ MODERATION` (`category:moderation`, `bot/constants.py`) —
`restricted=True`, same visibility treatment as `DEVELOPMENT`/`SHAHEEN ARENA` — holding one
channel, `channel:mod_log`. Picked up automatically by the next `/setup run` on any
existing guild, same as every other `CATEGORIES` addition in this repo's history — no
Discord-structure migration needed.

New table `warnings` (`src/database/models/warning.py`, migration `0005`): `guild_id`/
`discord_id` (BigInteger, indexed) identify the warned member by raw Discord ID —
deliberately **not** FK'd through `DiscordUser`/`ShaheenMember`, since a member can be
warned without ever having run `/link`. `active` (default `True`) lets `/clearwarnings`
soft-clear rather than delete, preserving the audit trail. `WarningRepository`: `add`,
`list_active_for_member`, `count_active_for_member`, `clear_all_for_member`.

New cog `bot/cogs/moderation.py` (`ModerationCog`), every command gated by
`require_staff_authorized()` (no new permission tier — reuses the exact check `/setup`
already uses): `/warn`, `/warnings`, `/clearwarnings` (new — nothing native did this),
plus thin `/kick`/`/ban`/`/timeout`/`/purge` wrappers around discord.py's own
`Member.kick`/`ban`/`timeout`/`TextChannel.purge`. Destructive actions
(`/clearwarnings`, `/kick`, `/ban`) go through `ConfirmView` (`bot/views/confirm.py`,
already used by `/unlink`/`/setup reset`) first; a shared `_confirm()` helper collapses
the kick/ban confirmation boilerplate into one method. Every action posts an embed to
`#mod-log` (`resolve_provisioned_channel`, the same reusable channel-lookup function
`bot/cogs/competition.py` already exposes for `#hall-of-fame`). `discord.Forbidden` is
caught everywhere a Discord call can fail because the bot's own role lacks a native
permission — a separate concern from `require_staff_authorized()`, which only gates who
can *invoke* the command, not what the bot itself is allowed to do.

### Part B — Chat-message XP/leveling, surfaced on the website

New pure-logic module `services/chat_gamification.py` (Discord/DB-free, same shape as
`services/achievements.py`, ADR-030's precedent — deliberately a *separate* system from
achievements, which track Brawlhalla-API progress, not in-Discord activity):
- A quadratic XP curve, `xp_for_level(n) = 100 * (n-1)**2` / its exact inverse
  `level_for_xp`. Level 2 at 100xp, level 3 at 400xp, level 10 at 8,100xp — fast early
  levels, slowing down at higher ones, standard Discord-bot XP pacing.
- A Brawlhalla-flavored rank-title ladder, deliberately distinct from Brawlhalla's own
  ranked tiers so a chat level is never confused with ranked standing: Hatchling (1) →
  Brawler (5) → Warrior (10) → Veteran (15) → Elite (20) → Legend (25) → **Valhallan**
  (30+) — a single deliberate echo of Brawlhalla's own top ranked tier, reused as the
  chat ladder's capstone.
- `roll_message_xp()` — a random 5–15 XP per eligible message, not a fixed amount, so
  activity isn't perfectly predictable/farmable.

New table `chat_activity` (same migration as Part A): `guild_id`/`discord_id` (unique
together, same "not FK'd through ShaheenMember" reasoning as `warnings` — everyone who
talks earns XP, not just linked members), `xp`, `level`, `message_count`, `last_xp_at`
(drives a 60s anti-spam cooldown, `MESSAGE_XP_COOLDOWN_SECONDS`). `level` is a write-path
convenience only, set by the caller on a detected level-up so it can diff old-vs-new —
`ChatActivityRepository.record_message` deliberately never writes it itself. **Every read
site must derive the level live** via `level_for_xp(xp)` rather than trust the stored
column, since a message that doesn't cross a level threshold leaves it stale; this was
caught during manual end-to-end verification (a 150xp member showed level 1 instead of
the correct level 2) and fixed at all three read sites — `bot/cogs/engagement.py`'s
`/level` and `/chatboard`, and `services/website_service.py`'s `get_community_activity`.

New cog `bot/cogs/engagement.py` (`EngagementCog`) — chat XP and welcome/leave together
(both are Discord-event listeners, not staff-gated, a natural pairing distinct from
`ModerationCog`'s permission model): `on_message` applies the cooldown, awards XP, and on
a detected level-up posts a `render_milestone_card`-based announcement to `#hall-of-fame`
(already the "something worth celebrating" channel). `/level [user]` and `/chatboard` —
no permission check, same posture as `/profile`.

**Website surface, reconciled with ADR-040's privacy stance.** `website_service.py`
never exposes raw Discord identity — only `BrawlhallaPlayer` fields are public. Publishing
a raw chat leaderboard by Discord username would cross that line, so the public
**Community Activity** section only includes members who are *also* actively linked to a
Brawlhalla profile, displayed by their **Brawlhalla player name**, never their Discord
handle — the same identity rule every other `website_service.py` method already follows.
A member who chats a lot but hasn't run `/link` still earns XP and shows up in
`/chatboard` inside Discord, just not on the public site — not a new carve-out, the
existing "public site mirrors linked, public Brawlhalla data" rule applied here too.
`get_community_activity` (`website_service.py`) → `CommunityActivityEntryResponse`
(`api/schemas.py`) → `GET /community/activity` (`api/routers/community.py`, registered in
`api/app.py` next to the other four routers, no CORS change needed — ADR-043 already
allows any origin for GET) → `ShaheenAPI.getCommunityActivity` (`web/assets/js/api.js`) →
a new "Community Activity" table on `web/clan.html` (`web/assets/js/pages/clan.js`,
mirroring `leaderboard.js`'s map→string→`innerHTML` pattern, in its own try/catch so a
failure there can't take down the rest of the page).

**Operational note**: chat-XP tracking needs the **`message_content` privileged intent**
enabled for this application in the Discord Developer Portal (the code already requests
every intent via `discord.Intents.all()`, `bot/client.py` — but that portal toggle lives
outside this repo). Without it, `on_message` simply never fires with readable content and
no XP is ever awarded — fails safe, the rest of the bot is unaffected either way, but
worth flipping before/soon after this ships.

### Part C — Welcome / leave cards, using the owner's branded templates

The owner supplied a branded "WELCOME TO SHAHEEN CLAN" / "GOODBYE UNTIL WE MEET AGAIN"
composite template (same visual family as `achievement_template.png` — crest, gradient,
corner taglines, an empty rectangular cutout for dynamic text) — superseding the earlier
plan of a plain-text leave message: both join *and* leave now render a real branded card.
Split into `src/assets/img/welcome_template.png`/`goodbye_template.png` at the composite's
visible center divider, shipped the same way `achievement_template.png` already does
(`src/assets/img/`, `Dockerfile`'s `COPY src/`). `image_service.py` gained
`render_welcome_card`/`render_goodbye_card`, sibling functions reusing every existing
ADR-062 building block (`_render_styled_text`, `_fit_font`, `_trim`, the gradient/
extrusion/stroke/glow text treatment) — only the template path and each template's own
measured cutout-box coordinates differ; `render_milestone_card` itself is untouched.

Both post to the existing `#welcome` channel — no new channel. `on_member_join` also
**auto-assigns the Guest role** (`ROLE_GUEST`, resolved via `ProvisionedResourceRepository`
the same way every other role/channel lookup in this codebase works) before posting the
welcome card, so the rank ladder means something from a member's very first message
rather than only starting at `/link`-triggered promotion. `on_member_remove` posts the
goodbye card with a low-key caption — no mention/ping, since the member has already left
and a ping would fail anyway. Both renders run off-thread (`asyncio.to_thread`, same
CPU-bound-off-the-event-loop reasoning as `render_milestone_card`'s call site) and are
wrapped in try/except so a render failure or `discord.Forbidden` never crashes the
listener — the card render is best-effort, not load-bearing.

### Part D — Further community-enthusiasm ideas (discussed, not built this round)

Written up for the owner to pick from later:

| Idea | What it is | Rough effort |
|---|---|---|
| Weekly recap digest | Auto-posted Sunday summary: top rating gains, most active chatters, matches played | Small — reuses snapshot loop's weekly cadence + existing repos |
| MVP of the Week | Auto- or staff-picked member (biggest rating jump / most chat XP that week) gets a callout + a temporary cosmetic role | Small-medium — needs a "top mover this week" query, a temp-role assign/remove job |
| Clan-wide milestone bar | A shared goal (e.g. "1,000 combined ranked wins") with a progress announcement at each 10% | Medium — needs a running clan-wide counter + threshold-crossing detection, mirrors the achievement-evaluator shape |
| Member spotlight | Staff-triggered `/spotlight user note` posting a featured-member embed | Small |
| Suggestions inbox | `/suggest text` posts anonymously to `#suggestions` with 👍/👎 reactions for the community to vote | Small |
| Casual matchmaking panel | A persistent "Looking to duo/scrim" panel beyond ranked spars, extending the existing spar-kiosk pattern (ADR-058) | Medium — new persistent view, mirrors `bot/views/roles.py`/spar kiosk exactly |
| "On this day" nostalgia | Auto-posts a past achievement/milestone from N months ago | Small, needs a scheduled job + a query over existing achievement/snapshot history |
| Opt-in birthday shoutouts | Member-set birthday (month/day only), auto-shoutout on the day | Small, but privacy-sensitive — must be opt-in and store no year/exact DOB |

Verified: `uv run pytest` (190 passed, including new `test_chat_gamification.py` — exact
curve thresholds + monotonicity, `test_warning_repository.py`, `test_chat_activity_
repository.py`, and extended `test_website_service.py`/`test_constants.py` coverage);
`uv run ruff check src tests` / `uv run mypy src` clean. `GET /community/activity`
exercised against a seeded test DB confirming both halves of the ADR-040 reconciliation:
a linked member with chat activity appears under their Brawlhalla name, an unlinked-but-
chatty member (99,999 XP) does not appear at all. `render_welcome_card`/
`render_goodbye_card` rendered directly against sample names and sent to the owner for a
look, the same verification step ADR-062's achievement card got, confirming the cutout-
box coordinates were measured correctly against each new template. Cog loading smoke-
tested the same way every other cog in this repo is (no live-Discord test harness exists
for anything making real Discord calls).

## ADR-066 — Website redesign: premium esports/stat-tracker direction, scroll storytelling, deeper Discord/Brawlhalla data

Decision: replace ADR-049's dark-neon-cyberpunk visual direction with a calmer, more
premium "esports team / stat-tracker" look (owner request, explicitly **not** neon-sign
or glitch/technoware fonts) — inspired by corehalla (clean, data-dense Brawlhalla stat
tracker) and PlayerX-style ThemeForest esports templates (angular sections, bold
team-site headings). *Both reference URLs were unreachable from this sandbox (network
egress proxy blocks corehalla.com and preview.themeforest.net) — confirmed with the
owner, who approved working from established genre conventions instead of a pixel
match.* Also: consolidate the site's two crest assets into one, build a scroll-mapped
homepage hero around the owner's 5-character banner, add a more deliberate reveal
animation to `clan.html`, and wire in three pieces of deeper Discord/Brawlhalla
integration. Scope: reskin all 8 existing pages, keep every page's data-fetching
untouched (`ShaheenAPI`, `website_service.py`, every endpoint) — a visual/structural
pass on top of unchanged functionality.

**Dropped, specifically the neon/glitch/technoware tells**: the `--neon-cyan` accent
(BRAND.md only sanctions green/gold; cyan was ADR-049's own liberty), the `textGlitch`
nav-hover keyframe (removed outright), default-everywhere `text-shadow` glow on ticker
text/nav links/stat values/table headers/dividers (glow now lives only on a few
deliberate accent moments — primary CTA, active nav underline, hover lift), and
`Orbitron` (a sci-fi/HUD-coded display face). **Kept**: BRAND.md's palette (deep forest
green, emerald, gold, black, cream) and motifs — untouched, non-negotiable — plus the
angular diagonal-cut `clip-path` language (`--cut`/`--cut-sm`), which reads as
PlayerX-style esports-team, not neon cliché, so it stayed and got a new diagonal
section-divider motif built on the same idea. **New type system**: `Bebas Neue` for
display type and big stat numbers (a standard sports/esports-team jersey face, zero
sci-fi connotation) replacing Orbitron; `Space Grotesk` (headings/nav) and `Sora` (body)
carry over unchanged from ADR-064.

**Logo consolidation.** `logo-full.png` (a near-black-canvas crest needing a CSS radial
mask to fake transparency, used only on `index.html`'s hero) and `shaheen-lockup.png`
(genuinely transparent, crest+wordmark+tagline, used only on `join.html`'s hero) were
two assets doing the same job. Now `shaheen-lockup.png/.webp` is the *one* hero crest,
used on both pages — the mask hack is gone entirely. `logo-icon.png/.webp` (the 34px nav
mark / 30px footer mark) was re-derived from the same lockup artwork (a PIL crop to just
the eagle/wings/crescent arch, no wordmark) instead of being a separately-generated
asset, so every crest touchpoint on the site now traces back to one source image;
`favicon-32/48.png`/`apple-touch-icon.png` were regenerated from the same crop for the
same reason. `logo-full.png/.webp` deleted, not just unreferenced.

**Homepage scroll-mapped hero.** The owner's 5-character banner (werewolf, hooded
rogue, central valkyrie, horned viking, ninja) becomes a "scrollytelling" section:
`web/assets/js/pillar-scroll.js` (new, homepage-only) pairs a `position:sticky` banner
image with five stacked 100vh text panels. Rather than pre-cutting five separate
masked character images (attempted first, discarded — matching each character's silhouette
by hand with only PIL's basic ops in this sandbox risked a bad crop that couldn't be
visually pre-verified against a rendered page), the "spotlight" is a single source image
(`hero-characters.jpg/.webp`) plus a runtime CSS radial-gradient vignette
(`.pillar-vignette`) whose center position is driven by a `--focus-x` custom property
(with an `@property` declaration so it interpolates smoothly where supported, and
degrades to an instant snap everywhere else — never breaks). An `IntersectionObserver`
(threshold 0.55 — the point at which a panel is roughly centered in the viewport) updates
`--focus-x`, the sticky caption's text, and fades in that panel's copy card. Pillar
mapping (left-to-right in the source image): werewolf -> *Community*, rogue -> *Competition*,
valkyrie (the banner's central hero figure) -> *The Clan*, viking -> *Tournaments*, ninja
(final, sharpest figure) -> *Join Shaheen*. On short/narrow viewports (`max-width:720px`
or `max-height:560px` — sticky scrollytelling gets unreliable on mobile browser
chrome-resize quirks) the whole thing falls back to a plain static stack: no sticky pin,
normal document flow, every card visible without needing to scroll-trigger. Inert under
`prefers-reduced-motion`, same posture as every other animation on this site.

**`clan.html` reveal.** The "The Clan" card's plain fade-in became a diagonal
`clip-path` wipe (`.clan-reveal`) with the crest watermark fading in behind the copy —
triggered manually via `requestAnimationFrame` rather than `scroll.js`'s shared
`IntersectionObserver`, since this card is injected into the DOM well after
`DOMContentLoaded` (once `ShaheenAPI.getClan()` resolves) and is also the first thing on
the page, so a scroll trigger was never the right fit for it specifically.

**Deeper Discord/Brawlhalla integration** (all three, owner-selected):
1. *Live Discord widget.* `web/assets/js/config.js` gained `DISCORD_GUILD_ID`; `api.js`'s
   new `wireDiscordWidgets()` fetches Discord's public, unauthenticated
   `guilds/{id}/widget.json` and fills every `[data-discord-widget]` element (header +
   footer on all 8 pages) with an online-count badge — silently stays hidden if the guild
   ID is unset, the widget isn't enabled, or the request fails. **Operational note**: needs
   "Server Widget" enabled under Discord's Server Settings -> Widget, a portal toggle
   outside this repo (same category as prior rounds' `message_content` intent note).
2. *Chat gamification, visual upgrade.* `clan.html`'s Community Activity table (ADR-065)
   became a card list (`web/assets/js/pages/clan.js`): a rank-title badge per member
   (`theme.js`'s new `chatRankBadge()`, styled via new `.rank-hatchling`..`.rank-valhallan`
   classes) plus an XP-to-next-level progress bar reusing the `.legend-bar-track/-fill`
   pattern already built for legend mastery. Same `GET /community/activity` data — no
   backend change, `theme.js`'s new `xpForLevel()` is a small intentional duplicate of
   `services/chat_gamification.py`'s formula (the API returns level/xp/rank_title, not a
   next-level threshold — not worth a new field for one progress bar).
3. *Brawlhalla stats already captured but unexposed* — cheap wins, no new API calls or
   migration: `RankingSnapshot.global_rank` was already stored but never left
   `website_service.py` — now a `PlayerProfile.global_rank` property, surfaced on
   `player.html` as a "Global Rank #N" stat. `LegendSnapshot.damagedealt`/`falls` were
   already stored per-legend but unused — added to `LegendMastery`/`LegendMasteryResponse`,
   shown in each legend's meta line on `player.html`.

Verified: `uv run pytest` (190 passed, including new/extended `test_website_service.py`
coverage for `global_rank`/`damagedealt`/`falls`), `uv run ruff check src tests` / `uv run
mypy src` clean, every touched JS file passed `node --check`. Visual verification used
this sandbox's established headless-Chromium-via-raw-CDP approach (no Playwright/
Puppeteer packages available) — screenshotted all 8 pages at desktop and ~400px mobile
width: confirmed the new crest renders everywhere, the pillar-scroll hero's vignette and
caption genuinely change per section with the copy card fading in at the right scroll
position (this needed two real fixes during verification: the card's alignment moved from
bottom to center so it lands on screen at the same scroll position the
`IntersectionObserver` fires at, and the screenshot script itself needed to wait for
`Page.loadEventFired` — a flat timeout wasn't reliably long enough given this sandbox's
proxied Google Fonts fetch), the mobile fallback drops the sticky pin and stacks cleanly
with no horizontal scroll, `clan.html`'s wipe fires, and `prefers-reduced-motion` still
disables every animation. Data-dependent pages (clan/leaderboard/tournaments) correctly
showed the site's existing "failed to fetch" error state rather than breaking, since this
sandbox's egress proxy can't reach the live Render-hosted API — a sandbox network
limitation, not a defect in this change.

## ADR-067 — `/profile` finished absorbing chat gamification, achievements, and unused API data

Decision: fix `/profile`'s "doesn't show much info" gap (owner report) by finishing what its own
docstring already claimed it was — "the one-look profile card" — rather than adding new data
sources. Read the actual implementation rather than trusting the docs: `build_profile_embed`
showed exactly six fields (Brawlhalla name/level, games/wins/win-rate, member-since, tier/
rating/peak, global rank, region), while `region_rank` was fetched from the Brawlhalla API on
every call and discarded, achievements were fully built (`/achievements`, a 5-entry catalog,
awarded and announced) but never mentioned on `/profile`, chat level/rank (ADR-065) lived only in
the separate `/level` command, and per-legend `damagedealt`/`falls` were already in the API
response `/legends` receives but never displayed (the website's equivalent view already showed
them, per ADR-066). None of this needed a new fetch, a new table, or a migration — every field
was already sitting somewhere in the system, just not assembled.

**`bot/content/profile_embeds.py`**: `build_profile_embed` gained two new parameters —
`chat_activity: ChatActivity | None` and `achievements: list[tuple[Achievement, datetime]]` —
plus a `Region Rank` field next to the existing `Global Rank` (from `ranked.region_rank`, already
on `PlayerRankedResponse`). Chat rank is derived live via
`services.chat_gamification.level_for_xp(chat_activity.xp)`, never read from `ChatActivity`'s
stored `level` column — same staleness rule established in ADR-065/066 (`bot/cogs/engagement.py`'s
`/level`, `website_service.py`'s `get_community_activity`), since that column only updates on a
detected level-up and can drift from `xp` between messages. Achievements show a count plus the
latest up to 3 by name. A new `Full Profile` field links to the website's `player.html?id=...` —
what a Discord embed can't show at all (the rating-history trend chart, full match history) —
using a small `_WEBSITE_BASE_URL` constant (GitHub Pages' default project-site URL for this repo,
no CNAME configured) rather than adding a new required env var just for one footer link;
Discord embed footers are plain text with no clickable links anyway, so the URL lives in a
regular field instead, which does support markdown links. `build_legends_embed` now includes
`damagedealt`/`falls` per Legend row, pulled straight from the `LegendStat` objects `/legends`
already fetches from the live API — no DB round trip needed, unlike the website's version which
reads them from the persisted `LegendSnapshot`.

**`src/services/profile_service.py`**: `ProfileService` now takes the `AsyncSession` directly
(alongside the existing `LinkService`/`BrawlhallaService`) so it can construct
`ChatActivityRepository`/`MemberAchievementRepository` itself, mirroring how every other service
in this codebase holds its own session-scoped repositories. Two new read-only methods,
`get_chat_activity` and `get_achievements`, both thin wrappers around existing repository calls —
the same ones `/level` and `/achievements` already use.

**`bot/cogs/profile.py`**: all four `ProfileService(...)` construction sites updated for the new
constructor signature; `/profile`'s handler fetches chat activity and achievements alongside the
existing stats/ranked calls and passes them through.

Verified: `uv run pytest` (198 passed, including new `tests/test_profile_embeds.py` — region rank
present/absent, chat rank derived live from xp rather than a deliberately-stale stored `level`
column, achievement count/names, the website link, and legend damage/falls), `uv run ruff check
src tests` / `uv run mypy src` clean. No live-Discord test harness exists in this repo (consistent
with every prior round), so the embed builders — pure functions given already-fetched data — are
exercised directly instead, the same pattern used throughout this project's test suite.

## ADR-068 — Rank promotion/demotion announcements, clan-wide Legend meta, head-to-head rivalry stats

Decision: build the first wave of the "gameplay/stat-tracking" roadmap (planned in ADR-067)
— three small features, each reusing data already being collected, no new tables or
migrations.

**Rank promotion/demotion announcements.** `services/snapshot_service.py`'s `snapshot_member`
already diffed consecutive `RankingSnapshot`s for a new career-peak rating; it now also diffs
`tier` the same way. Comparison is family-level only (Gold/Platinum/Diamond/...), not sub-rank
(Platinum III → Platinum II doesn't fire), using a newly-public `services.achievements.tier_index`
(renamed from the module-private `_tier_index` it already had — same "fails open on an
unrecognized tier string, never raises" posture `tier_at_least` already relied on). A new
`TierChange` dataclass (`old_tier`, `new_tier`, `promoted`) on `Announcement` lets
`bot/cogs/clan.py`'s existing `_announce` dispatch handle it as a third branch alongside
achievements and peak-rating milestones — same `#hall-of-fame` channel, same
`render_milestone_card` treatment. Demotions are announced too, not just promotions: hiding them
would read as inconsistent given the brand's own "ranked by results, not excuses" copy voice
(ADR-063), so `build_tier_change_announcement_embed` just gives demotions a calmer, non-exclamation
tone (forest green, "dropped from" vs. promotions' gold "climbed from").

**Clan-wide Legend meta (`/legendmeta`).** `ClanService` gained a `legend_meta` method and a
`LegendMetaEntry` dataclass, following the exact same shape `leaderboard()` already uses: loop
`list_active_for_guild`'s small set of linked members in Python and aggregate their latest
per-legend snapshot (`LegendSnapshotRepository.list_latest_per_legend`, already built for the
website's legend-mastery view) rather than one large SQL aggregate — the member count here is
small enough that this stays simple and fast. A `_MIN_GAMES_FOR_LEGEND_META = 20` threshold
(combined across the whole clan) keeps a single 2-game outlier from dominating the "meta" — this
is a UX/noise decision, not a technical constraint.

**Head-to-head rivalry (`/rivalry <a> <b>`).** Purely internal — `Match`/`MatchParticipant` data
Shaheen already tracks via `/report`/`/match create`, zero Brawlhalla API involvement.
`MatchRepository.head_to_head` joins `MatchParticipant` to itself (aliased) to find confirmed
matches where both members played on opposite sides, returning `(Match, the side member_a played)`
tuples so the caller can tell who won per match by comparing against `Match.winning_side` — no
de-duplication needed since `MatchParticipant`'s `(match_id, shaheen_member_id)` unique constraint
guarantees at most one row per side per match. `MatchService.head_to_head` resolves both Discord
IDs to `ShaheenMember` ids via a new **read-only** `_find_member_id` — deliberately not the
existing `_member_id` (which creates rows), since checking a stat shouldn't have a side effect of
creating a database row for someone who's never interacted with the bot; a rivalry between two
people who've never played is just a zeroed result, not an error.

Files: `services/achievements.py` (public `tier_index`), `services/snapshot_service.py`
(`TierChange`, tier-diff detection), `bot/content/clan_embeds.py`
(`build_tier_change_announcement_embed`, `build_legend_meta_embed`), `bot/cogs/clan.py` (`_announce`
branch, `/legendmeta`), `services/clan_service.py` (`LegendMetaEntry`, `legend_meta`),
`database/repositories/match_repository.py` (`head_to_head`), `services/match_service.py`
(`RivalryResult`, `head_to_head`, `_find_member_id`), `bot/content/competition_embeds.py`
(`build_rivalry_embed`), `bot/cogs/competition.py` (`/rivalry`).

Verified: `uv run pytest` (217 passed — 19 new: tier promotion/demotion/no-change/first-snapshot
detection, `tier_index` ordering, `legend_meta` aggregation and its games threshold, `head_to_head`
tallying both directions/ignoring unconfirmed matches/ignoring third-party matches/zeroing for
never-played pairs, plus embed-construction tests for all three new builders), `uv run ruff check
src tests` / `uv run mypy src` clean.

## ADR-069 — A real manual-verification gate, and a permission-drift self-heal fix

Reported bug: `#general`/`#pakistan-chat` were visible even though the server's `@everyone` is
meant to hide every channel until a member is manually approved. Investigation found two
distinct, real problems, not one — both fixed here.

**The bot had zero concept of a verification gate.** `CategorySpec.restricted` only ever existed
for 3 staff-only categories (SHAHEEN ARENA, MODERATION, DEVELOPMENT). SHAHEEN HQ and THE NEST
(which hold `#general`/`#pakistan-chat`) were never modeled as gated — `/setup` built **no
overwrite at all** for them, so it couldn't be the source of the bypass, but it also wasn't
enforcing the intended gate. A new `CategorySpec.gated` field (`bot/constants.py`) mirrors
`restricted` exactly, inverted: hidden from `@everyone` **and** the auto-assigned-on-join Guest
role (ADR-065), visible to a new `VERIFIED_ROLES` constant (every rank role except Guest —
Leader/Moderator/Elite/Shaheen/Trial/Ally). `_category_overwrites` (`setup_service.py`) branches
on `restricted` vs. `gated` — the two are mutually exclusive by construction, no spec sets both.
`gated=True` on THE NEST, BRAWLHALLA, and VOICE. **SHAHEEN HQ stays deliberately ungated** — a
brand-new Guest needs somewhere to read `#welcome`/`#rules`/`#roles` before staff can verify them;
gating the onboarding category itself would strand new members with nothing to look at.

**A real bug that let any such drift persist forever.** `_apply_categories`/`_apply_channels`
only called `.edit(overwrites=...)` when the computed overwrite dict was non-empty (`if
overwrites:` guards). For every channel/category whose spec says "no special overwrite" — which
was every channel outside the 4 previously-special-cased ones — `/setup run` never called
`.edit()` at all, so a manually-added overwrite (e.g. one set directly in Discord's UI) could
never be cleared. This directly contradicted the code's own existing comment ("a manually changed
permission on Discord's side gets corrected back," ADR-060) and is the actual reason the stray
overwrite on `#general`/`#pakistan-chat` never self-healed across any number of `/setup run`s.
Fixed by removing both guards: `.edit(overwrites=...)` is now called unconditionally on every
non-CREATE pass, even with `{}` — `discord.py`'s `edit(overwrites=...)` fully replaces a channel's
overwrite set, so this is what actually wipes a stray overwrite instead of silently leaving it.
Only `/setup run` calls `apply()`; `/setup verify` stays fully read-only (`service.plan()` only),
so this doesn't change `/setup verify`'s non-destructive contract. Note for the live server: this
fixes drift going forward, but the *currently-live* stray overwrite on those two channels won't
clear until `/setup run` is actually re-run against the real guild.

**Manual approval (`/verify <member>`).** Mirrors the *existing* Guest→Trial Shaheen promotion
`LinkCog._maybe_promote` already does on `/link` (`bot/cogs/link.py`) — same idiom (check for any
rank role above Guest already held, resolve roles by name via `discord.utils.get`, remove Guest,
add the target role), opposite trigger (staff command vs. an automatic Brawlhalla-link side
effect). New in `bot/cogs/moderation.py` — staff commands already live here, all under
`require_staff_authorized()` — promoting to Ally ("friends of the clan" per `embeds.py`'s
`build_roles_embed`, already the correct "verified, not yet a clan member" tier — no wording
changes needed). Not destructive, no `ConfirmView` (same posture as `/warn`); idempotent — running
it on an already-ranked member replies "already verified" instead of erroring; logs to `#mod-log`
via the cog's existing `_log()` helper; best-effort DM to the member.

Files: `bot/constants.py` (`CategorySpec.gated`, `VERIFIED_ROLES`, `gated=True` on THE
NEST/BRAWLHALLA/VOICE), `services/setup_service.py` (`_category_overwrites` gated branch, both
guard removals), `bot/cogs/moderation.py` (`/verify`), `bot/content/moderation_embeds.py`
(`build_verify_success_embed`, `build_already_verified_embed`, `build_verify_dm_embed`),
`docs/PERMISSIONS.md`/`docs/DISCORD_SPEC.md`/`docs/COMMANDS.md`.

Verified: `uv run pytest` (225 passed — new: `_category_overwrites` for gated vs. restricted vs.
neither, a regression test asserting `_apply_categories`/`_apply_channels` call `.edit()` even
with an empty overwrite dict, plus embed-construction tests for the three new `/verify` builders),
`uv run ruff check src tests` / `uv run mypy src` clean.

## ADR-070 — Weekly recap + MVP of the Week, suggestions inbox, member spotlight

Decision: build the "Part C" community-engagement roadmap items flagged small/high-visibility in
ADR-067's plan — weekly recap, MVP of the Week (sharing the recap's own query), `/suggest`, and
`/spotlight`.

**Weekly digest + MVP of the Week.** The recap needed three numbers per week: top rating gains,
top chatters, and matches played. Two of those were free — `RankingSnapshot` and `Match` are
already durable, timestamped history, so `RankingSnapshotRepository.list_since`/
`MatchRepository.count_confirmed_since` just window a query that already existed in a different
shape (`list_recent`/`head_to_head`'s CONFIRMED filter). Chat XP wasn't: `ChatActivity.xp` is a
single cumulative running total with no history, so "most active this week" had no signal to read
without adding state. Rather than a new time-series table, `ChatActivity` gained one more
column — `weekly_xp`, incremented alongside `xp` in `ChatActivityRepository.record_message` — that
the digest job zeroes (`reset_weekly`) right after reading it each week; same "stored counter,
periodically reset" shape used nowhere else in this codebase yet, but simpler than either a new
table or losing the all-time `/chatboard` ranking by repurposing `xp` itself. `services/
digest_service.py`'s `WeeklyDigestService.build_and_rotate` assembles `RatingGain`/`TopChatter`
dataclasses (raw `discord_id` + numbers — Discord display-name resolution stays in `ClanCog`,
same "service returns data, cog resolves live Discord state" split `/leaderboard` already uses)
and picks an MVP: biggest rating gain, falling back to the top chatter in a ranked-quiet week, and
`None` (no role change, no false MVP) if the whole week was quiet on both fronts.

`ClanCog` gained a second `tasks.loop`, alongside the existing snapshot loop, but shaped
differently on purpose: `tasks.loop(hours=24*7)` would drift against the calendar depending on
whenever the bot last happened to restart, so instead it's a **daily** loop fixed to a UTC
time-of-day that no-ops on every weekday but Sunday — the same total behavior, without the drift.
On the Sunday it fires, it posts the recap to `#announcements` and, if an MVP was picked, rotates
a new 🌟 MVP of the Week role: a purely cosmetic `RoleSpec` (`ROLE_MVP`, no permissions, not part
of `VERIFIED_ROLES` or the rank ladder) that `/setup run` creates/repairs like any other role,
removed from whoever held it and added to the new winner in the same tick.

**`/suggest <text>`.** Posts anonymously (the embed builder deliberately takes no author
parameter — nothing to leak) to a new `#suggestions` channel in SHAHEEN HQ, with 👍/👎 reactions
added automatically. Placed in SHAHEEN HQ rather than THE NEST specifically so it stays usable by
an unverified Guest (ADR-069's gate hides THE NEST/BRAWLHALLA/VOICE, not SHAHEEN HQ) — a new
member's very first idea for the clan shouldn't have to wait on `/verify`. No permission check,
same "any member" posture as `/level`; no new table, the message itself with its two reactions is
the entire feature.

**`/spotlight <user> <note>`.** A staff-only manual callout posted to `#announcements`
(`require_staff_authorized()`, same check `/verify`/moderation commands use) — no new data model,
purely a formatted embed with the note and the staff member's name in the footer.

Files: `database/models/chat_activity.py` (`weekly_xp`), `alembic/versions/0006_weekly_digest.py`,
`database/repositories/chat_activity_repository.py` (`list_top_weekly`, `reset_weekly`, `weekly_xp`
increment), `database/repositories/ranking_snapshot_repository.py` (`list_since`), `database/
repositories/match_repository.py` (`count_confirmed_since`), `services/digest_service.py` (new),
`bot/content/clan_embeds.py` (`build_weekly_digest_embed`, `build_mvp_announcement_embed`,
`build_spotlight_embed`), `bot/content/engagement_embeds.py` (`build_suggestion_embed`,
`build_suggestion_confirmation_embed`), `bot/content/channel_intros.py`
(`build_suggestions_intro_embed`), `bot/constants.py` (`ROLE_MVP`, `channel:suggestions`),
`bot/cogs/clan.py` (weekly digest loop, `/spotlight`), `bot/cogs/engagement.py` (`/suggest`),
`bot/cogs/setup.py` (`channel:suggestions` launch content), `docs/COMMANDS.md`/
`docs/DISCORD_SPEC.md`/`docs/PERMISSIONS.md`.

Verified: `uv run pytest` (243 passed — 18 new: rating-gain windowing/sorting/skip-on-no-change,
weekly-XP ranking vs. all-time XP, confirmed-match counting, MVP priority/fallback/quiet-week-none,
weekly-XP reset-after-read, plus embed-construction tests for all five new builders), `uv run ruff
check src tests` / `uv run mypy src` clean, a scratch-database `alembic upgrade head` confirming
migration 0006 applies cleanly on top of 0001-0005.

## ADR-071 — Full clan roster page + achievement gallery (Part D)

Decision: build the two website-side companions named in ADR-067's Part D roadmap — a full
roster page (every actively-linked member, not `/leaderboard`'s top-N) and an achievement
gallery (clan-wide completion stats, including achievements nobody's earned yet). Neither had
backend support: `get_leaderboard` caps at 100 and silently drops any unranked member, and no
method anywhere queried achievements clan-wide (`MemberAchievementRepository` is strictly
per-member; the catalog reader `AchievementRepository` wasn't even wired into `WebsiteService`).

**Roster.** New `WebsiteService.get_roster`/`RosterEntry` — the same `list_active_for_guild`
loop `get_leaderboard`/`get_community_activity` already use, but keeping every member
(`snapshot=None` instead of dropping them) and taking no `limit`, since "everyone" is the whole
point. `RosterEntry` also carries `joined_at` straight off `ShaheenMember` — already fetched by
`list_active_for_guild`, just unused until now. `GET /roster` (`src/api/routers/roster.py`)
mirrors `leaderboard.py` exactly, minus the `limit` query param.

**Achievement gallery.** New `WebsiteService.get_achievement_gallery`/`AchievementGalleryEntry` —
same "loop the small set of linked members in Python" shape `ClanService.legend_meta` already
uses rather than a SQL aggregate. Starts from the full catalog (`AchievementRepository.list_all`,
newly added to `WebsiteService.__init__`) so a zero-holder achievement still gets an entry, then
tallies `MemberAchievementRepository.list_earned_keys` per linked member into a holder count.
`completion_pct` is a computed property, not a stored field — `LegendMetaEntry.win_rate` is the
direct precedent. Catalog order, not sorted by rarity: a gallery reads as a fixed checklist, not
a leaderboard. `GET /achievements` (`src/api/routers/achievements.py`) mirrors `clan.py`'s
zero-param shape.

Both stay inside ADR-040's identity boundary for free — `list_active_for_guild`'s `discord_id` is
discarded (`_discord_id`) exactly like every other method in this service.

**Frontend.** `web/roster.html`/`web/achievements.html` clone `web/leaderboard.html`'s shell
verbatim (this repo has no templating system — every page hand-repeats header/ticker/banner/
footer/script-tags on purpose, so matching that is the correct move, not a shortcut).
`pages/roster.js` is `pages/leaderboard.js`'s table almost unchanged, plus a Member Since column
and `—` instead of a dropped row for unranked members. `pages/achievements.js` renders a
`.achievement-grid` of cards — the existing gold `.badge-icon` circle plus name/description/
progress-bar (`.legend-bar-track`/`.legend-bar-fill`, reused from the Community Activity
progress bars, not reinvented) — with one small new CSS block (`.achievement-grid`/
`.achievement-card`, only existing custom properties, no new tokens) since nothing existing was
quite this shape. A zero-holder achievement gets a dimmed/greyscale card so the gallery reads as
"earned vs. not" at a glance. Both new links were added to every existing page's identical
copy-pasted nav block (`web/*.html`, one line added twice each) — same as every prior page
addition to this site.

Files: `services/website_service.py` (`RosterEntry`, `get_roster`, `AchievementGalleryEntry`,
`get_achievement_gallery`), `api/schemas.py` (`RosterEntryResponse`,
`AchievementGalleryEntryResponse`), `api/routers/roster.py`, `api/routers/achievements.py` (new,
registered in `api/app.py`), `web/roster.html`, `web/achievements.html`,
`web/assets/js/pages/roster.js`, `web/assets/js/pages/achievements.js` (new),
`web/assets/js/api.js` (`getRoster`, `getAchievements`), `web/assets/css/style.css`
(`.achievement-grid`/`.achievement-card`), every existing `web/*.html`'s nav block.

Verified: `uv run pytest` (254 passed — 11 new: roster includes unranked members/orders ranked
members first/carries member_since/empty-guild case, achievement gallery includes zero-holder
achievements/counts holders and completion_pct/handles zero-members without a division-by-zero,
plus `TestClient` integration tests for both new routes including the ADR-040 identity-boundary
check), `uv run ruff check src tests` / `uv run mypy src` clean. Both pages verified against a
local `uv run uvicorn` + seeded scratch database via headless Chromium (desktop and ~400px
mobile widths): roster correctly shows a `—` row for an unranked member instead of omitting it;
the achievement gallery correctly dims zero-holder achievements and shows accurate completion
percentages; nav links resolve correctly from every page.

## ADR-072 — Channels now carry an explicit copy of their category's gate/restriction

Reported: after ADR-069's gate shipped and `/setup run` was re-run on the live server, newly
created channels still showed no permission restriction. ADR-069's design relied entirely on
Discord's own category→channel permission cascade: `_category_overwrites` set the deny/allow on
the *category* (THE NEST/BRAWLHALLA/VOICE/the 3 `restricted` categories), while every child
channel was created or reconciled with an *empty* overwrite dict, trusting Discord to apply the
category's overwrite to any channel with no overwrites of its own. That cascade is real — but
Discord's own client never actually relies on it silently: when a channel is created inside a
category through the Discord app, the client explicitly **copies** the category's current
overwrites onto the new channel ("Permissions Synced"), rather than leaving it with an empty
overwrite list and trusting the cascade. Given a live report that channels weren't ending up
restricted, the safer, verifiable fix is to do the same thing Discord's own client does —
stop relying on cross-level inheritance holding for every code path, and copy the overwrite down
explicitly ourselves.

`_channel_overwrites` (`setup_service.py`) now takes the parent `CategorySpec` alongside the
channel's own spec: it starts from `_category_overwrites(parent, role_by_key)` — copying each
`PermissionOverwrite` via `.pair()`/`.from_pair()` so the channel gets independent objects, not
shared references that a later `staff_only_send` edit could corrupt — then layers `staff_only_send`
on top via `.update()` (which sets one flag without clobbering ones already copied from the
parent, e.g. a channel that's both gated *and* staff-only-send keeps the parent's `view_channel`
grants while adding its own `send_messages` restriction). `_apply_channels` builds a
`category_spec_by_key` lookup from `bot.constants.CATEGORIES` to resolve each channel's parent
spec by its `category_logical_key`. Every channel in THE NEST/BRAWLHALLA/VOICE (and the 3
`restricted` categories) now gets its own explicit copy of the gate on every `/setup run` —
including at creation time for a brand-new channel, not just reconciled after the fact.

Files: `services/setup_service.py` (`_channel_overwrites` signature + body, `_apply_channels`'
`category_spec_by_key` lookup).

Verified: `uv run pytest` (260 passed — 6 new: a channel copies a gated/restricted parent's
overwrite, no parent + not staff_only_send stays empty (regression, matches prior behavior),
staff_only_send layers over a gated parent without losing its view_channel grants, the copies are
independent objects rather than shared references, and an end-to-end test using the real
`channel:general`/`category:the_nest` specs from `bot/constants.py` confirming `.edit()` is
called with the correct gate applied), `uv run ruff check src tests` / `uv run mypy src` clean.
Note: this — like ADR-069's own fix — only takes effect once `/setup run` is actually re-run
against the live server; the currently-live channels won't self-correct until then.

## ADR-073 — Site-wide autoplay background audio (clan anthem)

Requested: play the clan's anthem (`assets/audio/anthem.mp3`, a 60s Urdu-language track ending
in the brand's own "HIGHER TOGETHER" line) automatically on every page of the website.

Constraint that shapes the whole design: no current browser (Chrome, Firefox, Safari) allows
unconditional autoplay-with-sound on page load without prior engagement from the visitor on
that origin — this is a deliberate, unbypassable browser policy, not a bug to chase later. The
only honest implementation is the pattern every site with background audio actually uses: call
`audio.play()` immediately, and if the returned promise rejects (autoplay blocked), fall back
to starting playback on the visitor's very first `click`/`keydown`/`touchstart` anywhere on the
page. `assets/js/audio.js` implements exactly that, plus a persistent mute toggle and playback
position, and nothing more.

The site is 10 hand-authored static pages with no templating or shared shell, so the module is
deliberately self-contained — no dependency on `config.js`/`api.js` — and wired in with one
identical `<script src="assets/js/audio.js"></script>` tag added as the *first* script on every
page, the same mechanical one-line-per-file pattern used for prior site-wide additions (nav
links, etc.).

This feature introduces two firsts for the site, both used minimally and defensively:

- **First `localStorage` usage.** Two keys: `shaheen-audio-muted` (a visitor's explicit
  mute/unmute choice, so muting on one page stays muted across the next) and
  `shaheen-audio-position` (a throttled, `timeupdate`/`pagehide`-driven save of playback
  position, so clicking to a new page resumes roughly where the anthem left off instead of
  visibly restarting from 0:00 every navigation — this is a 10-page static site, not an SPA, so
  audio genuinely tears down and rebuilds on every page load). Every read/write is wrapped in
  try/catch: private browsing or a locked-down context can throw on `localStorage` access, and
  the feature must degrade to "just doesn't persist" rather than breaking the page.
- **First `position: fixed` UI element.** The mute/unmute toggle (`.audio-toggle`,
  `web/assets/css/style.css`) is a small circular button pinned bottom-left, always reachable
  regardless of scroll position. It reuses the existing `--card-bg`/`--card-border` treatment
  and the same green-glow family as `.btn-primary`/`.cta-pulse`, with its own `.is-pending`
  pulse (gold, not green) to signal "autoplay was blocked — tap anywhere to start" whenever the
  fallback path is active, and an `.is-muted` state that dims it to `--grey`. A
  `@media (max-width: 640px)` rule shrinks and repositions it slightly, matching the site's one
  existing narrow-viewport breakpoint.

Icon is an inline SVG (speaker + sound-wave arcs, with a muted/slash variant), not an emoji
glyph, so it renders crisply at 1x and stays colorable with `currentColor` across every OS
without emoji-rendering variance.

Files: `web/assets/audio/anthem.mp3` (new), `web/assets/js/audio.js` (new),
`web/assets/css/style.css` (`.audio-toggle` block + `audioTogglePending` keyframes + one mobile
rule), every `web/*.html` file (one new `<script>` tag each).

Verified: headless-Chromium pass confirming the toggle renders correctly and matches the site's
visual language at desktop and ~400px widths, that both autoplay outcomes (allowed and blocked)
leave the button in the correct state including the first-interaction fallback actually starting
playback, and that the mute preference and resume position both survive a simulated page
navigation. No Python changes in this round — `ruff`/`mypy`/`pytest` untouched.

## ADR-074 — "Spirit of Shaheen" animated section on clan.html

Requested: a branded infographic (Iqbal's Shaheen poetry, a "What We Stand For" values list,
"Shaheen Is More Than a Name", and a closing "Fly High. Fight Hard. Leave a Legacy." tagline)
added to the website animated in the homepage's style, plus the same content split into a text
block and a separate image for posting in Discord. None of this copy existed anywhere in the
repo before this round — `docs/BRAND.md` and `src/core/brand.py` carry only the base
motto/tagline, not this supplementary content — so it's new copy, not a reuse of existing
strings. `core/brand.py`'s `MOTTO`/`TAGLINE` are untouched; the Discord side is two deliverable
files (a text block + `web/assets/img/shaheen-lockup.png`), not bot/cog/embed code — the user
explicitly scoped that half to "deliverable files only."

`web/clan.html` (the "About the Clan" page) was chosen over the homepage or a new page: it
currently has zero static philosophy/values content — everything there is API-injected (motto
card, member count, community activity, explore links) — so this is a natural, non-duplicative
home for identity/brand content, and it can render immediately rather than waiting on the API
fetch that gates the rest of the page (which can take "up to a minute" on first load).

Four new sections were inserted in `<main>` **before** the existing `#clan-content` div: "The
Spirit of Shaheen" (intro + two Iqbal couplets + closing line), "What We Stand For" (5 value
tiles), "Shaheen Is More Than a Name" (intro + 6 feature tiles), and a closing tagline banner.
Each reuses existing components — `.wrap.reveal`, `.divider`, `.card`, `.stat-grid`/`.stat`,
`[lang="ur"]` (Nastaliq + RTL is already global) — rather than inventing new ones; new CSS is
limited to genuine gaps: `.spirit-intro` (centered paragraph), `.spirit-couplets`/`.couplet` (a
2-column Urdu/English quote layout with an auto-collapsing `auto-fit minmax(260px,1fr)` grid),
`.stat-desc` (an optional third description line under `.stat`'s existing value+label — reused
by the values grid, useful for any future `.stat` tile that needs one), and `.spirit-banner` (a
gold radial-glow banner inspired by the homepage hero's `.hero-glow` technique, self-contained
via a `::after` pseudo-element instead of `.hero-glow`'s separate sibling-div structure). The
6-tile feature grid needed zero new CSS — it's an exact reuse of the pattern this same page
already uses for its own "Explore" grid, just non-linked.

Animation is deliberately not uniform: the first three sections use plain `.reveal` (fade +
slide) — dignified rather than flashy, appropriate for poetry/values copy per BRAND.md's
"avoid... childish copy... cluttered" guidance. The closing tagline banner alone uses
`.clan-reveal` (this page's existing diagonal-wipe + crest-watermark treatment, until now used
only on the API-injected motto card) — reserving the more elaborate animation for one true "hero
moment" rather than overusing it across every section.

This surfaced and fixed a real gap: `clan.html` never loaded `assets/js/scroll.js`. Its only
prior `.clan-reveal` usage (the motto card) is injected by `pages/clan.js` *after* an async API
fetch resolves, well after `DOMContentLoaded` — so `clan.js` has always hand-rolled its own
reveal trigger (a manual double-`requestAnimationFrame` then `classList.add("in-view")`) instead
of relying on scroll.js's shared `IntersectionObserver`, which only observes elements present in
the DOM at `DOMContentLoaded`. The four new sections above ARE static markup present at that
point, so they need scroll.js's observer to fire their entrances. Added the script tag,
positioned to match `index.html`'s load order (`spotlight.js` → `scroll.js` → page script) —
zero JS code changes needed. No conflict with the existing motto card: scroll.js's
`querySelectorAll(".reveal, .clan-reveal")` runs once at `DOMContentLoaded`, before clan.js's
fetch has injected anything, so the two reveal mechanisms never observe the same element — the
new sections are handled by scroll.js, the motto card keeps animating exactly as it did before.

Files: `web/clan.html` (4 new sections + one new `<script>` tag), `web/assets/css/style.css`
(`.spirit-intro`, `.spirit-couplets`/`.couplet`, `.stat-desc`, `.spirit-banner`).

Verified: headless-Chromium pass — each new section's entrance animation fires once on scroll
(three plain fades, one diagonal wipe), Urdu couplets and the banner's Urdu line render in
Nastaliq/RTL correctly, the 5-tile and 6-tile grids sit as single rows on desktop and wrap
cleanly at ~400px, and — the one real regression risk — the existing API-injected motto card
still animates exactly once via its own manual trigger with `scroll.js` now also loaded on the
page, with member count / community activity / the existing Explore grid all still rendering
unaffected below the new sections. No Python changes — `ruff`/`mypy`/`pytest` untouched.

## ADR-075 — "Spirit of Shaheen" rebuilt as fade-scrollytelling, art cropped from the reference poster

Requested: replace ADR-074's four static reveal-on-scroll sections with proper scrollytelling
("scroll + storytelling") in the homepage's animation family, styled after an uploaded reference
poster. Two explicit steering decisions when asked to clarify: (1) crop the actual uploaded
poster image into web assets — not the existing `hero-characters.jpg`/`banner.jpg` site imagery,
and not freshly generated art — with a fade/crossfade scroll mechanic, explicitly not the
homepage's `pillar-scroll.js` pin-and-pan mechanic; (2) both the "What We Stand For" and
"Shaheen Is More Than a Name" sections get horizontal-scroll-snap carousel treatment, not just
one.

**Image pipeline.** The poster (726×2167px portrait) was cropped into four assets with Pillow —
`Image.LANCZOS` upscale + `UnsharpMask` to counter the source being much narrower than a
purpose-built asset like `hero-characters.jpg` (2172×724): `spirit-hero.{jpg,webp}` (the eagle
cliff/mountain scene), `spirit-pillars-strip.jpg` (all 5 value statues, one shared strip —
mirrors `pillar-scroll.js`'s own "one source image, shift it" philosophy rather than 5 separate
low-res crops), `more-than-name.jpg` (the cityscape band), `spirit-banner-bg.jpg` (the closing
floating-islands scene). Every crop was deliberately chosen to **exclude the poster's own baked
headings/paragraphs** — an early pass reused crops that still carried the poster's own text
(e.g. "THE SPIRIT OF SHAHEEN"), and rendering confirmed it read as an unintended duplicate/ghost
of the real foreground heading rather than atmosphere, even under the vignette's darkening; the
final crops are pure scenery, letting the site's own HTML/CSS text be the only text layer.

**Section A — `assets/js/spirit-scroll.js`, new, sibling to `pillar-scroll.js`.** Same
sticky-stage/panel-column skeleton (`.spirit-hero` > `.spirit-stage` > `.spirit-visual` [sticky,
`height:100vh`] + `.spirit-panels`) and the same `IntersectionObserver({threshold: 0.55})`
shape, but the backdrop stays one static crop — no `--focus-x` pan. Instead, one
`.spirit-panel-card` is ever `opacity:1` at a time across the 4 panels (intro, two Iqbal
couplets, closing line): the observer callback removes `.in-view` from every sibling before
adding it to the entering card, which is what makes it read as a genuine crossfade in *both*
scroll directions — `pillar-scroll.js` by contrast never un-marks a panel once revealed, since
its effect (panning) only ever needs to move forward. Same mobile/short-viewport
(`@media (max-width: 720px), (max-height: 560px)`) and `prefers-reduced-motion` fallback posture
as `.pillar-hero`: no sticky pin, cards permanently visible.

**Sections B & C — `assets/js/carousel.js` + `.carousel*` CSS, new: the site's first
horizontal-scroll-snap pattern.** No such pattern existed anywhere before (`.table-scroll`/
`.bracket` are bare `overflow-x:auto`, no snap, no JS). Native `scroll-snap-type: x mandatory`
does all the real scrolling; `carousel.js` only adds optional prev/next buttons for
keyboard/no-trackpad users — shipped `hidden` in markup, unhidden only once JS actually wires
them, same posture as the header's `.discord-widget`, so a JS failure never leaves a dead button
behind. Cards reuse `.stat`'s existing card chrome (`class="carousel-card stat"`) rather than a
new tile style. Section B's 5 cards each show a `.pillar-card-art` slice of
`spirit-pillars-strip.jpg` via `background-position` (one image, five uses); since that art
already carries its own icon glyph per pillar, the redundant emoji icon was dropped from those
cards. Section C's `.carousel-backdrop` uses `more-than-name.jpg` as a shared background behind
all 6 feature cards — its overlay gradient was strengthened (to `0.72`/`0.88` alpha) after an
initial pass showed the backdrop's own city-light detail reducing card-text contrast once real
content sat on top of it.

**Section D** — kept `.card.clan-reveal.spirit-banner` exactly as ADR-074 shipped it (still the
page's one "hero moment" wipe). Added a low-opacity (`0.32`) `spirit-banner-bg.jpg` layer via a
plain `<div>` rather than reusing the `::before` slot, since `.clan-reveal::before` already owns
that slot for its crest watermark — both effects now show together.

**Removed:** the old `#clan-spirit` markup and its `.spirit-couplets` grid CSS (ADR-074).
**Kept and reused as-is:** `.spirit-intro`, `.couplet`/`.couplet-en`/`cite`, `.stat-desc`, and
the whole `.spirit-banner*` block. `core/brand.py` and the Discord bot remain untouched — this
is a `web/`-only change.

Files: `web/clan.html`, `web/assets/css/style.css`, `web/assets/js/spirit-scroll.js` (new),
`web/assets/js/carousel.js` (new), `web/assets/img/spirit-hero.{jpg,webp}`,
`spirit-pillars-strip.jpg`, `more-than-name.jpg`, `spirit-banner-bg.jpg` (all new, cropped from
the uploaded poster — no raw poster file committed).

Verified: headless-Chromium pass — exactly one `.spirit-panel-card` is `opacity:1` at any scroll
position, confirmed scrolling both down and back up (re-entering an earlier panel correctly
re-lights it); the mobile/short-viewport and `prefers-reduced-motion` fallbacks render a static,
fully-visible, non-sticky stack; both carousels scroll/snap correctly, their prev/next buttons
unhide once wired and correctly disable at each end; all 4 new images load with no broken-image
icons at desktop and ~400px widths; `.spirit-banner`'s new background doesn't hurt text
legibility; the untouched `#clan-content` block below (API motto card, stats, activity, Explore
grid) still renders and animates correctly, no regression to ADR-074's `scroll.js` wiring. No
Python changes — `ruff`/`mypy`/`pytest` untouched.

## ADR-076 — Fix blurred poster crops, replace the carousel with scroll-jacked horizontal pan

Requested: corrective feedback on ADR-075's just-shipped work, via two annotated screenshots.
(1) `spirit-hero.jpg`'s background showed visible blur/haloing behind the second Iqbal couplet.
(2) The manual/touch carousel shipped for "What We Stand For" and "Shaheen Is More Than a Name"
was the wrong interaction model — normal vertical page-scrolling should drive horizontal panning
across a single wide image, with content fading in as a card block (not a swipe/click carousel).
"The Spirit of Shaheen" keeps its existing single-image + vertical-scroll-driven fade — that part
already matched what was asked; only its image quality needed fixing.

**Blur root cause**: `spirit-hero.jpg` was cropped from a tiny ~348×250px region of the 726px-
wide source poster, then upscaled 4.5x with `UnsharpMask(radius=2, percent=60, threshold=3)` on
top — that combination (small native crop blown way up, then sharpened) is exactly what produces
visible smearing and halo/ringing. Fix: crop wider/taller native regions (less zoomed-in framing)
so the needed upscale drops to ~2.3–3.7x, and drop the unsharp pass entirely — a plain `LANCZOS`
resize read noticeably cleaner once actually rendered on the page than the same crop with heavy
sharpening baked in, confirming the sharpening (not just the upscale ratio) was compounding the
"distorted" look. Applied to all four poster-derived assets (`spirit-hero.jpg`/`.webp`,
`spirit-pillars-strip.jpg`, `more-than-name.jpg`, `spirit-banner-bg.jpg`) for consistency, since
the latter two are being promoted from small thumbnails/card-backdrops into full 100vh sticky
hero backgrounds by this same round and need the same headroom. Every crop still deliberately
excludes the poster's own baked headings/labels (ADR-075's original lesson) — confirmed this
round while widening `spirit-pillars-strip.jpg`'s candidate crops, several of which reintroduced
baked "WHAT WE STAND FOR" heading text or per-pillar name labels that would have duplicated the
site's own `.values-panel-card` text once that backdrop became a full-bleed pan target instead of
a 150px thumbnail.

**New mechanism**: `assets/js/scroll-pan.js` (new) generalizes `spirit-scroll.js`'s proven
sticky-stage/panel-column crossfade — one `IntersectionObserver({threshold: 0.55})` per stage,
mutual exclusion so only one `[data-scroll-card]` is ever `opacity: 1` within that stage's panels
at a time, meaning the outgoing card block fades to 0 at the same moment the incoming one fades
to 1, a true crossfade in both scroll directions — and adds one optional, data-attribute-gated
behavior: a panel carrying `data-pan-x` writes that value to a `--pan-x` custom property scoped
to *its own stage's* sticky visual element, read by that section's CSS to pan a background image
horizontally via `background-position`. `spirit-scroll.js` is deleted; Section A migrates onto
the new shared module too (adding `data-scroll-stage`/`-visual`/`-panel`/`-card` attributes,
no `data-pan-x`, so its behavior is unchanged) rather than leaving three near-identical sticky-
crossfade scripts on one page. Unlike the homepage's `--focus-x` (global on `<html>`, fine since
`pillar-scroll.js` runs exactly one stage), `--pan-x` is deliberately set per-stage-element: this
page runs three independent scrollytelling stages at once, and global state would make "What We
Stand For" and "Shaheen Is More Than a Name" fight over the same property. Registered via
`@property --pan-x` next to the existing `--focus-x`, so the pan transitions smoothly.

**Section B** ("What We Stand For") reuses the exact panning technique from the retired
`.pillar-card-art` (`background-size: 500% 100%`, one image, `background-position` stepped in
25% increments) — now driving `.values-visual`'s full sticky backdrop instead of a 150px card
thumbnail, in 5 discrete steps matching the strip's 5 statues. **Section C** ("Shaheen Is More
Than a Name") pans the same way but *continuously*, not in 6 hard stops: `more-than-name.jpg` is
one unbroken cityscape panorama, not six pictorially distinct positions, so an overscanned
`background-size: 145% 100%` and a slower transition read as a smooth pan rather than a jump-cut
— judged more honest to the source than forcing 6 fake "stops" out of one continuous scene. Both
share `.spirit-hero`'s exact mobile/short-viewport fallback (`@media (max-width: 720px),
(max-height: 560px)`: disable the sticky pin, static ~42vh backdrop, cards always visible) and
`prefers-reduced-motion` fallback — trading away the retired carousel's native-touch swipe on
mobile for the same single-markup-plus-fallback simplicity already used everywhere else on this
page, rather than maintaining two parallel markups per breakpoint.

**Removed**: `assets/js/carousel.js`, `assets/js/spirit-scroll.js`, and the `.carousel*`/
`.pillar-card-art`/`.carousel-backdrop` CSS block from ADR-075 — the carousel was the wrong
interaction model, not a bug to patch.

Files: `web/clan.html`, `web/assets/css/style.css`, `web/assets/js/scroll-pan.js` (new),
`web/assets/js/spirit-scroll.js` + `web/assets/js/carousel.js` (deleted), all four
`web/assets/img/spirit-*.jpg`/`more-than-name.jpg` (+webp) assets regenerated.

Verified: headless-Chromium pass — regenerated images show no visible upscale smear or
sharpening halo at actual render size; scrolling down through sections A→B→C shows exactly one
`.in-view` card per stage at a time, with `--pan-x` advancing 0→25→50→75→100 through section B
and 0→0→20→40→60→80→100 through section C as each panel centers; scrolling back **up** through
all three confirms bidirectional re-crossfade and `--pan-x` correctly restoring for the
re-entered panel (the main regression risk of generalizing the observer); ~400px width and a
short-viewport-height window both fall back to a static, fully-visible stacked layout with no
sticky pin; `prefers-reduced-motion: reduce` renders everything statically; no broken images; the
closing tagline banner and the API-driven `#clan-content` block below still render and animate
correctly. No Python changes — `ruff`/`mypy`/`pytest` untouched.

## ADR-077 — clan.html's story replaced wholesale with a delivered scrollytelling prototype

Requested: a complete, self-contained prototype (`shaheen_scrollytelling_v2.zip` — `index.html` +
five purpose-made 1920×1080 scene images) that does what ADR-074/075/076 were reaching for
properly: one continuous scroll-jacked story — hero title → Iqbal's poetry → a horizontally
sweeping pillar-values row → "more than a name" → closing legacy tagline — driven by a single
sticky stage and a continuous scroll-position formula, not discrete `IntersectionObserver` stops.
This **replaces** ADR-074/075/076's three-section approach entirely (`.spirit-hero`/
`.values-hero`/`.more-hero`/`.spirit-banner`, `scroll-pan.js`, and the small cropped-poster
images that round kept fighting blur on) — not an iteration on top of it. Two integration
decisions confirmed before implementation: reconcile the prototype's own Inter font and muted
gold/cream palette onto this site's existing Bebas Neue/Space Grotesk/Sora + `--gold`/`--cream`/
`--void` tokens, rather than introducing a second parallel style system; and drop the
prototype's own fake top nav (logo + Home/About/Community/Tournaments/Join) since the site's
real sticky `.site-header` above it is sufficient.

The five scene images are used as delivered (1920×1080, no upscaling needed — the blur problem
from the last two rounds was specific to the 726px source poster this round's assets don't share)
under `web/assets/img/story/`. They deliberately carry some baked scene text as art direction
behind the real DOM content, not a duplication bug like the earlier rounds' poster crops: the
real interactive cards sit on top with their own dark backing, so the baked text reads as
atmosphere rather than a legibility collision.

`web/assets/js/clan-story.js` (new, replaces the deleted `spirit-scroll.js`/`scroll-pan.js`) is
a near-verbatim port of the prototype's engine, selectors renamed to this page's `story-`
prefixed classes (chosen because the prototype's own short class names — `.eyebrow`, `.legacy`,
`.cta`, `.feature` — were fine in a standalone page but too generic for a 1700-line shared
stylesheet). One continuous formula (`scrollY / max → per-scene fractional progress`) drives
everything: which of the five `.story-scene-bg`/`.story-panel` pairs is active, a subtle
background zoom, the two-Iqbal-quote crossfade as an independent sub-beat within the spirit
scene, and the pillar row's `translateX` sweep as a sub-beat within the pillars scene — genuine
continuous panning, not the discrete `--pan-x` steps ADR-076 used.

One real gap found while porting, not present in the standalone prototype: its poetry beat
templated whichever Iqbal couplet was active into a single DOM slot via JS. Since this site's
`prefers-reduced-motion` convention is to never attach a scrollytelling module's scroll listener
at all (matching `pillar-scroll.js`/`scroll.js`), that would have left reduced-motion visitors
with an empty, never-populated verse — silently dropping both Iqbal quotes for anyone who
prefers-reduced-motion. Fixed by writing both couplets statically into the HTML as two stacked
`.story-quote` elements instead of one JS-templated slot; `clan-story.js` crossfades between them
via `opacity` for normal-motion visitors, while the reduced-motion CSS fallback below simply
shows both in static normal flow — the content is now in the DOM regardless of whether JS runs.

No separate mobile/short-viewport static fallback was built this round (unlike ADR-074/075/076's
discrete-panel sections) — this design has exactly one sticky element for the whole page instead
of three stacked independent ones, architecturally simpler and less prone to the compounding
sticky-context quirks that motivated the earlier `@media (max-width: 720px), (max-height: 560px)`
fallback. Verified visually at ~400px instead; flagged as a follow-up if it turns out to jitter
on real devices, rather than pre-built speculatively.

Files: `web/clan.html` (old sections removed, new `.story-stage`/`.story-scroll-area` section
added), `web/assets/css/style.css` (`.spirit-*`/`.values-*`/`.more-*`/`@property --pan-x` removed,
new `.story-*` block added plus its `prefers-reduced-motion` fallback), `web/assets/js/clan-story.js`
(new), `web/assets/js/spirit-scroll.js` + `web/assets/js/scroll-pan.js` (deleted),
`web/assets/img/story/01-hero.jpg` … `05-legacy.jpg` (new, copied from the delivered prototype
as-is), `web/assets/img/spirit-hero.{jpg,webp}`/`spirit-pillars-strip.jpg`/`more-than-name.jpg`/
`spirit-banner-bg.jpg` (deleted — no longer referenced by anything).

Verified: headless-Chromium pass — scrolling the full 650vh steps through all five scenes with
correct background crossfades; the two Iqbal couplets crossfade within the spirit scene; the
pillar row visibly sweeps horizontally as a continuous pan; progress dots and the counter track
the active scene; scrolling back up reverses cleanly; desktop and ~400px widths both hold up;
`prefers-reduced-motion: reduce` renders a static, fully-visible stack with both Iqbal couplets
present and no sticky pin or JS scroll listener attached; no broken images; the untouched
API-driven `#clan-content` block below still renders and animates correctly. No Python changes —
`ruff`/`mypy`/`pytest` untouched.

## ADR-078 — real eagle animation, card-free Pillars, new Legends scene

Requested: three of ADR-077's five story beats fell short of a fuller scrollytelling spec —
Hero/Spirit needed a real animated eagle (perched → taking off → flying) instead of a static
baked bird; Pillars needed to drop its sliding card row entirely ("no cards, boxes or borders")
in favor of one static environment with a moving spotlight; and a "Legends" roster beat (horizontal
scroll-driven character strip, "slide + fade, not individual cards") didn't exist at all — the
Journey scene it replaces was a generic boxed feature-grid card. A second asset delivery
(`shaheen_story_web_1.zip`) provided what ADR-077 didn't have: three transparent eagle-pose
cutouts (`eagle_perched/launch/flying.png`) and five transparent character cutouts
(`legend_mordex/brynn/tezca/nix/jaeyun.png`) — true layered foreground art, not another flattened
scene mockup. The zip's own `hero.png`/`pillars.png`/`legends.png`/`storyboard.png` are browser
screenshots of its own demo (baked-in fake nav, headline, dot indicators) and were treated as
visual reference only, not assets — reusing them as backgrounds would have reintroduced the
exact "one giant flattened image" problem this round moves away from. `01-hero.jpg`…`05-legacy.jpg`
(ADR-077, already reconciled to this site's tokens) stay as the environment layers underneath the
new foreground cutouts.

Requested roster was eight legends (Orion, Artemis, Mordex, Brynn, Tezca, Nix, Jaeyun, Petra);
finished cinematic-style cutout art exists for five. A follow-up reference sheet confirmed all
eight are real Brawlhalla legends worth including eventually, but its own art for them is a flat
"chibi rock-pedestal" icon style that doesn't match the five cinematic cutouts already on hand —
mixing styles would read as an error, not a roster. Per confirmed direction, this round ships
exactly the five with matching art; Orion/Artemis/Petra are a follow-up once art exists in the
same style. No image-generation or true AI-upscaling tool is available in this environment, so
neither the missing three nor any "higher-resolution" regeneration of existing assets was
possible this round — confirmed directly with the user rather than assumed.

**Eagle** (`.story-eagle`, `web/assets/img/story/eagle_{perched,launch,flying}.png`): an
independent foreground layer inside `.story-stage`, not scoped to a single `.story-panel` — it
spans the Hero (scene 0) and Spirit (scene 1) scenes together, crossfading perched → launch →
flight as `clan-story.js`'s overall scroll formula advances through both. This needed a layout
change to avoid colliding with text: both panels' copy was center/right-anchored in the vertical
middle of the frame, exactly where a foreground eagle wants to sit, so both were re-anchored to
the lower frame (`align-items: flex-end`) leaving the eagle the upper two-thirds, left-of-center.

**Pillars** (`.story-pillar-spotlight`, `.story-pillar-captions`): the sliding bordered
`.story-pillar` cards are gone. The background (`03-pillars.jpg`) already shows all five totems
across one mountain range, so a radial-gradient spotlight now sweeps a `--focus` position across
five stops to brighten whichever totem is active, while a plain unboxed caption (index, name,
tagline, one-line description) crossfades in sync — text swaps discretely and stays readable,
the environment is what visibly highlights. All five captions live statically in the DOM (same
"both in the DOM, crossfade via opacity" pattern as the Spirit scene's two quotes) rather than
one JS-`textContent`-swapped slot — the latter would have silently dropped four of the five
captions for `prefers-reduced-motion` visitors, the same class of bug ADR-077 already caught and
fixed once for the Iqbal quotes; no reason to reintroduce it here.

**Legends** (new `.story-legends` scene, replaces the old "Journey" boxed feature-grid card;
`web/assets/img/story/legend_{mordex,brynn,tezca,nix,jaeyun}.png`): a horizontal roster strip
driven by vertical scroll, background reused from `04-journey.jpg` (its "different paths, one
sky" mood fits; the zip's own `legends.png` bakes a *different* set of character renders directly
into its pixels, which would visibly double up against the real cutouts layered on top). All five
cutouts + names + traits are static DOM elements (`.story-legend`); `clan-story.js` only toggles
which is `.active` (full opacity/scale, others dimmed/blurred/scaled down — "slide + fade") and
translates the strip to center the active one, with the step width measured live via
`getBoundingClientRect` rather than hardcoded so it stays correct at the mobile breakpoint's
narrower cards.

**Legacy**: the six feature words (Ranked/Scrims/Tournaments/Achievements/Leaderboards/Community)
moved out of the deleted Journey grid into the Legacy scene as a single plain, unboxed strap-line
above the closing headline — "integrate into the environment rather than cards," per the request.
`05-legacy.jpg`'s existing pull-back fortress framing already supports this; no new background
needed. The closing headline, Urdu line, "Higher Together" and the join CTA are unchanged.

`.story-scroll-area` grew from 650vh to 800vh to give the new Legends beat proper scroll room
without compressing the other four.

Two real bugs found and fixed while verifying this round, neither introduced by this round but
both surfaced by it:

1. `clan-story.js`'s scroll-progress formula divided by `document.body.scrollHeight - innerHeight`
   — the whole page's scrollable height, including `#clan-content` and the footer below the
   story. Since the sticky stage's actual pin range never covers that extra height, the Legacy
   scene (the last of the five) only reached its `.active` state right as, or after, the stage
   had already started unpinning — it could flash in but never settle fully on screen. Fixed by
   measuring progress against the story section's own pin range instead, anchored off
   `.story-scroll-area` (a plain, non-sticky block) rather than the sticky stage itself: reading
   `offsetTop` on a `position: sticky` element returns its current *stuck* render position in
   this browser once scrolled, not its static one, so it can't be used as a stable boundary.
2. The reduced-motion fallback's `.story-panel` override never reset the base rule's
   `display: flex`, so a panel with more than one now-`position: static` child laid its children
   out side by side in a row instead of stacking them. Invisible while every panel had at most one
   multi-part block (ADR-077), but latent even then in the Pillars scene's title + track pair;
   newly obvious once this round's captions/legends markup added more such panels. Fixed with one
   `display: block` on the fallback's `.story-panel` rule.

## ADR-079 — clan page cleanup + aggregate Discord guild stats (member count, boost tier)

Requested: clean up `web/clan.html`'s `#clan-content` and improve/add Discord-integration
features now that the guild ID is configured. Two things were wrong with `#clan-content`
specifically: its first `.stat-grid` only ever filled 1 of the 3 tiles the CSS was already
built/animated for (`style.css`'s `.stat-grid`/`.stat`, `:nth-child(2)`/`(3)` stagger delays going
unused), and a 3-link "Explore" block just duplicated the site's own top nav (Leaderboard/Player
Profiles/Tournaments) for no reason. Separately, the client-side live widget badge
(`[data-discord-widget]`, ADR-066) had existed since that round but had never actually rendered
anywhere: `web/assets/js/config.js`'s `DISCORD_GUILD_ID` was blank, so `wireDiscordWidgets()`
always early-returned. And beyond that badge, the site had **no real Discord guild data anywhere**
— `WebsiteService`/the API are deliberately Discord-agnostic (ADR-040/042), so `member_count` on
the clan page has only ever meant "linked Brawlhalla accounts," never an actual Discord server
member count.

Confirmed before implementing: new Discord-integration features stay within ADR-040's boundary —
**aggregate/guild-wide numbers only** (member count, server boost tier), never anything tied to a
specific person (no avatars/usernames/online-status lists). This round reaffirms that boundary
rather than reversing it.

**Architecture constraint that shaped the design**: the API (Render, `shaheen-api`) and the bot
(Fly.io) are separate deployed processes — the API has no live discord.py gateway connection, so
it can never read `guild.member_count` itself; only the bot can. `ClanCog._snapshot_tick`
(`src/bot/cogs/clan.py`) already fetches `guild = self.bot.get_guild(...)` on every scheduled
tick for the existing Brawlhalla snapshot; `guild.member_count`, `guild.premium_tier`, and
`guild.premium_subscription_count` are all already-cached fields on that same object
(`Intents.all()` already enabled — no new intents, permissions, or Discord API calls needed). So
the bot now persists a lightweight `GuildSnapshot` row on every tick — append-only, same shape as
`RankingSnapshot` — and the already-read-only API serves the latest one, the exact same bot → DB
→ API → website pipeline every other stat on this site already uses, just with a guild-level
table instead of a per-player one.

New pieces: `src/database/models/guild_snapshot.py` (`GuildSnapshot`: `guild_id`, `captured_at`,
`member_count`, `boost_tier`, `boost_count`) + `alembic/versions/0007_guild_snapshots.py` +
`src/database/repositories/guild_snapshot_repository.py` (`add`/`get_latest`, mirrors
`RankingSnapshotRepository`). `src/services/guild_snapshot_service.py` is a new, separate,
deliberately Discord-agnostic service (takes plain ints, never a `discord.Guild` object) — it
doesn't belong inside `SnapshotService`, which is Brawlhalla-API-driven and explicitly documented
as never touching Discord; guild member/boost counts come from Discord, not Brawlhalla.
`ClanCog._snapshot_tick` calls it right alongside the existing `SnapshotService.run_for_guild`
call, same session, same cadence (`snapshot_interval_hours`) — no new loop.

`ClanInfo` (`services/website_service.py`) and `ClanInfoResponse` (`api/schemas.py`) both gained
three nullable fields (`discord_member_count`, `discord_boost_tier`, `discord_boost_count`) —
nullable because a fresh deploy has no `GuildSnapshot` row yet until the bot's next tick, and the
frontend must degrade gracefully rather than show a misleading `0`.

Frontend (`web/assets/js/pages/clan.js`, `style.css`): the stat grid now renders up to 3 tiles
(Linked Members always; Discord Members and Server Boost only when their value is present/
nonzero — no snapshot yet just means those tiles don't render, not a broken "0" state). The
"Explore" block is gone, replaced by a small "Join the Community" strip: the existing
`DISCORD_INVITE_URL` button plus a third `[data-discord-widget]` instance — giving the
already-built widget an actual home in the page's own content instead of only header/footer
chrome. That third badge didn't exist yet when `api.js`'s `DOMContentLoaded` handler first ran
`wireDiscordWidgets()` (this card renders later, once its fetch resolves), so `clan.js` re-invokes
that same global best-effort function after rendering — no new widget logic, just re-running the
existing one now that its target exists. A couple of inline `style="..."` attributes in the motto/
tagline markup were replaced with two small CSS classes (`.motto-centered`/`.tagline-centered`),
matching the rest of the codebase's class-driven convention.

`web/assets/js/config.js`'s `DISCORD_GUILD_ID` was filled in with the real numeric guild ID
(public, not secret — same treatment as the already-hardcoded `DISCORD_INVITE_URL`) to finally
activate the dormant widget badge. Still best-effort: it requires "Server Widget" enabled under
Discord's Server Settings → Widget, an out-of-repo portal toggle ADR-066 already flagged; the
badge simply stays hidden if that's off, same as before.

Files: `src/database/models/guild_snapshot.py` (new), `src/database/repositories/
guild_snapshot_repository.py` (new), `src/services/guild_snapshot_service.py` (new),
`alembic/versions/0007_guild_snapshots.py` (new), `tests/test_guild_snapshot_service.py` (new),
`src/bot/cogs/clan.py`, `src/api/schemas.py`, `src/services/website_service.py`,
`src/api/routers/clan.py`, `web/assets/js/config.js`, `web/assets/js/pages/clan.js`,
`web/assets/css/style.css`, `tests/test_api.py`.

Verified: `ruff`/`mypy`/`pytest` (full suite including the new/extended tests) pass; the Alembic
migration applies and rolls back cleanly; headless-Chromium pass on `web/clan.html` confirms the
stat grid renders correctly both with and without the Discord fields present, the "Explore" block
is gone, and the "Join the Community" strip renders with a working invite link. The live widget's
actual output against the real `discord.com` widget endpoint couldn't be verified from this
sandboxed environment — the wiring and graceful-fallback logic were verified instead.

Files: `web/clan.html` (Hero/Spirit panels re-anchored to the lower frame; `#story-eagle` layer
added; Pillars track markup replaced with spotlight + five static captions; Journey section
replaced with the new Legends section; the six feature words moved into Legacy as a strap-line),
`web/assets/css/style.css` (`.story-eagle`/`.story-eagle-pose` added; `.story-pillar`/
`.story-pillars-track` replaced with `.story-pillar-spotlight`/`.story-pillar-captions`/
`.story-pillar-caption`; `.story-legends-caption`/`.story-legends-strip`/`.story-legend` added;
`.story-features`/`.story-feature`/`.story-journey`/`.story-journey-card` removed;
`.story-legacy-features` added; `@media (max-width: 800px)` and the global
`prefers-reduced-motion` block both updated for all of the above), `web/assets/js/clan-story.js`
(eagle sub-beat spanning scenes 0–1 added; pillar `translateX` pan logic replaced with the
`--focus` spotlight sweep + caption crossfade; legends sub-beat added), `web/assets/img/story/
eagle_{perched,launch,flying}.png` + `legend_{mordex,brynn,tezca,nix,jaeyun}.png` (new, copied
from the delivered zip as-is), `docs/DECISIONS.md` (this entry).

Verified: headless-Chromium pass — the eagle visibly steps perched → launch → flight across the
Hero and Spirit scenes without covering their text, and the Iqbal couplets still crossfade
correctly underneath it; the pillar spotlight sweeps across the totems roughly in sync with their
positions in the art, captions and progress track correctly, no card/border/box renders anywhere
in that scene; the legends strip slides through all five, the active one is sharp/large/full
opacity and the rest are visibly dimmed/blurred/small, no card/border box; the legacy strap-line
renders as plain inline text with the closing headline and CTA unchanged; reverse-scroll holds up
for all of the above; desktop (~1440px) and ~400px mobile widths both hold up; `prefers-reduced-
motion: reduce` renders a static, fully-visible stack — all five pillar captions, the full
legends roster, and both Iqbal quotes all present and readable, decorative-only layers (eagle,
background art, spotlight) simply hidden rather than frozen mid-pose; no broken images, no
console errors; the untouched API-driven `#clan-content` block below still renders and animates
correctly. No Python changes — `ruff`/`mypy`/`pytest` untouched.

## ADR-079 — first-visit "Shaheen" landing gate; clan.html's story goes fully static

Requested: bring the delivered `shaheen-scenes.html` film into the site as a one-time landing page
for brand-new visitors, so the clan makes a cinematic first impression before anyone touches the
home page — but never trap anyone: once seen (or on any exit/CTA click) it must not come back on
its own, and it must stay reachable on demand from the site nav. In the same pass, clan.html's
five-beat story section was to lose its scroll-driven stage entirely and read as a simple stacked
narrative.

**Landing page** (`shaheen-scenes.html` → `web/landing.html`): the delivered scenes file was
promoted into the site as `web/landing.html` (relative asset paths resolve correctly from the
`web/` root; the root-level original is left untouched as the source copy). Its prototype nav
anchors were replaced with real page links (Home, Clan, Roster, Tournaments, Leaderboard, Join) and
its Legacy-scene CTAs now target `join.html`/`roster.html`/`index.html`. The first-visit gate is a
single localStorage key `shaheen_landing_viewed`: only `index.html` carries a pre-paint redirect —
if the key is absent it runs `location.replace("landing.html")` from a `<script>` in `<head>`,
wrapped in a try/catch so private-mode/blocked-storage browsers fall through to the normal homepage
instead of erroring. `landing.html` itself never redirects and sets the key three ways: scrolling
the closing Legacy scene to its end (`p >= 0.98`), clicking any `[data-leave]` link (normal anchor
behaviour, key set), or clicking `[data-enter]` (key set, then navigated via `leaveTo(href)`).
"Scenes" was added to the nav of every page so the film is always one click away.

**Static story** (`web/clan.html`, `web/assets/css/style.css`): the sticky stage
(`.story-stage`/`.story-scroll-area`), `clan-story.js`, the eagle poses, the pillar spotlight, the
progress dots, the scene counter and the scroll hint are all removed. The five beats (Hero, Spirit,
Pillars, Legends, Legacy) are now ordinary stacked `<section>`s inside a `.story-static` wrapper,
each with its story art behind a dark gradient and all copy statically in the DOM — the layout
ADR-077/078 only produced under `prefers-reduced-motion`, now the only path. The old animated
`.story-*` rules and their reduced-motion overrides were replaced by a scoped
`.story-static .story-*` block (the reduced-motion media query otherwise is unchanged for the rest
of the site). `web/assets/js/clan-story.js` is deleted as dead code. The API-driven
`#clan-content` block below the story was already wrapped in its own `.wrap` and is unchanged.

Files: `web/landing.html` (new, from `shaheen-scenes.html`), `web/index.html` (pre-paint redirect +
Scenes nav), `web/clan.html` (static story rewrite, Scenes nav, `clan-story.js` include removed),
`web/assets/js/clan-story.js` (deleted), `web/assets/css/style.css` (`.story-static` block in,
animated story rules out, reduced-motion story overrides removed), the other nine `web/*.html`
pages (Scenes nav), `docs/DECISIONS.md` (this entry).

Verified: with no flag, index.html routes to landing.html before first paint; with the flag set it
loads normally, and landing.html loads directly in every case; finishing the Legacy scene, clicking
any `[data-leave]` link and clicking `[data-enter]` each set the key; all nav links and CTAs land
on the right pages. clan.html renders the five beats as readable stacked sections with art behind a
gradient at desktop and ~400px widths, copy fully present with no JS, and the `#clan-content` block
below unaffected. No references to `clan-story.js` or the removed story classes remain anywhere in
`web/`. No Python changes — `ruff`/`mypy`/`pytest` untouched.

## ADR-080 — landing page rethemed to the site palette; clan anthem added

Requested: the first-visit landing page (ADR-079) still carried the delivered prototype's muted
antique-gold / cold blue-grey cinematic palette, which reads against the premium green/gold site
theme (ADR-066) — bring its colors into the site token set. In the same pass it was to get the
site-wide background audio (ADR-073) like every other page.

**Palette** (`web/landing.html`): the page's own `:root` tokens now mirror the site
(`assets/css/style.css :root`): `--ink:#030604`/`--stone:#0a1f15`/`--slate:#071008` (the green-tinted
darks), `--gold:#ffd23f`/`--gold-dim:#e8b52f`, `--gold-hi` and `--mist` both `#eaf6ef` (site cream —
highlights and body alike, exactly as the site uses cream for text), `--muted:#8a9992` (site grey),
plus the site's `--green:#2fe89a`/`--green-soft:#1fb87e` secondary accent. The bulk of the page was
already token-driven, so the recolor came from swapping those values; the remaining hardcoded
literals were shifted hue-for-hue from the old cool blue-grey ramp to green-tinted equivalents
(text greys, scene scrims/overlays `rgba(4,6,9,…)` → green-tinted darks, white dims →
`rgba(47,232,154,…)`) and every old gold glow `rgba(207,165,80,…)` → `rgba(255,210,63,…)`. Green now
carries the interactive accents the way the site does: nav hover, the scene-4 primary CTA
(`.btn` — green border/cream text, green fill on hover), the ghost button borders, and the ambient
glows behind the pillar ring and legend cutouts. The scene-4 eyes/hover text-on-gold darks became
the site's `#04120a`.

**Music** (`web/landing.html`, reusable `web/assets/js/audio.js`): the landing page now includes
`assets/js/audio.js` like every other page, so the clan anthem and its mute state/position follow
the same localStorage keys (`shaheen-audio-muted`, `shaheen-audio-position`) across the whole site.
Because the page is self-contained (no `style.css`), the `.audio-toggle` button is styled inline in
the page's own green/gold tokens — same geometry, hover, muted and is-pending (autoplay-waiting)
states as the site-wide button, bottom-left, shrinking to 44px below 1100px. The full-width
`.footline` strip is padded 64px on its left so the fixed button never sits on the corner text; the
hero scene's word rail on phones is a decorative strip beneath a non-interactive overlay and is
left alone.

Files: `web/landing.html` (token remap + literal recolors + audio toggle CSS + `audio.js` include),
`docs/DECISIONS.md` (this entry).

Verified: no old-palette literals remain in `web/landing.html` (grep sweep of the retired hexes and
rgba seeds); the inline `<style>` still has balanced braces (290/290); the toggle renders
bottom-left with footline text cleared, and returns to the same size/position convention as the
rest of the site. No Python changes — `ruff`/`mypy`/`pytest` untouched.

## ADR-081 — achievements rebuilt: 30-entry catalog, four award sources, per-member website view

Reported: "Achievements are same for all members — how is this possible?" Two independent causes,
both real.

**Cause 1 — the website page has no member dimension.** `web/achievements.html` is a clan-wide
gallery by design (ADR-071): `WebsiteService.get_achievement_gallery` returns *the whole catalog
once* with holder counts. Everyone saw the same cards because that page never varied by member.

**Cause 2 — the catalog barely discriminated.** There were five achievements. `first_link` goes to
every linked member by definition. `games_100`/`games_500` evaluate against **lifetime career
games**, which any established Brawlhalla player clears on their very first snapshot. That left the
two tier achievements as the only ones that could differ. Worse, only two systems awarded anything
at all (`link_service.py`, `snapshot_service.py`) — tournaments, matches, scrims, chat XP, MVP weeks
and tenure awarded nothing, and the `extra` JSON column on `member_achievements` was declared,
accepted by the repository, and never written or read.

**Catalog: 5 → 30**, across six categories (`onboarding`, `milestone`, `ranked`, `competition`,
`community`, `tenure`) with a new `category` field on `AchievementDef` and an `achievements.category`
column. `services/achievements.py` stays pure — no DB, no Discord — and grows threshold tables plus
four evaluators, each taking plain numbers:

| Source | Evaluator | Awards |
|---|---|---|
| Ranked snapshot | `evaluate_snapshot_achievements` (extended) | games 100→5000, tier gold→valhallan, peak 1500/1800/2000, `global_top_1000`, `region_top_100`, `win_rate_60` |
| Clan competition | `evaluate_competition_achievements` | `first_win`, `wins_10`, `wins_50`, tournament entrant/finalist/champion, `scrim_regular` |
| Engagement | `evaluate_engagement_achievements` | chat level 10/25/50, `mvp_of_week` |
| Tenure | `evaluate_tenure_achievements` | 30/180/365 days from `ShaheenMember.joined_at` |

`win_rate_60` is floored at `MIN_RANKED_GAMES_FOR_WIN_RATE = 50` ranked games — a 100% rate over
three games is noise. Tenure fails closed when `joined_at` is NULL rather than guessing.

**One award seam.** `services/achievement_service.py` is new and is the only place that turns an
`AchievementDef` into a row. `link_service` and `snapshot_service` were refactored onto it; the four
new sources use it too, instead of what would have become six copies of the same "look up catalog
row → award → build an Announcement" dance. A catalog miss logs a warning and returns None (the
deploy is mid-migration) rather than failing the caller's real work — a match result is not worth
losing over a missing badge.

**`extra` put to work.** Every award now records what earned it (`{"games": 1043}`,
`{"tournament_id": 3, "placement": 1}`, `{"peak_rating": 1812}`), so two members holding the same
badge still read differently.

**New award call sites.** `match_service.confirm_result` *and* `resolve_result` (a staff-settled
dispute is still a win); `tournament_service.register` (entrant) and final-round completion
(champion + finalist to the winner, finalist to the runner-up) — event-driven rather than
count-driven, because a tournament placement is not a running total; `cogs/engagement.py` on chat
level-up, guarded so a lurker who has never linked doesn't get a member row created just by talking;
`ClanCog._rotate_mvp_role` on the weekly MVP; and tenure on the snapshot loop, which is already the
one recurring pass over every linked member, so time-served milestones need no job of their own.

**`region_rank` is now persisted** (`ranking_snapshots.region_rank`). It has been fetched and shown
in Discord since Phase 2 and thrown away every time; it backs `region_top_100`.

**Website.** The gallery keeps its clan-wide checklist and gains `category` plus a rarity band
(`rarity_label` in `services/achievements.py`, so Discord and the site can't drift on what "rare"
means; 0% reads **Unclaimed**, not Legendary — nobody holding it says nothing about difficulty).
The real fix for the reported symptom is new: `GET /players/{id}/achievements` returns the full
catalog flagged earned/unearned with award dates, and `web/player.html` renders it grouped by
category with an "N of 30 earned" bar. That per-member view did not exist anywhere before.

**Migration `0008`** adds both columns, backfills categories for the five existing rows, and inserts
the 25 new ones with seed data inlined (never imported from app code, following `0003`). The
downgrade deletes dependent `member_achievements` rows first (FK), then the 25 keys, then both
columns.

Files: `src/services/{achievements,achievement_service,snapshot_service,link_service,match_service,
tournament_service,website_service}.py`, `src/bot/cogs/{clan,engagement}.py`,
`src/database/models/{achievement,ranking_snapshot}.py`,
`src/database/repositories/{match,scrim}_repository.py`, `src/api/{schemas.py,routers/{achievements,
players}.py}`, `alembic/versions/0008_achievement_expansion.py`, `web/assets/js/{api.js,pages/
{player,achievements}.js}`, `web/assets/css/style.css`, tests, this entry.

Verified: migration 0008 round-trips on a scratch SQLite DB (30 rows with the expected category
split, both columns added and cleanly dropped, re-upgrade to head clean); evaluator boundary tests
at each threshold and one below; integration tests that a match confirmation, a staff resolution, a
tournament registration and a tournament win each actually award; API tests for the checklist
endpoint and the gallery's new fields; Playwright confirms the player page renders the grouped
checklist and falls back to the earned-only list if the new endpoint 404s (an API instance that
predates it must not take the page down).

## ADR-082 — why the live Discord widget was never visible, and how it fails now

Reported: "I don't see the live widget." It was not the guild ID — `1546568759530229961` is set and
valid. Four causes, ranked by how much they mattered:

1. **The page being looked at had no badge on it.** `web/index.html` redirects a first-time visitor
   to `landing.html` (ADR-079), and `landing.html` contained **zero** `[data-discord-widget]`
   elements and loaded neither `config.js` nor `api.js`. In a fresh browser or incognito session the
   badge could not exist. Fixed: the landing page now carries the badge and both scripts, styled in
   its own inline token set rather than importing `style.css`.
2. **Every failure was silent** — a bare `return` on `!response.ok` and a bare `catch {}`. "Widget
   disabled" was indistinguishable from "wrong guild" from "network error" without opening the
   Network tab. Each bail-out now logs a specific reason: 403 names the *Server Settings → Widget →
   Enable Server Widget* toggle, 404 names the guild ID and where it's configured, any other status
   reports itself, and a network failure reports its message.
3. **`members.length` instead of `presence_count`.** Discord caps `members` at 100 and omits members
   who opted out, so it under-reports on any real server — and an empty array rendered a literal
   "0 online now". Now `presence_count` is preferred, `members.length` is a fallback, and a response
   with neither is treated as no usable signal (hidden + warning) while a genuine `presence_count: 0`
   still renders.
4. **`[hidden]` was inert** — `.discord-widget { display: inline-flex }` beat the UA's
   `[hidden] { display: none }`, so `el.hidden = false` was a no-op and the CSS comment claiming
   "hidden by default" was false. `.discord-widget[hidden] { display: none }` makes the attribute
   load-bearing.

Also: `clan.js` rendered its "Join the Community" strip *inside* the `getClan()` try block, so a
cold Render instance took the whole strip down; the skeleton now renders before the API call.
`join.html` had the invite URL hardcoded twice and both copies had gone stale against `config.js`;
any element marked `[data-discord-invite]` now reads from `DISCORD_INVITE_URL`.

**Out of repo, and never once verified in this repo's history:** the *Enable Server Widget* toggle.
With it off the endpoint returns `403 {"code": 50004}`. Fastest triage — open
`https://discord.com/api/guilds/1546568759530229961/widget.json` in a browser tab: 200 means Discord
is fine and it was the redirect; 403 means flip the toggle; 404 means the guild ID is wrong.

Files: `web/assets/js/api.js`, `web/assets/css/style.css`, `web/landing.html`,
`web/assets/js/pages/clan.js`, `web/join.html`, this entry.

Verified: Playwright across three pages (`index.html`, `landing.html`, `clan.html`) × seven mocked
widget responses (presence_count 57, a genuine 0, members-array fallback, empty/no-data, 403, 404,
500) — the badge renders the right count when there is one, stays hidden rather than showing a
misleading zero when there isn't, and logs the distinct warning for each failure. The live endpoint
is unreachable from this sandbox (the egress proxy blocks `discord.com`), so real output stays
unverifiable here — the browser-tab triage above is how that gets confirmed.

## ADR-083 — /lookup: check any Brawlhalla player's rank without linking, in clan context

Requested: let people check a Brawlhalla rating without linking an account, but make it relevant to
the clan — "comparing to close members or their ranking."

**Identifiers, not names.** Brawlhalla's API has no username search — only `/search?steamid=` and
`/player/{id}/...`. So `/lookup` takes a Steam64 ID or a Brawlhalla player ID, reusing
`BrawlhallaService.resolve_identifier`, which already handles both. Because a plain "player not
found" would read as "that player doesn't exist" when the real problem is that a *name* was typed,
a `NotFoundError` renders a dedicated help embed naming both accepted ID formats and where to find
them, rather than the global handler's one-line warning.

**The clan half is the point.** `ClanService.rank_context(guild_id, rating)` walks every actively
linked member's latest snapshot and returns where that rating would slot in: the rank it would hold,
and the nearest member above and below with rating deltas. "1720" means little; "would place #3 of
11, 200 below Kaero, 140 above Ali" means something.

**Read-only.** `/lookup` writes nothing — no `DiscordUser`, no `ShaheenMember`, no
`BrawlhallaPlayer` row, no link, no snapshot — and the embed footer says so. It is ephemeral and
needs no permission check, matching `/profile`'s any-member posture. `LookupService` composes the
existing `LinkService.resolve_candidate` (for error translation) and `ProfileService` (for the
cached fetches) rather than reaching for the integration client directly.

Files: `src/services/{lookup_service,clan_service}.py`, `src/bot/{cogs/lookup.py,
content/lookup_embeds.py,client.py}`, `tests/test_{lookup_service,lookup_embeds,clan_service}.py`,
this entry.

Verified: service tests cover placement mid-ladder, at both ends, with no ranked members, with an
unranked target, and that a lookup leaves the database untouched; embed tests cover the ladder edges
and the help copy. Commands can't be exercised against live Discord from here, so the service and
embed layers beneath them carry the coverage, matching the existing cog-test approach.

## ADR-084 — /compare, /refresh, /clanstats, and ranked-Legend data finally surfaced

A command-gap pass over the bot alongside ADR-081/083. Four additions, each filling something
nothing else covered:

- **`/compare <member_a> [member_b]`** — side-by-side ranked and lifetime stats for two linked
  members. `/rivalry` already covers the head-to-head *match record*; nothing covered stats.
  Rendered as aligned rows rather than paired embed fields so the numbers line up on mobile.
- **`/refresh`** — a member's own snapshot on demand. Before this, data only updated on `/link` or
  the six-hour loop. Because this is member-triggered traffic to the Brawlhalla API,
  `SnapshotService.refresh_member` enforces `REFRESH_COOLDOWN_SECONDS = 15 * 60`, measured off the
  last stored snapshot rather than an in-process timer, so it survives a bot restart. It runs the
  same work the scheduled loop does, achievement awards included, so a member who just crossed a
  threshold doesn't wait for the next tick.
- **`/clanstats`** — clan-wide aggregate: combined games/wins, average *and* median rating, highest
  rated member, tier spread, region split and most-played Legends. Median sits next to the mean
  deliberately: on a roster this size one high-rated member drags the average well away from where
  the clan actually sits. `ClanService.clan_stats` reuses `leaderboard()` and `legend_meta()` and
  keeps the established "loop the small set of linked members in Python" shape (ADR-068).
- **Ranked per-Legend data surfaced.** `PlayerRankedResponse.legends` (per-Legend ranked rating,
  peak, tier, W/L) has been parsed on every snapshot since Phase 2 and discarded unread. `/legends`
  now annotates each Legend row with it when the member has played that Legend in ranked.

Files: `src/services/{clan_service,snapshot_service}.py`, `src/bot/cogs/{profile,clan}.py`,
`src/bot/content/{profile_embeds,clan_embeds}.py`, `tests/test_{clan_service,snapshot_service,
profile_embeds,clan_embeds}.py`, this entry.

Verified: cooldown tests for all three states (no prior snapshot, blocked with nothing fetched or
written, and running again once the window passes); `clan_stats` aggregation including the
empty-roster case; embed tests for the compare footer, an unranked side rendering "—" rather than a
fabricated 0, and the ranked-Legend annotation appearing only when ranked data is present.

**Note on ADR numbering:** `docs/DECISIONS.md` carries two entries numbered **ADR-079** (the clan
page cleanup + guild stats round, and the first-visit landing gate). Both are referenced elsewhere,
so the collision is left documented rather than renumbered; new ADRs continued from 081.

## ADR-085 — clan page rebuilt; the "story art" was screenshots of the mockup

Reported: "clan page have hero sections that is not good, make it again with new template."

**The cause was not styling.** `web/assets/img/story/0{1..5}-*.jpg` — the five full-bleed
backgrounds behind the clan story — are **screenshots of the original design mockup**, not artwork.
Opened directly they show the mockup's own nav bar (`HOME ABOUT COMMUNITY TOURNAMENTS JOIN`), its
own `SHAHEEN` wordmark, a scroll progress bar, social icons, and headlines sliced mid-word by the
crop (`IGH. FIGHT HARD. / VE A LEGACY.`, `N A NAME`, `T OF / EN`, `alla clan built for players`).
The page then printed the same copy in HTML on top of a picture of that copy, under a heavy dark
gradient. Five of those in a row, each `min-height: 100vh`, is what read as "five bad heroes":
duplicate titles, duplicate pillar cards, and truncated words baked into the pixels. The five
`legend_*.png` files are the same kind of thing at a smaller scale — rectangular card crops with a
landscape background, a sliver of the neighbouring legend at the left edge, and the legend's name
burned into the bottom.

**All five screenshots are deleted**, along with `web/assets/img/banner.webp` (orphaned; the CSS
only ever referenced `banner.jpg`) and the repo-root `shaheen-scenes.html` (a 3.5 MB pre-retheme
duplicate of `web/landing.html`, outside the deployed directory, referenced nowhere but this file).
`banner.jpg` stays — it is the real brand art and backs `.page-banner` site-wide.

**What replaces them.** The page keeps the standard chrome (header, ticker, footer) and the site's
own card / divider / button language; the cinematic weight now comes from type scale and section
rhythm rather than full-screen photos:

- **Overture** — one masthead (`min-height: min(76vh, 640px)`) replacing both the old `.page-banner`
  and the duplicate `story-hero` beneath it. Its field is **pure CSS** — a green-black ground, a low
  gold horizon and a vignette. `banner.jpg` was tried here and rejected: its own wordmark and
  strap-lines are baked in, which reproduced the exact duplicate-title problem this rebuild exists
  to remove.
- **Spirit** — an asymmetric split: the two Iqbal couplets as real `<blockquote>`s with gold rules
  and glosses, beside a framed piece of art.
- **Pillars** — five `.card`s in a five-column grid with gold indices, so `spotlight.js` and the
  site's card treatment apply for free. Sized to keep "BROTHERHOOD" and "IMPROVEMENT" on one line
  even when Bebas Neue hasn't loaded and the wider fallback face is in use.
- **Legends** — the five crops framed as deliberate portrait tiles (`aspect-ratio: 3/4`,
  `object-fit: cover`, cropped up and right) so the baked-in caption and the neighbouring legend
  fall outside the frame. The name and trait below each tile are real text.
- **Legacy** — the closing band, then the site's truck-art divider and the live `#clan-content`
  block, unchanged.

**The eagle cutouts are now used, not deleted.** `eagle_perched.png` and `eagle_flying.png` were
orphaned (an earlier plan had them down for removal) but they are the one piece of genuinely clean,
transparent, on-brand art in the repo. Both carry a stray fragment from their original cutting, so
each is deliberately oversized and clipped so the fragment lands outside its box.

Motion is the existing site-wide `.reveal` IntersectionObserver in `assets/js/scroll.js` — this page
adds no JavaScript of its own, and inherits the reduced-motion behaviour unchanged.

**Story duplication collapsed.** The five beats existed in three places: `landing.html` (the
cinematic first-visit gate), the repo-root `shaheen-scenes.html` (a dead copy of it), and
`clan.html` (the same beats as flat photo panels). The dead copy is gone; `landing.html` keeps the
cinematic telling; `clan.html` is now the editorial clan page rather than a third retelling.

Files: `web/clan.html`, `web/assets/css/style.css` (the `.story-static` block, 312 lines, replaced
by `.clan-*`), `docs/COMMANDS.md` untouched, deletions listed above, this entry.

Verified with Playwright at 1440×900 and 390×844: no broken images, no horizontal overflow, no
console errors, five pillars and five legend tiles present, every `.reveal` section resolving to
visible, no surviving reference to `story-panel`/`story-static` or to any deleted screenshot, all
five pillar headings measured at exactly one line, and a 404 sweep across `index`, `clan`, `join`,
`achievements`, `player` and `landing` returning none. `web/` drops from ~11.3 MB to 9.3 MB, and the
repo also sheds the 3.5 MB root prototype. No Python changes — `ruff`/`mypy`/`pytest` untouched.

**Known, pre-existing and not addressed here:** `.audio-toggle` is `position: fixed` at the
bottom-left of the viewport site-wide, so it sits over whatever content is in that corner at the
current scroll position — on a phone that can include this page's first call to action. Changing it
affects every page and belongs in its own pass.

## ADR-086 — the badge stops depending on a toggle nobody can verify; real legend art

Two reports: the live Discord badge still isn't visible, and the legend images should be cut from
the official legend line-up sheet.

**The badge had a single point of failure outside this repository.** Every version since ADR-066
read one source: `discord.com/api/guilds/{id}/widget.json`, which only answers when *Enable Server
Widget* is switched on in Discord's Server Settings → Widget. With it off the endpoint returns
`403 {"code": 50004}` and the badge hid itself — correct behaviour, invisible outcome. ADR-082 made
the failure loud in the console; it did not make the badge work. That toggle has never been
confirmed on, and it cannot be checked from this sandbox (the egress proxy blocks `discord.com`;
the deployed site is unreachable from here too).

So the badge now has **two sources**, in order:

1. Discord's widget endpoint → `"N online now"` (a real *online* count, when the toggle is on).
2. **Shaheen's own API** (`GET /clan`) → `"N members"`. The bot already writes a guild snapshot —
   member count, boost tier, boost count — into the database on every scheduled tick (ADR-079), so
   the site can show a real member count with no Discord involvement at all.

That inverts the dependency: Discord's widget is now an *enhancement*, and the badge only stays
hidden when both the widget and our own API have nothing to say. Total failure is still safe — the
badge hides and never renders a misleading number.

**Visible diagnostics.** Appending `?widget-debug=1` to any page renders the failure reason *in the
badge* instead of hiding it (`widget: the server widget is disabled. Enable it in Discord under
Server Settings -> Widget -> Enable Server Widget.`). Console warnings only help someone who already
knows to open devtools; this makes "I don't see the badge" answerable in one click.

**Legend art.** The five `story/legend_*.png` files were crops of the design mockup: a landscape
background, a sliver of the neighbouring legend at the left edge, and the legend's name burned into
the bottom of the image (the page then printed the same name underneath in HTML). They are replaced
by square portraits cut from the official legend line-up sheet — `web/assets/img/legends/{brynn,
jaeyun,mordex,nix,tezca}.png`, 304×304 each. Because the new tiles are clean, `.clan-legend-frame`
drops to `aspect-ratio: 1/1` with `object-position: center` and no defensive crop, and the name
under each tile is now the only one on screen. A hover scale replaces the old transform hack.

Files: `web/assets/js/api.js` (badge rewritten as source-1/source-2 with `?widget-debug=1`),
`web/assets/img/legends/*.png` (new), `web/assets/img/story/legend_*.png` (deleted),
`web/clan.html`, `web/assets/css/style.css`, this entry.

Verified with Playwright: badge renders `57 online now` from a healthy widget response; falls back
to `137 members` from a mocked `GET /clan` on both 403 and 404; stays hidden when the widget fails
*and* the API carries no snapshot; and `?widget-debug=1` renders the reason visibly. The clan page
still loads with no broken images and no console errors, and all five legend tiles now resolve to
`assets/img/legends/`.

**Still outside this repo:** turning the widget toggle on is what upgrades the badge from "N
members" to a live "N online now". Triage unchanged — open
`https://discord.com/api/guilds/1546568759530229961/widget.json`: 200 means it is on, 403 means flip
it, 404 means the guild ID is wrong.

## ADR-087 — cold-start snapshots, automatic rank roles, and /help

Three changes chosen together because each one turns data or work the project already has into
something a member actually sees.

### Cold-start snapshots — the site stops looking broken on first load

The API runs on Render's free tier, which sleeps after 15 minutes idle and can take 30–60s to wake.
`api.js` has had a 50-second timeout since Phase 6 precisely because of this, but the honest effect
was that the first visitor to the clan, leaderboard, roster or achievements page sat on
*"Loading… (first load can take up to a minute)"* — the worst possible first impression for a page
whose whole job is to look like a real esports clan.

`.github/workflows/snapshot.yml` now runs every six hours (and on demand), fetches `/clan`,
`/leaderboard?limit=25`, `/roster` and `/achievements`, and commits each response to
`web/data/<name>.json` wrapped as `{captured_at, source, data}`. Those files ship with the site, so
they load instantly from the same origin. `ShaheenAPI.withSnapshot(name, liveFetch, render)` renders
the committed copy immediately, then re-renders from the live API.

The failure modes are all deliberate:

- **Live call fails, snapshot exists** → the page keeps the snapshot and says how old it is, rather
  than throwing away good data for an error message.
- **No snapshot committed yet** (or the site opened from `file://`) → exactly the previous
  behaviour, including the old error text.
- **An endpoint doesn't respond during the workflow** → a warning, and its previous snapshot is
  left untouched. A sleeping API never overwrites good data with an error page.

The workflow reads `API_BASE_URL` out of `web/assets/js/config.js` rather than repeating it, so it
cannot drift from what visitors actually hit. Committing under `web/` also triggers `pages.yml`, so
a fresh snapshot deploys itself; `pages.yml` never commits, so there is no loop.

### Automatic rank roles — using tier data the bot has collected since Phase 3

Every six hours the snapshot loop has recorded each member's Brawlhalla tier and done nothing with
it. Four new roles (`🥇 Gold`, `💠 Platinum`, `💎 Diamond`, `⚔️ Valhallan`) are now applied and
removed automatically from that same pass.

- `SnapshotRunResult` gained `tiers: dict[int, str | None]`, so the service reports tiers and stays
  Discord-agnostic; `ClanCog._sync_rank_roles` does the role edits, the way `_rotate_mvp_role`
  already does.
- `services/rank_roles.py` is pure: `plan_rank_roles(tier=…, current_keys=…)` returns a diff, so an
  unchanged member costs **zero** API calls on every six-hourly run, a promotion and a demotion both
  leave exactly one role, and roles outside the rank set are never touched.
- Unrecognized tier strings fail closed — a Brawlhalla rename stops granting rather than granting
  the wrong role.
- **Only Gold and above get a role.** Below that the label says more about how much ranked someone
  has played than how good they are, and a wall of low-tier roles discourages more than it
  motivates.
- `hoist=False` on purpose: the member-list sidebar is already grouped by the clan ladder, and four
  more hoisted groups would bury it. These are colour and *mention* tags — "@Diamond scrims at 9" is
  the point. They are `mentionable=True` for exactly that.

### /help — 43 commands and no way to find them

Discord's command picker shows names, no grouping, and no sense of which commands are staff-only.
`/help` renders the catalog grouped the way a member thinks about it (Getting Started, Your Stats,
The Clan, Playing, Tournaments, Community, Staff), with an optional `category` choice for one
section. Ephemeral, no permission check, no database access — it is the one command that has to work
for someone who has done nothing else yet.

The catalog is hand-written rather than introspected: introspection gives names and descriptions for
free but cannot group by intent, cannot mark staff-only (that lives in a decorator), and cannot add
the "why you'd use this" copy that makes 43 names usable. The cost is drift, so
`tests/test_help_embeds.py` walks the real command tree and demands an exact match — adding a
command without listing it fails the suite. The full embed is also asserted against Discord's 6000
character and 1024 per-field limits, since a rejected `/help` would be the worst one to lose.

Files: `.github/workflows/snapshot.yml` (new), `web/assets/js/api.js`,
`web/assets/js/pages/{clan,leaderboard,roster,achievements}.js`, `web/assets/css/style.css`,
`src/services/rank_roles.py` (new), `src/services/snapshot_service.py`, `src/bot/constants.py`,
`src/bot/cogs/clan.py`, `src/bot/cogs/help.py` (new), `src/bot/content/help_embeds.py` (new),
`src/bot/client.py`, `tests/test_{rank_roles,help_embeds,snapshot_service}.py`, this entry.

Verified: 17 new unit tests cover the tier mapping at every boundary (promotion, demotion,
below-Gold strip, unranked, unrecognized tier, other roles untouched, unchanged = no-op) and the
help catalog against the live command tree; `SnapshotRunResult.tiers` is asserted for both a ranked
and an unranked member. Playwright covers the five snapshot cases: snapshot replaced by live data
with the note cleared, live failure keeping the snapshot with its note, no-snapshot-and-dead-API
still showing the old error, live-only unchanged, and the clan page rendering its snapshot with no
console errors. Full suite: 342 passing, ruff and mypy clean.

**Needs one action outside this repo:** run `/setup run` once so the four rank roles are actually
provisioned — until then the sync logs "Rank roles not provisioned" and does nothing.

## ADR-089 — a real join-approval system

Asked: "is an approval system in place?" It was not. `/verify` existed — a staff member manually
promotes someone from Guest to Ally — but there was no way to *apply*, no record of who asked, no
queue, and no trace of who decided what or why. Joining Shaheen was: land in the server, receive the
auto-assigned Guest role, and hope somebody noticed you.

### The flow

1. **Apply** — a permanent "Apply to Shaheen" button in a new public `#📝-apply` channel, or
   `/apply` for anyone who has scrolled past it. Both open the same five-field modal: Brawlhalla or
   Steam64 ID, region/timezone, current ranked tier, why Shaheen, and an optional referrer. Five is
   not a design preference, it is Discord's hard cap on modal inputs — so the five questions had to
   be the ones that actually decide an application.
2. **Review** — the submission posts a card to a new staff-only `#📥-applications` with **Approve**
   and **Decline** buttons. Decline opens a second modal for a short reason.
3. **Decide** — approving grants member access and DMs the applicant; declining DMs them the reason.
   Either way the card is edited in place to show the outcome and **its buttons are removed**.
4. **Track** — `/application` shows an applicant their own status and any staff note;
   `/applications` gives staff the pending queue, oldest first.

### Decisions worth recording

**Buttons find their application through the message, not the custom_id.** The obvious design bakes
the application id into each button's `custom_id`, which in discord.py means `DynamicItem` and a
regex template. Instead the card's message id is stored on the row (`review_message_id`) and the
buttons look themselves up by `interaction.message.id`. The custom_ids stay static, so **one**
registered view serves every card ever posted, forever, across restarts — and it reuses a column
that had to exist anyway to edit the card.

**A decision can only be made once, and the service enforces it — not the UI.** Removing the buttons
after a decision is cosmetic: the card stays in the channel, and two staff can click at the same
moment. `ApplicationService.decide` raises unless the application is still pending, so a double
click or a stale card cannot re-decide a settled application, re-DM the applicant, or re-grant a
role. Nobody can review their own application either.

**One open application, and a 14-day cooldown after a denial.** Long enough that reapplying instantly
isn't a way to wear staff down, short enough that someone who fixed the reason they were declined
isn't locked out for a season. A denial with no timestamp is treated as expired rather than locking
someone out forever. Withdrawing frees the applicant to apply again immediately — they chose to
stop, staff didn't decide anything.

**Applicants are not members.** `Application.discord_id` is a raw Discord id, deliberately **not** a
`ShaheenMember` foreign key. Forcing a member row at submit time would put people in the roster
before anyone approved them, and the roster is supposed to mean something.

**Answers are JSON.** The questions are presentation and will change; the decision is the data. The
form can be reworded without a migration.

**One promotion path.** `bot/membership.py` now owns "remove Guest, add Ally", and both `/verify` and
an approved application call it. Two code paths doing that separately would drift, and a member let
in through one door but not the other is the kind of bug nobody finds until someone can't see a
channel.

**Everything an applicant writes is untrusted input.** The review embed clips every free-text field
to 1000 characters — Discord rejects a field over 1024, and a rejected embed would lose the card the
buttons hang off. The decision DM tells the applicant the outcome and any staff note but never who
decided; that stays in `#📥-applications`.

**Nothing is lost if a channel is missing.** If `#📥-applications` isn't provisioned or the bot can't
post there, the application row is still written and `/applications` still lists it — a `/setup`
that hasn't been run yet must not silently swallow someone's application.

Files: `src/database/models/application.py`, `src/database/repositories/application_repository.py`,
`src/services/application_service.py`, `src/bot/{membership.py,views/application.py,
cogs/application.py,content/application_embeds.py}` (all new),
`alembic/versions/0010_applications.py`, `src/bot/{constants.py,client.py,cogs/setup.py,
cogs/moderation.py,content/{channel_intros,help_embeds}.py}`, `docs/{COMMANDS,ROADMAP}.md`,
`tests/test_application_service.py`, this entry.

Verified: 16 new tests (374 total, was 358) covering one-open-application, the decide-once guard,
self-review rejection, the cooldown and its expiry, an approved member reapplying, withdraw-then-
reapply, per-guild scoping, queue ordering excluding decided rows, review-card lookup, plus embeds
for a 4000-character answer being clipped under Discord's limit, an applicant who left the server,
and the decision DM not naming the reviewer. Migration 0010 round-trips on a scratch SQLite DB. The
existing `test_setup_launch_messages` suite caught that `#📥-applications` had no intro message —
now it has one. ruff and mypy clean across 123 source files.

**Needs `/setup run`** to create the two new channels and post the apply panel.

## ADR-090 — Ally is read-only, the rest of the moderator toolkit, and the legend emoji pack

Asked: is a real permission tier in place now that anyone can apply — new members should see the
basic channels, an approved applicant should get into the member channels but read-only, and an
actual Shaheen member should be able to type — plus whatever moderator commands are still missing,
and a curated set of custom emoji cropped from the clan's own Brawlhalla legend art, picked by a
bot command rather than uploaded by hand one at a time.

### Ally becomes a real middle tier

Before this round `gated` categories (THE NEST, BRAWLHALLA, VOICE) drew one line: Guest is hidden
out, every other rank role in fully, with identical read/write access. That collapsed the entire
point of Ally — "approved, but not yet a playing member" — into "same as everyone else." Two new
tuples in `bot/constants.py` split it properly: `VERIFIED_ROLES` still governs *view*, and the new
`FULL_MEMBER_ROLES` (Trial Shaheen and everything above it — Ally deliberately excluded) governs
*participation*. `SetupService._apply_membership_tier` layers this on top of the existing gated
overwrite: Ally gets `send_messages=False` on a gated text channel and `speak=False` on a gated
voice channel (they can still connect and listen — "read-only" has no literal meaning for audio, so
listen-only is the closest equivalent); Trial Shaheen and up get the matching `True`. SHAHEEN HQ,
MODERATION, and DEVELOPMENT are untouched — this only applies inside `gated` categories, and only to
channels, not the category shell itself (a category isn't textual or vocal, so the participation
split lives in `_channel_overwrites`, not `_category_overwrites`).

**This closed a real hole, not just a gap.** `LinkCog._maybe_promote` (ADR-026) promoted straight
from **Guest** to Trial Shaheen — meaning anyone could skip `/apply` and staff review entirely by
running `/link` before ever applying. That's a bigger problem than an unfinished permission tier: it
made the approval system built in ADR-089 optional. `_maybe_promote` now requires already holding
Ally; a bare Guest who links stays Guest. ADR-026 is superseded, not deleted from history — the
promotion trigger (linking a Brawlhalla account) is unchanged, only the starting rank required to
trigger it.

### The rest of the moderator toolkit

The existing set (`/warn`, `/kick`, `/ban`, `/timeout`, `/purge`) had no way to undo two of its own
actions and no channel-level tools at all. Six additions, all following the same "do it, log it, no
confirmation needed" shape as `/timeout` and `/purge` already used — these are either reversible
(`/unban`, `/untimeout`, `/unlock`) or low-stakes config changes (`/lock`, `/slowmode`, `/nickname`),
so unlike `/kick`/`/ban` they skip `ConfirmView`:

- **`/unban`** / **`/untimeout`** — undo the two actions that had no undo.
- **`/lock`** / **`/unlock`** — toggle `send_messages=False` for `@everyone` on a channel. Explicitly
  *not* a `/setup`-managed state: `/setup run` reconciles every channel's overwrites on every pass
  (ADR-060/069), so a `/lock` left in place gets silently cleared on the next run. That's a feature,
  not a bug to work around — a stale lockdown nobody remembers to lift is worse than one that expires
  — but it means `/unlock` clears the overwrite key back to `None` rather than forcing it to `True`,
  so unlocking a channel that's normally `staff_only_send` doesn't accidentally grant it send access.
- **`/slowmode`** — direct wrapper over `TextChannel.edit(slowmode_delay=...)`.
- **`/nickname`** — set or reset (omit the argument) a member's nickname; the one identity-management
  tool that was missing entirely.

### Visual pass on every moderation embed

`/mod-log` was a wall of identical grey embeds — same colour, same shape, no way to tell entries
apart at a glance. Every embed in `moderation_embeds.py` now carries the target's avatar as a
thumbnail and, on log/confirm embeds, a footer naming the acting moderator with their avatar plus a
timestamp (`_with_target_thumbnail`/`_with_moderator_footer`, two small helpers rather than
duplicating `set_thumbnail`/`set_footer` calls across a dozen builders). Purely additive — every
existing embed's title/colour/description is unchanged, so this cost nothing in `/help` or command
behaviour, just made `#mod-log` skimmable.

### The legend emoji pack

Two sprite sheets of Brawlhalla-legend reaction art (16 legends, ~13 expressions each) became 24
cropped 128×128 PNGs at `src/assets/emoji/*.png` — one per file, filename is the emoji name. The
selection deliberately avoids the trap of "take GG from every legend": each of the 24 covers a
*different* expression (gg, wp, nt, heart, question, cry, laugh, cool, zzz, fire, money, wolf, rip,
ninja, mask, buddha, yinyang, cheers, thumbsup, sparkle, facepalm, angry, dizzy, wink), and the
legend supplying each one was picked to spread across as many of the 16 as possible — nobody's
personal favourite legend dominates the pack, and no two emoji are redundant. Cropping was the
tedious part: the sheets' row/column grid is 13 columns, not the 12 an eyeballed guess suggested, and
each two-row legend block's label caption doesn't end where the next row starts (row 0's caption
bleeds several pixels past the nominal boundary) — both found by pixel-sampling actual crop
boundaries and overlaying a numbered grid, not by trusting the visible thumbnail labels, several of
which are themselves duplicated/mislabeled in the source art.

`services/emoji_service.py` — `available_emoji_files()` (pure) plus `EmojiService.sync()` — uploads
whichever packaged file the guild's emoji list doesn't already have **by name**. It never overwrites
an existing emoji: a name collision is skipped and reported, not clobbered, so a staff member's own
hand-picked emoji for that name survives a resync. It also respects `guild.emoji_limit` (50/100/150/
250 by boost tier) and only counts *static* emoji against it — an animated emoji already on the guild
doesn't eat into the pack's room. `/emoji sync` (staff only, `bot/cogs/emoji.py`) is the one command;
re-running it after adding files to the folder, or after a guild's emoji were wiped, is exactly the
intended use.

Files: `src/bot/constants.py` (`FULL_MEMBER_ROLES`), `src/services/setup_service.py`
(`_apply_membership_tier`), `src/bot/cogs/link.py` (`_maybe_promote`), `src/bot/cogs/moderation.py`
(6 new commands), `src/bot/content/moderation_embeds.py` (visual pass + new builders),
`src/services/emoji_service.py`, `src/bot/content/emoji_embeds.py`, `src/bot/cogs/emoji.py` (all
new), `src/assets/emoji/*.png` (24 new), `src/bot/client.py`, `src/bot/content/help_embeds.py`,
`docs/{PERMISSIONS,COMMANDS}.md`, `tests/{test_setup_service,test_link_promotion,
test_moderation_embeds,test_emoji_service}.py`, this entry.

Verified: 24 new tests (398 total, was 374) — six on the gated-channel membership tier (text/voice ×
Ally-denied/full-member-granted, plus ungated/restricted channels staying untouched), four on
`_maybe_promote` (bare Guest refused, approved Ally promoted with the correct role swap, Trial/Elite
left alone), six on `EmojiService` (empty-guild upload, existing-name skip, slot-limit stop, static-
only counting, a `Forbidden` recorded not raised, the packaged pack non-empty), eight on the new/
polished moderation embeds. ruff and mypy clean across 126 source files. No migration — this round
touches no database schema.

**Needs `/setup run`** to reconcile the new Ally read-only overwrites onto THE NEST/BRAWLHALLA/VOICE,
and `/emoji sync` to actually upload the pack once the bot is in the server.

## ADR-091 — Guest gets one channel, approval grants full access, and the redesigned arrival cards

Follow-up to ADR-090, same session. Two corrections plus a template swap:

1. **Guest's visible surface shrinks to one channel.** Before this round, SHAHEEN HQ (announcements/
   welcome/rules/apply/roles/clan-info/suggestions) was deliberately ungated — ADR-069's own
   rationale was "a brand-new Guest needs somewhere to read the rules before they can be verified."
   The owner overrode that explicitly: a new member should see `#apply` and nothing else until
   they're actually let in. `#apply` moves into a new, minimal, still-ungated category (`🦅 START
   HERE`); SHAHEEN HQ gains `gated=True` and keeps everything else. ADR-069's rationale is
   superseded, not the mechanism — `CategorySpec.gated` still does exactly what it did.

2. **Approval grants full read+write, not read-only.** ADR-090 built a three-tier model — Guest sees
   HQ, Ally can view the gated categories but not type, Trial Shaheen+ can type — based on a literal
   reading of "read only" in the request that started that round. The very next message contradicted
   it ("he/she will be able to see message history of most channels, send message" right after a
   moderator verifies them), so this went back to the owner via `AskUserQuestion` rather than
   guessing: **full participation from the moment of approval**, confirmed. "Read-only" was never
   about Ally at all — it's specifically about `#hall-of-fame`/`#leaderboard`, which should stay
   read-only for *everyone*, staff included, because they're bot-broadcast channels where a human
   typing was never the point.

   This reverts `FULL_MEMBER_ROLES`' channel-permission role (it's kept, narrowed to what it's
   actually still used for — `LinkCog._maybe_promote`'s "already Trial or above" check, unrelated to
   channel access) and `_apply_membership_tier` in favor of a new `CategorySpec.readonly` flag,
   meaningful only combined with `gated=True`: every `VERIFIED_ROLE`, not just Ally, gets
   `send_messages=False`/`speak=False`. A new `🏆 HALL OF RECORDS` category (`gated=True,
   readonly=True`) holds `#leaderboard` and `#hall-of-fame`, split out of SHAHEEN ARENA, which keeps
   `restricted=True` for `#scrims`/`#tournaments` — that half of ADR-090's read-only concept was
   right, it was just scoped to the wrong role. ADR-090's *other* fix — `/link` requiring Ally before
   promoting to Trial Shaheen, which closed the real hole where anyone could skip `/apply` by linking
   first — is untouched; it was never about read-only, it was about who gets let in at all.

3. **A planner gap this surfaced.** Moving `#leaderboard`/`#hall-of-fame` to a new category exposed
   that `setup_planner.py` never compared a channel's *live* category against its *configured* one —
   `_channel_diffs` checked name/kind/topic, never category membership. On an already-provisioned
   guild, `/setup run` would have found these two channels by their stored IDs, seen no diff, and
   left them parented under the old SHAHEEN ARENA forever — silently defeating the whole point of
   this category split. `_plan_channel` now takes the target category's resolved live ID (`None`
   when that category is itself being created this run — nothing to compare against yet, and the
   channel gets correctly parented via its own CREATE path) and flags a diff when the channel's
   `live.category_id` doesn't match; `_apply_channels`' repair path now passes `category=category` on
   every edit, so a detected mismatch actually reparents the channel instead of just being reported.

4. **Redesigned welcome/goodbye cards.** The owner supplied a finished composite (Brawlhalla legend
   art, an empty username pill, an Urdu tagline, four labeled icon columns) to replace the existing
   templates — split into two 768×1024 PNGs the same way the previous templates were ("owner-
   supplied, split from one side-by-side composite," per `image_service.py`'s own docstring; nothing
   new about the pattern, just new art). The username — the one thing this module renders
   dynamically here — moves from Orbitron Bold to Rajdhani SemiBold (already bundled, matching the
   owner's spec), while `render_milestone_card`'s achievement headline stays on Orbitron; different
   function, different template. The small-label typography (Montserrat/Inter) and the Urdu tagline
   the owner also specified are already baked into the supplied artwork as static pixels, the same
   way the achievement template's own corner Urdu already was (ADR-062's docstring: "No Urdu is
   rendered dynamically... baked into the template's own corner artwork") — no font-loading code
   needed for those, and none was added.

Files: `src/bot/constants.py` (`CategorySpec.readonly`, new `category:start_here`/
`category:hall_of_records`, `category:shaheen_hq` gated, `FULL_MEMBER_ROLES` narrowed to its rank-
only purpose), `src/services/setup_service.py` (`_apply_readonly_gate` replacing
`_apply_membership_tier`), `src/services/setup_planner.py` (category-reparenting diff),
`src/services/image_service.py` (new template dimensions/cutout box, Rajdhani for the username),
`src/assets/img/{welcome,goodbye}_template.png` (replaced), `docs/{PERMISSIONS,DISCORD_SPEC,
ROADMAP}.md`, `tests/{test_setup_service,test_setup_planner,test_image_service}.py`, this entry.

Verified: `test_setup_service.py`'s ADR-090 read-only tests replaced with tests for the reverted
default (plain gated grants no participation overwrite at all) and the new `readonly` gate (denies
every VERIFIED_ROLE, staff included, on both text and voice); three new `test_setup_planner.py`
tests cover the reparenting diff (flagged when a channel's live category disagrees, not flagged when
it already matches or when its category is itself brand new this run); five new
`test_image_service.py` tests render both cards at the new 768×1024 size, including a very long and
an empty member name, plus confirm the new templates ship inside `src/`. A local render smoke test
(both cards, a long and a short username) confirmed the recalibrated cutout box centers text
correctly before committing the coordinates. 407 passing (was 402), ruff and mypy clean across 126
source files. No migration — this round touches no database schema.

**Needs `/setup run`** to gate SHAHEEN HQ, create `🦅 START HERE`/`🏆 HALL OF RECORDS`, and reparent
`#leaderboard`/`#hall-of-fame` off of SHAHEEN ARENA.

## ADR-092 — /apply and /verify stop doing the same thing; an interactive emoji picker

Two independent asks, same round.

1. **`/apply` and `/verify` produced the same outcome.** Both ended in `grant_member_access` — Guest
   → Ally — so filling out the five-field application form (Brawlhalla ID, region, rank, "why
   Shaheen", referrer) got a member exactly as far as a moderator just running `/verify` on them with
   no form at all. The owner wanted these genuinely separated: `/apply` is applying **to the clan
   roster**, not asking to hang out, and an approved application should promote straight to **Trial
   Shaheen**, skipping Ally entirely — the applicant already went through real screening. `/verify`
   is unchanged: the lightweight staff action that grants general community access (Ally) with no
   form, for people who want to be part of the server without trying out for the roster. Confirmed
   via `AskUserQuestion` against the alternative of redefining `/verify` itself — the owner picked
   "Trial Shaheen directly," leaving `/verify` exactly as it was.

   `bot/membership.py` gains `is_already_a_clan_member` (True for `FULL_MEMBER_ROLES` — Trial
   Shaheen and up) as the new gate on `/apply`, replacing the old `is_already_verified` check there;
   an Ally let in via `/verify` can still apply for the roster, since Ally isn't clan membership.
   `is_already_verified` itself is untouched and still gates nothing but its own callers. A new
   `grant_clan_membership` mirrors `grant_member_access`'s shape — removes Guest and/or Ally,
   whichever is held, adds Trial Shaheen — and raises the same `ShaheenError` if Trial Shaheen isn't
   provisioned yet. `bot/views/application.py` and `bot/cogs/application.py` call the new gate/grant
   pair; the decline branch is untouched, it never touched roles. Copy in
   `bot/content/application_embeds.py` (`/apply`'s panel and the approval DM) and
   `bot/content/moderation_embeds.py`/`bot/cogs/moderation.py` (`/verify`'s description and its own
   DM/success embeds) now says which outcome each path leads to, so the distinction is visible in
   `/help` and in what a member actually receives, not just in the role that lands.

2. **A new zip of legend art plus a request for an in-bot picker.** The owner uploaded
   `shaheen_emoji_transparent_pack.zip` — 20 per-legend PNGs, transparent background — and asked for
   a UI to pick which crops to upload instead of the fixed 24-emoji pack ADR-090 shipped. Inspected
   the zip first: it's low-resolution (~380×180px) packed thumbnail exports, not a clean grid — faces
   overlap tightly with decoration fragments between them, not separate cells. Column-gap
   segmentation and alpha-based connected-component blob detection (with dilation to merge a face
   with its nearby decoration) were both tried and both failed to reliably isolate individual icons —
   blobs either fragmented one face into pieces or merged two or three faces into one box, confirmed
   visually. This material isn't suitable for automated per-icon cropping, so it isn't the picker's
   source. Instead, the picker draws from the **original two high-resolution sprite sheets** already
   in the repo's history (the same source ADR-090's curated 24 came from) — the crop geometry for
   both was already validated, so a full bulk export was safe: every cell, not just the curated 24,
   ~260 crops across the 16 legends the sheets actually contain, checked into
   `src/assets/emoji_candidates/<legend>/expr_NN.png` as plain files, same pattern as the existing
   pack. Three block/row combinations (nix's two rows, wu_shang's second row) needed their own crop
   window rather than the shared default — caught by spot-checking contact sheets of the bulk output,
   not flagged by the owner, and re-cropped individually before committing. The zip's 12 legends that
   aren't in those two sheets (artemis, lucien, mordex, orion, petra, rayman, scarlet, sentinel,
   tezca, thatch, val, vector) are **not** in the candidate pool — stated here rather than silently
   dropped; cleaner individual source art for them would slot into the same pool later with no design
   change.

   `services/emoji_service.py` gains `candidate_legends()`/`candidate_files(legend)` (pure listing
   functions, same shape as the existing `available_emoji_files()`) and `sync()` grows an optional
   `files: Sequence[tuple[str, Path]] | None` parameter — explicit `(emoji_name, path)` pairs to
   upload instead of the default curated pack. `/emoji sync` (`files=None`) is unchanged.
   `bot/views/emoji_picker.py` is new: `EmojiBrowseView` opens on a `discord.ui.Select` of the 16
   legends (well under Discord's 25-option cap), then an icon browser (◀ Prev / ▶ Next / ➕ Add /
   🔁 Legends / ✅ Done) once one's picked, rendering the current crop as the embed's image via
   `discord.File` + `attachment://`. ➕ Add opens a one-field modal pre-filled with a proposed
   `legend_NN` name so a staff member can rename before it's queued; ✅ Done calls
   `EmojiService(guild).sync(files=view.queue)` and shows the existing sync-report embed. Unlike
   `bot/views/application.py`'s `PersistentView` pieces, this is session-lived — bounded timeout, no
   custom_id routing, never re-registered across restarts, matching `ConfirmView`'s existing pattern
   rather than the persistent one. `bot/cogs/emoji.py` gets a new `/emoji browse` (staff-only)
   opening it; `/emoji sync` is unchanged.

Files: `src/bot/membership.py`, `src/bot/views/application.py`, `src/bot/cogs/application.py`,
`src/bot/content/application_embeds.py`, `src/bot/cogs/moderation.py`,
`src/bot/content/moderation_embeds.py`, `src/services/emoji_service.py`,
`src/bot/views/emoji_picker.py` (new), `src/bot/content/emoji_embeds.py`, `src/bot/cogs/emoji.py`,
`src/bot/content/help_embeds.py`, `src/assets/emoji_candidates/` (new, ~260 files),
`docs/{PERMISSIONS,COMMANDS,ROADMAP}.md`, `tests/test_membership.py` (new),
`tests/test_emoji_service.py`, `tests/test_emoji_embeds.py` (new), this entry.

Verified: new `tests/test_membership.py` covers `is_already_a_clan_member` (false for Guest/Ally,
true for Trial/Elite) and `grant_clan_membership` (Guest→Trial, Ally→Trial removing only Ally, raises
when Trial Shaheen isn't provisioned, wraps `Forbidden`), plus regression coverage that
`grant_member_access` still only ever grants Ally. `tests/test_emoji_service.py` extended with
`candidate_legends()`/`candidate_files()` against the real checked-in pool and `sync(files=...)`
coverage (uploads exactly the given pairs, still respects the existing-name skip and slot-limit
guards, ignores the curated pack entirely when `files` is passed, no-ops on an empty list).
`tests/test_emoji_embeds.py` is new, covering the browse-intro and per-candidate preview embeds.
`tests/test_help_embeds.py`'s catalog/command-tree parity test required adding `/emoji browse`'s
entry. 431 passing (was 407), ruff and mypy clean. No migration — no database schema touched.

**No `/setup run` needed** — this round touches no channel/category structure.

## ADR-093 — recropping the emoji candidate pool: connected components, not a fixed grid

Follow-up to ADR-092, same session, reported directly by the owner: several of the ~260 candidate
crops showed **two character faces in one image** — most visibly `nix`'s first candidate, which
included a claw-shaped tendril from the neighboring legend portrait alongside the actual face.

Root cause: the original bulk crop used a purely geometric grid (a fixed `LEFT`/column-width/
row-height per sprite sheet, carried over from the 24-emoji curated pack's manually-verified
coordinates) and simply sliced pixels at those coordinates. That geometry was accurate for *where a
cell's label sits*, but the character art itself doesn't respect cell boundaries — wide hair, hoods,
and held weapons routinely spill into a neighboring cell's rectangle, and the four two-row legends
(`koji`/`hattori`/`wu_shang`/`nix`) each sit directly right of a full character **portrait** whose
own hair/tendril art can bleed into column 0's crop window. `nix`'s hood tendril was the worst case,
but not unique — inspection turned up bleed at multiple points across all four two-row legends.

Fix: rebuilt the entire pool from the same two source sheets using **alpha-channel connected-
component segmentation** instead of fixed-pixel slicing:

1. For each nominal cell (legend, row, column), label connected components (`scipy.ndimage.label`,
   8-connectivity) *within a horizontal band strictly bounding that row* — never across the whole
   sheet. This was necessary in its own right: an early version that labeled the full image (or too
   generous a row band) let faces merge **vertically across unrelated rows** where two legends'
   hair happened to touch with no transparent gap between them (`sheet2`'s column 0 was one single
   component spanning three legends' rows before this fix), and separately let a row's own label-
   text pill get pulled into the same component as the face above it when the row band was too
   tall.
2. Within that band, pick the largest component whose centroid falls near the cell's nominal x
   position — this is what actually excludes a neighbor's disconnected bleed (like the portrait
   tendril): unrelated art has its own separate component and simply isn't the biggest thing near
   this cell's center.
3. When the closest match is implausibly wide (still merged with a neighbor — two touching faces'
   hair, no true gap between them) or nothing matches at all, fall back to the largest component
   found strictly *within* the nominal cell's rectangle — never the raw union bounding box of
   everything in that rectangle, which first attempt showed still stitches together a sliver of one
   neighbor with the real content into a single distorted crop.

`src/assets/emoji_candidates/` (all 260 files) was regenerated with this method and re-verified via
full per-legend contact sheets (all 16 legends, every candidate, eyeballed at 90×90 in a grid) before
replacing the shipped pool — the `nix` tendril is gone, no crop merges two characters, and the small
number of genuinely awkward source frames left (e.g. `wu_shang`'s duplicated "spirit transformation"
slot, which is a stylised aura shape even in the original sheet) are exactly what the picker's
"browse and choose" design was already built to tolerate, per ADR-092's plan. No code changed —
`services/emoji_service.py`'s `candidate_legends()`/`candidate_files()` and
`bot/views/emoji_picker.py` are indifferent to how the files were produced. The one-off segmentation
script itself lives outside `src/` (in this session's scratch space, not committed) — same posture
as the original bulk-crop pass: a one-time data-generation tool, not application code.

Verified: full `pytest` still 431 passing (the candidate-pool tests assert file counts and directory
shape, not pixel content, so they were unaffected), ruff and mypy clean. No migration.

## ADR-094 — `/emoji clear`: delete every custom emoji, admin-gated

"Clean all emojis" — confirmed via `AskUserQuestion` to mean literally every custom emoji in the
guild, not just the Shaheen pack, since that's what "clean all" says. That's more destructive than
anything `/emoji` has done before: it can remove something a staff member hand-added that the bot
never uploaded and has no way to restore. Two consequences follow directly from that:

1. **Gated by `require_setup_authorized()`** (Leader/admin only, same as `/setup reset`) — not
   `require_staff_authorized()` (Leader or Moderator) that `/emoji sync`/`browse` use. Deliberate
   deviation: "upload from a curated pack" and "delete everything, including things you didn't
   upload" don't belong at the same permission tier.
2. **Two-step confirm, not a single `ConfirmView` round-trip.** Reuses `/setup reset`'s exact
   pattern (`_ResetWarningView` → a modal requiring a typed phrase, docs/DECISIONS.md ADR-060) rather
   than the lighter single-click confirm `/kick`/`/ban` use — `_EmojiClearWarningView` →
   `_EmojiClearConfirmModal` (type `"DELETE ALL EMOJI"`), in `bot/cogs/emoji.py`.

`services/emoji_service.py` gains `EmojiClearReport` (`deleted`, `errors`, `.total` — same shape as
`EmojiSyncReport`) and `EmojiService.clear()`, the one method on this class that's an explicit
exception to its own "never deletes or replaces an existing emoji" rule. Iterates `guild.emojis`,
`await emoji.delete(...)` per item, catching `Forbidden`/`HTTPException` per-emoji into `errors`
rather than aborting the batch — same resilience posture `sync()` already has for uploads.
`bot/content/emoji_embeds.py` gains `build_emoji_clear_warning_embed()` (explicit "this deletes
everything, not just the pack" copy, danger-colored) and `build_emoji_clear_report_embed(report)`.

Files: `src/services/emoji_service.py`, `src/bot/cogs/emoji.py`, `src/bot/content/emoji_embeds.py`,
`src/bot/content/help_embeds.py` (new catalog entry — required by the existing command-tree parity
test), `docs/{COMMANDS,ROADMAP}.md`, `tests/{test_emoji_service,test_emoji_embeds}.py`.

Verified: `clear()` deletes every emoji regardless of name/origin and reports names; collects
`Forbidden` per-item without aborting the batch; no-ops on an empty guild. New embed tests for the
warning/report pair. No cog-level test (matches this repo's existing posture). Full suite green, no
migration.

## ADR-095 — Music Library page: two new anthem tracks, an audio-reactive visualizer

Owner uploaded two full-length Suno-generated anthem tracks (`anthem_1.mp3` — "anthem", 4:48; and a
track titled "بلندیوں کی جانب" — the site's own tagline, 4:37), distinct from the short clip already
autoplaying sitewide (`assets/audio/anthem.mp3`, "آسمان ہمارا", ADR-073) — three versions now exist.
Confirmed via `AskUserQuestion`: **sitewide background audio is untouched** — the short anthem keeps
autoplaying everywhere; the two new tracks live only on a new `web/music.html` page where a visitor
explicitly presses play. No changes to `assets/js/audio.js` or ADR-073's behavior.

New assets, checked in as plain files matching the existing `assets/audio/anthem.mp3` convention:
`assets/audio/anthem-full.mp3`, `assets/audio/bulandiyon-ki-janab.mp3`, and their embedded cover art
(small Suno-generated stock photos) at `assets/img/music/*.jpg`, used as track-card thumbnails — the
page's primary visual stays on-brand using the site's own logo/eagle imagery, not these.

**The animation is a live audio-reactive visualizer**, not a decorative scroll effect — Web Audio
API `AnalyserNode` fed by `createMediaElementSource` on the one `<audio>` element, drawn as frequency
bars on a `<canvas>` inside a "Now Playing" panel (green→gold gradient, matching `--green`/`--gold`).
The track's cover art sits in a circular disc that rotates via CSS animation only while playing
(`.is-playing` toggles `animation-play-state`). Under `prefers-reduced-motion`: the disc doesn't spin
(new rule in the existing global override block) and the JS draw loop never starts — a single static
bar pattern renders once instead, same guard pattern `spotlight.js`/`pillar-scroll.js` already use.

Playback is **user-initiated** (press play on a track card), so none of ADR-073's autoplay-block
workaround applies here. One courtesy taken from it anyway: starting a library track pauses the
sitewide `#site-audio` element if it's playing, so two anthems never overlap — implemented by
watching `#site-audio`'s own `play` event (not just a one-time pause-on-click), because
`assets/js/audio.js` can still be waiting on its own DOMContentLoaded-deferred init when this script
runs (both are plain `<script>` tags near the end of `<body>`) and can independently start playback
via its own document-level interaction fallback right after this page's own click handler runs.

New `web/assets/js/pages/music.js` (self-contained IIFE, matches `pages/achievements.js`'s shape):
owns the one `<audio>` element (appended to `<body>`, same as `audio.js`'s own element), the
`AudioContext`/`AnalyserNode`, play/pause/seek/volume wiring, the rAF draw loop, and active-track-card
state. New CSS section in `style.css` (`.music-now-playing`, `.music-disc`, `.music-visualizer`,
`.music-tracks`, `.music-track-card`, progress/volume controls) reusing existing tokens
(`--card-bg`/`--card-border`/`--cut`/`--green`/`--gold`) — no new stylesheet.

Nav: `<a href="music.html">Music</a>` added between Roster and Achievements across all 12 HTML pages
(the same manual, mechanical edit ADR-073 already describes for its own `<script>` tag).

Files: `web/music.html` (new), `web/assets/js/pages/music.js` (new), `web/assets/audio/*.mp3` (new),
`web/assets/img/music/*.jpg` (new), `web/assets/css/style.css`, all 12 `web/*.html` (nav link),
`docs/ROADMAP.md`.

Verified: no build step or JS test runner exists for `web/` (confirmed). A Playwright smoke pass
against a local static server: pressing play actually plays the `<audio>` element and draws non-blank
canvas frames; clicking pause stops it; switching tracks swaps the `src`; the sitewide `#site-audio`
correctly pauses the moment a library track starts, including the race where its own interaction
fallback fires after this page's click handler; `prefers-reduced-motion` freezes the disc and skips
the draw loop while still showing static bars; no horizontal overflow at a 375px viewport; no console
errors. No migration — purely static.

## ADR-096 — A richer /profile: favourite Legend, derived playstyle, and a redesigned player page

Owner uploaded `SHAHEEN_PROFILE_CARD_IMPLEMENTATION_KIT.zip` — a design reference (a polished mockup
PNG plus a bare HTML/CSS/JS skeleton showing the intended field list, not production code) for a
dark-navy/gold profile card: username/handle/avatar, country, server level/XP, messages, matches,
events, day streak, favourite Legends, Brawlhalla rank/ELO, playstyle tags, achievements, clan role,
joined date, and Discord account age.

Confirmed via `AskUserQuestion`:
- **Target: the website now; a Discord-native image is scoped for later, not built.** The kit is
  literal HTML/CSS/JS — the same tech as `web/`, not something Discord can render natively (no
  headless-browser pipeline exists; `services/image_service.py`'s Pillow renderer only composites 1-2
  short strings into an owner-drawn template today, nowhere near a 10+ field multi-panel card). A
  true Discord-native version needs new background art plus a real layout engine — real, separate
  work for a future round, not attempted here.
- **Country flag and day streak: dropped.** Neither exists in Shaheen's data — only a Brawlhalla API
  *region*, not a country; no streak concept anywhere in the schema (confirmed via full-repo grep).
- **Events-attended: also dropped** — currently only a one-shot flag passed at achievement-award
  time, not a running counter; left alone rather than reverse-engineering one.
- **Playstyle tags: derived from real per-Legend stats** — not stored today, and not literal
  Brawlhalla data either (their API reports no such field).

**`services/playstyle.py`** (new): `derive_playstyle_tags(legends) -> list[str]`, a pure function
shared by both surfaces below. Aggregates KOs/damage/falls across every played Legend into per-game
rates and returns 1-3 tags crossing fixed, hand-picked thresholds (`Aggressive`, `Heavy Hitter`,
`Survivor`; `Well-Rounded` fallback). Documented in its own docstring as a labeled heuristic, not a
Brawlhalla-reported stat — both call sites repeat that framing rather than presenting it as fact.

**`/profile` embed** (`bot/content/profile_embeds.py`/`bot/cogs/profile.py`) gains: Favourite Legend
(top of `stats.legends` by games — same sort `/legends` already uses), Playstyle (the derived tags),
an `Achievements (N/{total})` fraction (imports `CATALOG` from `services/achievements.py` instead of
a bare count), Clan Role (`member.top_role`, excluding `@everyone`), and a combined Discord field
(`member.created_at` account age + `member.joined_at` this-guild date) — the two Discord-native dates
from the kit's list that the database doesn't and structurally can't store (nothing else here
persists per-member Discord timestamps; `GuildSnapshot` is deliberately guild-aggregate-only,
ADR-040), so they're read live from the cog's already-held `discord.Member` instead.

**`web/player.html`** is reskinned in the kit's visual language, not rebuilt — same Brawlhalla-ID-
keyed URL, same API calls, restructured markup in `web/assets/js/pages/player.js`: a Cinzel-accented
name heading (one page's own display-font register, precedented by `landing.html`'s own Cormorant
Garamond pairing, ADR-066/078), a Playstyle tag row, and a Favourite Legends strip (top 5, reusing the
already-fetched `/legends` payload — no new request) that degrades to an initial-avatar chip for any
Legend without real cutout art (`theme.js`'s `LEGEND_ICONS` set covers only 5 of the roster today).
`PlayerProfileResponse` (`src/api/schemas.py`) gains `playstyle_tags: list[str]`; `WebsiteService`'s
`PlayerProfile` gains a `legends` field (unsliced, unlike the separate `/legends` endpoint's top-N
view) and a `playstyle_tags` property calling the same `derive_playstyle_tags` — one heuristic,
computed once, shared by Discord and the website rather than reimplemented in JS.

**Deliberately not added to the public website**: Discord username/handle/avatar, message count, chat
level/XP, clan role. `services/website_service.py`'s existing boundary (ADR-040: "public identity is
Brawlhalla identity, never Discord identity") stays intact — the site has no Discord API access at
request time regardless, and a public, unauthenticated Discord-identity-to-stats mapping was a
deliberate earlier decision, not a gap this round should quietly reverse.

Files: `src/services/playstyle.py` (new), `src/bot/content/profile_embeds.py`, `src/bot/cogs/
profile.py`, `src/services/website_service.py`, `src/api/schemas.py`, `src/api/routers/players.py`,
`web/player.html`, `web/assets/js/pages/player.js`, `web/assets/js/theme.js`,
`web/assets/css/style.css`, `docs/{COMMANDS,ROADMAP}.md`, `tests/{test_playstyle,
test_profile_embeds,test_website_service,test_api}.py`.

Verified: new `tests/test_playstyle.py` covers every tag's threshold plus the zero-games/empty-list
fallback. `tests/test_profile_embeds.py` extended for all five new embed fields (favourite Legend,
playstyle, the achievement fraction, clan role present/absent, Discord dates present/absent).
`tests/test_website_service.py`/`test_api.py` extended for `playstyle_tags` (both a real derived tag
from seeded Legend snapshots, and the no-snapshots fallback through the live API). A Playwright smoke
pass against a local static server with the live API mocked: the Cinzel heading actually wins the CSS
cascade (an earlier `.player-card-name`-alone rule lost to `.profile-head h2`'s higher specificity —
fixed by matching it with `h2.player-card-name`), playstyle tags and favourite-Legend chips render
correctly, a Legend with real art uses it, no console errors, no mobile overflow. Full suite (453
tests) green, ruff and mypy clean. No migration — `PlayerProfile.legends` is an in-memory dataclass
field, not a new column.

**Scoped for a future round, not built now**: a Discord-native image version of this card — needs new
background artwork (the kit's `reference.png` is a mockup for direction only, its Legend SVGs
explicit swap-out stubs) and a real multi-panel layout engine in `image_service.py` (avatar
compositing, a stat grid, icon tiles — none of which the current single-template-string renderer
does). Would reuse `derive_playstyle_tags` and the same field set assembled for the embed above.

## ADR-097 — Rising Shaheen, Core Member, a meetings voice channel, and /anthem

Four of the five prior round's advisory suggestions, built this round (the fifth — timezone-aware
scrim scheduling/reminders and voice-activity XP tracking — is real, separate scope: a new data model
plus a background job for the former, extending `services/chat_gamification.py` and
`bot/cogs/engagement.py`'s message-only XP system to also listen for voice-state events for the
latter. Left for a future round rather than folded in here alongside four smaller, well-scoped items).

**Rising Shaheen — a role for sub-Gold ranked members.** `services/rank_roles.py`'s rank-role mapping
only ever covered Gold and up (ADR-087, deliberate — a wall of low-tier roles is discouraging). That
left a real gap: a brand-new ranked player earns no rank tag at all until they climb to Gold, which
can be a while. Rather than adding a role per tier (four more roles) or leaving the gap, Tin/Bronze/
Silver now collapse into one combined `🌱 Rising Shaheen` role — the one rank tag a new member can
actually earn on day one. `bot/constants.py` gains `ROLE_RANK_RISING`, prepended to `RANK_ROLES`
(lowest tier first); `services/rank_roles.py`'s `_TIER_INDEX_TO_ROLE_KEY` maps tier indices 0-2 to it.
No other code changes — `bot/cogs/clan.py`'s `_sync_rank_roles` and `plan_rank_roles`'s revoke/grant
diffing already iterate `RANK_ROLES` generically.

**Core Member — a role for high chat-level members.** Brawlhalla rank has cosmetic recognition (the
roles above); chat leveling (`/level`) had none beyond `/chatboard` and the weekly MVP rotation.
`services/chat_gamification.py` gains `CORE_MEMBER_MIN_LEVEL = 15` and a pure
`earns_core_member_role(level) -> bool` — level 15 ("Veteran") is `RANK_TITLES`' 4th of 7 tiers, the
same relative position Brawlhalla rank roles start rewarding from (Gold is the 4th of 8 Brawlhalla
tiers). `bot/constants.py` gains `ROLE_CORE_MEMBER` (`🔥 Core Member`), not part of the rank ladder or
`VERIFIED_ROLES` — same posture as `ROLE_MVP`. `bot/cogs/engagement.py`'s `on_message` level-up path
calls a new `_maybe_assign_core_member_role` (mirrors `_assign_guest_role`'s shape: best-effort,
missing role/permission logged and skipped) whenever a level-up crosses the threshold. Granted once,
never revoked — chat XP is strictly cumulative, so there is nothing to demote from. Like rank-role
sync, this only fires on the events that already touch a member (here, a level-up message) — there is
no periodic backfill loop, so a member who was already past level 15 before the role existed only
picks it up on their next level-up. Acceptable and disclosed rather than building a sweep job for it.

**A voice channel for clan meetings, AMAs, and tournament casting.** The 4 channels in `category:voice`
were all general/gaming-purpose — nowhere set aside for that kind of event. `bot/constants.py` adds
`channel:voice_meetings` (`🗣️-meetings-and-amas`) to `category:voice`. **Deliberately a plain voice
channel, not a true Discord Stage channel** — a Stage channel is a distinct type discord.py exposes
separately from `VoiceChannel` (`discord.StageChannel`), and `ChannelKind`/`services/setup_planner.py`/
`services/setup_service.py` assume exactly two channel kinds throughout (`_create_channel`'s branch,
`build_snapshot`'s `isinstance(chan, discord.TextChannel)` check, several `discord.TextChannel |
discord.VoiceChannel` type unions). Plumbing a third kind through all of that is real, separate scope
of its own, not a "low-cost addition" once actually attempted — a plain voice channel gets the same
practical outcome (a dedicated space to talk) without it.

**`/anthem` — the one concrete Discord-to-website link from the Music Library round (ADR-095).**
`bot/content/engagement_embeds.py` gains `build_anthem_embed`, linking to `music.html`; `bot/cogs/
engagement.py` gains a new `/anthem` command (no permission check, ephemeral — same "any read-only
command" posture as `/help`/`/level`/`/chatboard`). Reuses the same GitHub Pages base-URL constant
pattern `bot/content/profile_embeds.py` already established (`_WEBSITE_BASE_URL`, duplicated rather
than extracted to a shared setting — same reasoning as there: no `WEBSITE_URL` setting exists yet,
worth promoting to one if a third use turns up).

Files: `src/bot/constants.py`, `src/services/rank_roles.py`, `src/services/chat_gamification.py`,
`src/bot/cogs/engagement.py`, `src/bot/content/engagement_embeds.py`, `src/bot/content/
help_embeds.py`, `tests/{test_rank_roles,test_chat_gamification,test_engagement_embeds}.py`, `docs/
{COMMANDS,PERMISSIONS,DISCORD_SPEC,ROADMAP}.md`.

Verified: `tests/test_rank_roles.py` updated for the Tin/Bronze/Silver → Rising Shaheen mapping (was
"earns nothing"), plus `ALL_RANK_ROLE_KEYS` coverage. `tests/test_chat_gamification.py` extended for
`earns_core_member_role` at/above/below the threshold. `tests/test_engagement_embeds.py` extended for
the anthem embed's link. No cog-level test for the role-assignment wiring itself — matches this
repo's existing posture (`_assign_guest_role` isn't cog-tested either; only the pure logic and embeds
underneath are). Full suite (456 tests) green, ruff and mypy clean. No migration — no new database
columns, only new `ProvisionedResource` rows created the normal way by `/setup run`.

**Not deployed by this round.** `/setup run` is a live Discord command gated by
`require_setup_authorized()`; provisioning the two new roles and the new voice channel against the
real Shaheen guild, and deploying the updated bot code to the Fly.io app this repo already documents
(`fly.toml`, README "Deploying to production"), both require the owner's own Discord/Fly.io
credentials — outside what a coding session against this repository can trigger. Both steps are
exactly what the existing `flyctl deploy` + `/setup run` workflow already covers once this round's
code is merged; nothing new is required beyond running them.

## ADR-098 — Legend portraits from the owner's roster sheet, on Discord and the website

The owner supplied a 65-Legend roster sheet (13×5 framed portraits, each with a baked-in name label)
and asked for it to be used on both the bot and the website. Until now only 5 Legends had any art
(`web/assets/img/legends/`, the landing-page cutouts from ADR-078), so every favourite-Legend chip and
mastery row for anyone else fell back to an initial avatar, and the bot showed no Legend art at all.

**Assets.** Each card was cropped just inside its gold frame (the frame stroke is located per card,
with any faint stretch filled from its row/column median — the sheet is AI-drawn, so the grid isn't
perfectly regular), which also drops the painted-in name label, then normalised to 104×132. They ship
twice, once per deploy target: `src/assets/legends/<key>.png` for the bot (inside `src/`, which the
Dockerfile already copies) and `web/assets/img/legend-portraits/<key>.webp` for GitHub Pages (~8 KB
each). `tests/test_legend_art.py` fails if the two rosters drift apart.

**Keys.** Files use the underscored form (`lord_vraxx`, `wu_shang`). The stored `legend_name_key` is
whatever the Brawlhalla API sent, and its multi-word shape isn't pinned down anywhere in this repo
(fixtures only use single words), so both surfaces normalise before lookup — lowercase, spaces/hyphens
to underscores, diacritics stripped (`Bödvar` -> `bodvar`): `services/legend_art.py`'s
`normalize_legend_key` and `theme.js`'s `normalizeLegendKey`. The two formerly duplicated
`_legend_display_name` helpers in `bot/content/{profile,clan}_embeds.py` now use the same normaliser,
so "lord vraxx" displays as "Lord Vraxx" either way.

**Sheet labels taken as intended, not literally.** Two labels are wrong on the sheet: the wolf card
reads "BARBARA" (no such Legend; Mordex has no other card, and the art is Mordex) and the hooded
scythe card reads "FADIN" (Fait). They're keyed `mordex` and `fait`. The sheet also includes a few
names this project can't confirm against the API (e.g. Rupture, Sandstorm, Ransom, Aurus, Lady Vera);
their files are harmless if the API never sends those keys.

**Discord.** An embed's thumbnail already holds the member's avatar, so rather than displacing it the
bot renders a strip — framed portraits side by side with names underneath — with Pillow
(`services/legend_art.py`'s `render_legend_strip`, Discord-agnostic like `image_service.py`) and
attaches it as the embed image: top 3 Legends on `/profile`, top 5 on `/legends`, the clan's top 5 on
`/legendmeta`. `bot/legend_art.py`'s `attach_legend_strip` renders off-thread and returns no file when
none of the Legends have art or rendering fails, so the embed goes out exactly as before in that case.

**Website.** `theme.js`'s `LEGEND_PORTRAITS` (all 65) replaces the 5-entry `LEGEND_ICONS`;
`legendAvatarHtml` serves the portrait, square-cropped on the face, and still falls back to the
initial avatar for anything missing. `player.html`'s favourite-Legend chips become portrait cards
(top 5, the first marked "Main"), and each row of the Legend mastery list gets its portrait.
The landing page's 5 cutouts (`assets/img/legends/`) are unchanged — they're full-body scene art, not
avatars.

Files: `src/assets/legends/*.png`, `web/assets/img/legend-portraits/*.webp` (new),
`src/services/legend_art.py`, `src/bot/legend_art.py` (new), `src/bot/cogs/{profile,clan}.py`,
`src/bot/content/{profile,clan}_embeds.py`, `web/assets/js/theme.js`, `web/assets/js/pages/player.js`,
`web/assets/css/style.css`, `docs/{COMMANDS,ROADMAP}.md`, `tests/test_legend_art.py` (new).

Verified: `tests/test_legend_art.py` covers key normalisation, portrait lookup hits and misses,
bot/web roster parity, and strip rendering (skipping Legends without art, `None` when none have it).
The strip itself was checked by eye. A Playwright pass on `player.html` with the API mocked, using
`mordex`, `lord vraxx`, `bödvar`, `wu_shang` and an unknown key: the four real ones load their
portraits in both the cards and the mastery list, the unknown one falls back to an initial, no console
errors, no horizontal overflow at 390px. Full suite green, ruff and mypy clean. No migration.

## ADR-099 — A Pakistan leaderboard beside the clan one, and one Rankings page

The owner asked for two boards: the clan's (fed by `/link`, unchanged) and one for Pakistan's
Brawlhalla scene, filled by a separate command — and for the site to reconcile its Leaderboard and
Roster pages accordingly. Confirmed via `AskUserQuestion`: members add themselves and staff can add
any Pakistani player (Discord member or not); clan members opt in with the same command rather than
being added automatically; one Rankings page with two tabs replaces Leaderboard + Roster.

**Its own table, not a flag on members.** `pakistan_board_entries` (migration 0011) references
`brawlhalla_players` directly, because the whole point of staff adds is players who were never Discord
members — a `ShaheenMember` column couldn't hold them. Soft-deleted via `removed_at` like
`member_player_links`, with a partial unique index for one active entry per player per guild.
`owner_discord_id` records a self-add, so `/pakistan leave` only ever removes your own entry and one
member can't take over another's; a staff-added entry with no owner is claimed by whoever later
`/pakistan join`s with that ID.

**Opt-in only.** The Brawlhalla API reports a server region ("SEA", "EU"), never a country, and nothing
else in Shaheen's data says where someone lives. The 🇵🇰 self-assign role was considered as an
automatic source for clan members and rejected by the owner in favour of the explicit command.

**Snapshots.** Snapshot rows already key on the player, not the member, so non-members fit the existing
tables. `SnapshotService.snapshot_player` is the rating + per-Legend write extracted from
`snapshot_member` (which now calls it); `run_for_guild` runs it for Pakistan entries not already covered
by a clan link that tick. Non-members get no achievements, rank roles or announcements — those are clan
features keyed to a `ShaheenMember`. `/pakistan join|add` takes an immediate snapshot, as `/link` does.

**A cap of 150 entries.** Each costs two Brawlhalla API calls per six-hourly tick on top of the clan's;
the cap keeps a staff bulk-add from eating the quota. Raise it deliberately if the scene outgrows it.

**Discord.** A new `/pakistan` group (`join`, `leave`, `leaderboard`; staff `add`, `remove`), reusing
`/link`'s resolver (`LinkService.resolve_candidate`, Steam64 or Brawlhalla ID) and `ConfirmView`.
`build_leaderboard_embed` gained `title`/`empty_hint`/`noun` so both boards share one builder; the
Pakistan board shows Brawlhalla names, with 🦅 on clan members.

**Website.** `GET /pakistan/leaderboard` (Brawlhalla identity only — the ADR-040 boundary holds; this
board holds non-members, which makes it stricter, not looser). `rankings.html` has two tabs, mirrored to
the URL hash so `rankings.html#pakistan` links straight to that board. The clan tab is built from the
existing `/roster` payload — already every linked member, rating-sorted, unplaced included — as a
podium, a ranked table, and a "Not placed this season" list: the old top-25 Leaderboard and the full
Roster were the same members viewed twice, now one list. `leaderboard.html`/`roster.html` are redirect
stubs so old links (including ones already shared) still land; the nav across every page says Rankings.
The `/leaderboard` and `/roster` endpoints stay — the home page and cold-start snapshots use them — and
the snapshot workflow also captures `/pakistan/leaderboard`.

Files: `src/database/models/pakistan_board_entry.py`, `alembic/versions/0011_pakistan_board.py`,
`src/database/repositories/pakistan_board_repository.py`, `src/services/pakistan_board_service.py`,
`src/bot/cogs/pakistan.py`, `src/api/routers/pakistan.py` (new); `src/services/snapshot_service.py`,
`src/bot/content/{clan,help}_embeds.py`, `src/bot/cogs/clan.py`, `src/bot/client.py`,
`src/api/{app,schemas}.py`, `web/rankings.html`, `web/assets/js/pages/rankings.js` (new),
`web/{leaderboard,roster}.html` (now redirects; their page scripts removed), `web/*.html` nav,
`web/assets/js/api.js`, `web/assets/css/style.css`, `.github/workflows/snapshot.yml`,
`docs/{COMMANDS,DATABASE,ROADMAP}.md`, `tests/test_pakistan_board_service.py` (new),
`tests/{test_snapshot_service,test_api,test_clan_embeds}.py`.

Verified: new service tests cover join, replacing your own entry, staff add of a non-member and a later
claim, ownership conflicts, leave/remove, the cap, and a season-scoped, rating-sorted leaderboard that
flags clan members. Snapshot tests: a Pakistan-only player gets rating rows but no achievements, tiers
or announcements, and a clan member who also joined is snapshotted once. API test for the endpoint,
including that no Discord identity leaks. Alembic round-trip passes. Playwright on `rankings.html` with
the API mocked, desktop and 390px: both tabs render, clicking and arrow keys switch tabs, `#pakistan`
deep-links, podium in 2·1·3 order, unplaced members listed, clan tags shown, both old URLs redirect, no
overflow, no console errors.

## ADR-100 — The Pakistan board as server promotion; whole-wing logo; who earned each achievement

**Promotion, not a gate.** The owner asked whether the Pakistan board could require joining the
Discord, then chose a middle ground: the board stays open (staff can still add players who aren't in
the server — that's what makes it the scene's board rather than a member list), but being in the server
visibly earns more. Nothing new is stored — "claimed" is the existing `owner_discord_id` from ADR-099,
set by `/pakistan join`. Unclaimed entries never expire; the owner declined that.

- **Website.** `/pakistan/leaderboard` rows gain `is_claimed` — a boolean only, never the owner's id
  (ADR-040). The Pakistan tab tags rows ✓ Verified or Unclaimed; unclaimed rows carry a "Claim this
  spot" link to the Discord invite, and a banner above the board explains the claim, the role and the
  weekly callout. The link reads `DISCORD_INVITE_URL` directly because `wireDiscordLink()` only fills
  `[data-discord-invite]` links present at page load, not rows rendered later.
- **🇵🇰 Pakistan Top 10 role** (`ROLE_PAKISTAN_TOP`, created by `/setup run`, cosmetic, no permissions).
  `PakistanBoardService.top_role_earners` takes the board's top 10 by current-season rating and returns
  the owners of the claimed rows. An unclaimed player keeps their place and simply earns nothing — the
  role isn't passed down to #11, since that would make the board's order mean different things in
  different places. Synced every snapshot tick after the rank roles (`_sync_pakistan_top_role`): add to
  earners who are in the guild, remove from holders who dropped out. Best-effort like the other system
  roles — a `Forbidden` is logged, not raised.
- **Weekly post in #pakistan-chat**, from the Sunday digest tick. `build_pakistan_weekly_embed` lists the
  top 10 with unclaimed rows marked, the week's biggest climbers (`PakistanBoardService.climbers`: the
  same first-vs-last rating diff over the last seven days the clan digest uses), and — only if any spot
  is unclaimed — how to claim one. Claimed climbers are pinged in the message content, since mentions
  inside an embed don't notify. Skipped when the board has no ranked rows.

**Logo.** The nav/footer mark (`logo-icon`, a 256px square) was a crop too tight for the crest's
spread wings, which were clipped at both sides — the "cropped" logo the owner reported. It's replaced by
`logo-emblem.png/.webp` (384×228), cut from `shaheen-lockup.png` with both wings whole and the wordmark
faded out at the bottom, and sized by height (`height: 32px; width: auto`) so the aspect ratio holds.
The same swap applies to the footer crest, the Rankings tab icon and the faint crest watermark on the
clan section. The web copies of `logo-icon.*` are removed (nothing referenced them); favicons stay
square and the bot keeps its own `src/assets/img/logo-icon.png`.

**Achievements gallery: who earned it.** `/achievements` entries gain `holders` — each holder's
Brawlhalla id, name and `earned_at`, earliest first (Brawlhalla identity only, ADR-040). Built in the same
per-member loop the gallery already ran (ADR-071), now reading `list_with_details` for the award time.
The page groups achievements by category with an "n/m unlocked" count per group, and each card shows
who got there first and when, up to six holder chips linking to their player pages, "+N more", or
"Nobody yet — be the first". The grid uses `auto-fill` so a one-achievement category keeps a normal
card instead of stretching the width of the page.

**Regional Force wording.** `region_top_100` is awarded when the snapshot's `region_rank` (from the
Brawlhalla API's `/player/{id}/ranked`, stored since ADR-081) is 1–100. That's the player's rank on their
Brawlhalla **server region's** 1v1 ladder (SEA, EU, US-E…) — Brawlhalla has no country data — so "top
100 of your region" read like a claim about Pakistan. Migration 0012 rewrites the stored description to
name the server region; the key, the rule and existing awards are unchanged.

Files: `src/services/pakistan_board_service.py`, `src/bot/constants.py`, `src/bot/cogs/clan.py`,
`src/bot/content/clan_embeds.py`, `src/services/website_service.py`, `src/services/achievements.py`,
`src/api/{schemas,routers/pakistan,routers/achievements}.py`,
`alembic/versions/0012_region_top_100_wording.py` (new), `web/assets/img/logo-emblem.{png,webp}` (new),
`web/*.html` (brand/footer marks), `web/rankings.html`, `web/assets/js/pages/{rankings,achievements}.js`,
`web/assets/css/style.css`, `README.md`, `docs/{COMMANDS,PERMISSIONS,ROADMAP}.md`, tests.

Verified: service tests for `is_claimed`, the role going only to claimed players inside the top places
(an unclaimed #1 earns nothing and nobody below the cut is promoted), and climbers ranked by in-window
gain; embed tests for the weekly post with and without unclaimed spots; API tests that `is_claimed` is
exposed without any Discord id and that gallery holders carry only Brawlhalla identity; gallery holders
ordered by award time. Full suite and the Alembic round-trip pass. Playwright with the API mocked,
1440px and 390px: the nav mark renders the emblem undistorted, Verified/Unclaimed tags and claim links on
the Pakistan tab point at the Discord invite, the achievements page shows category groups, first holder,
chips and "+N more", no horizontal overflow, no console errors.

## ADR-101 — An unplaced season reads as "no rating", not 0 / "None"

Brawlhalla's Season 41 ended on 23 September 2026. Right after the reset, the site's clan ladder showed
the owner at rank 1 with a rating of 0, peak 0 and a tier badge reading "None". For a player with no
placement games in the new season, `/player/{id}/ranked` answers **200** with `rating: 0`,
`peak_rating: 0`, `tier: "None"` and zero ranks. That is different from the 404 an account that never
played ranked gets, which we already handled. The zeros were stored verbatim and a 0 counted as a real
rating (`rating != null`).

**Normalize at the integration boundary.** `PlayerRankedResponse` and `RankedLegendStat` share a
`_RankedStanding` base whose validator turns an unplaced standing (tier `""`/`none`/`unranked`, or a
rating ≤ 0) into `rating = tier = None`, a peak ≤ 0 into `None`, and a global/region rank ≤ 0 into
`None`. A genuine peak survives even when the current rating is unplaced. Everything downstream already
treats `None` as unranked: the clan tab lists the player under "Not placed this season", rank roles
fail closed, achievements need `0 < region_rank`, and climbers skip missing ratings. Only the models
change (docs/BRAWLHALLA_API.md: API shape lives in the integration). Migration 0013 rewrites the rows
already stored the same way; it has no downgrade because the zeros carried no information.

**The Pakistan board lists placed players only.** It's a ranked board. After a reset, every entry reads
unplaced, and an unrated claimed entry must never fill a Top 10 slot and earn `ROLE_PAKISTAN_TOP` (ADR-100).
Unplaced entries stay on the board and reappear once they play placements.

**Season stamp.** `BRAWLHALLA_SEASON` (ADR-088) still has to be bumped by hand at each reset. It was
missing from the README's `flyctl secrets set` list, so a deploy that followed it stamped everything
season 1; it's listed there now with a note to bump it.

Files: `src/integrations/brawlhalla/models.py`, `src/services/pakistan_board_service.py`,
`alembic/versions/0013_unplaced_snapshots.py` (new), `web/assets/js/pages/rankings.js`, `README.md`,
`tests/test_brawlhalla_models.py`, `tests/test_pakistan_board_service.py`. Verified: model tests for the
post-reset payload (player and per-Legend) and for a real peak surviving an unplaced rating; a service
test that an unplaced entry is off the board and earns no role; full suite and Alembic round-trip pass.

## ADR-102 — Pakistan Seasons: named, badged, rotating every 13 weeks

The owner supplied a sheet of 13 season badges, each "Season of …" with an English and an Urdu name.
They asked for Shaheen's own seasons numbered 1, 2, 3… alongside Brawlhalla's. Their answers:
- Brawlhalla S42, which began on 23 September 2026, is **Pakistan Season 1**.
- Seasons rotate every 13 weeks, Brawlhalla's usual length; the details were left to us.
- The season shows on the website, in bot embeds, and as a season-start announcement.

**One pure module.** `services/seasons.py` holds the anchor (S42 at 2026-09-23 00:00 UTC), the 13-week
length and the 13 `(name, urdu)` pairs in badge order. Everything else asks it:
- `brawlhalla_season_at(now, override=)`: the season in progress;
- `pakistan_season(n)`: number, names, badge key and the 13-week window;
- `season_label(n)`: the single wording every Discord footer uses;
- `season_to_announce(current, last)`: whether to announce.

The API returns the names, so the website keeps no copy of the list.

**The season comes from the date, not a hand-set env var.** ADR-088 made `BRAWLHALLA_SEASON` a required
manual bump at each reset. Production never set it, so every rating row said "season 1". The bot now
stamps snapshots with `ShaheenBot.current_brawlhalla_season()`, derived from the calendar.
`BRAWLHALLA_SEASON` becomes an optional override for when Brawlhalla's real reset drifts from the
rhythm. It has to be unset again afterwards, or the season stops advancing, and README says so. The
13-week window is documented as approximate for the same reason. Brawlhalla's API never reports the
season, so the date plus an override is the most we can know.

**Numbering.**
- Pakistan numbers keep counting.
- Names and badges cycle after 13 (Season 14 is Zarb-e-Shaheen again, about 3¼ years out); a longer
  sheet extends the tuple.
- Seasons before S42 have no Pakistan season. They read "Brawlhalla Season 41" on Discord, and
  `pakistan_season` is null in the API.

**Restamping stored data (migration 0015).** Only `ranking_snapshots.season` is season-scoped. Legend
snapshots, achievements, matches, tournaments and Pakistan-board membership are all-time on purpose.
- Rows stamped with the default 1 become 41 if captured before the S42 anchor and 42 at or after it.
  Shaheen went live on about 7 September, inside S41.
- NULL-season rows are untouched.
- There's no downgrade: once new S42 rows exist they can't be told apart from restamped ones.

**Badges.** Cut from the uploaded sheet (1500×1000, transparent) by alpha connected components, each
assigned to its nearest badge. The number diamonds touch the badge above them tip to tip along one row,
so that row is split only for labelling; the output keeps every pixel.
- `web/assets/img/seasons/NN.{webp,png}` are 256px tall.
- `src/assets/img/seasons/NN.png` are the full crops for Discord, shipped by `COPY src/` (ADR-060).
- The full sheet is kept as `web/assets/img/seasons/sheet.webp` for re-cuts.
- Both sides look badges up by the `badge` key ("01"…"13").

**Surfaces.**
- `/clan` and `/players/{id}` gain `pakistan_season`.
- The Rankings page opens with a season banner: the badge, "Pakistan Season 1", "Season of
  Zarb-e-Shaheen", the Nastaliq Urdu name, and the Brawlhalla season with its approximate end date.
- The clan page's season tile and the player page's season line use the Pakistan season.
- `/leaderboard`, `/pakistan leaderboard` and the weekly Pakistan post name the season in the footer,
  with the badge as the thumbnail.
- **Season-start announcement:**
  - The snapshot tick posts the new season's badge and names to #announcements once.
  - `guild_settings.announced_season` (migration 0014) records it only after a successful post, so a
    missing channel or permission retries next tick.
  - The first deploy announces Season 1.

Files: `src/services/seasons.py`, `src/bot/content/season_embeds.py`,
`alembic/versions/0014_announced_season.py`, `alembic/versions/0015_restamp_default_season.py`,
`web/assets/img/seasons/*`, `src/assets/img/seasons/*` (new); `src/core/config.py`, `src/bot/client.py`,
`src/bot/cogs/{clan,link,pakistan,profile}.py`, `src/bot/content/clan_embeds.py`,
`src/services/snapshot_service.py`, `src/database/models/guild_settings.py`,
`src/database/repositories/guild_settings_repository.py`, `src/api/{schemas,routers/clan,routers/players}.py`,
`web/rankings.html`, `web/assets/js/{theme,pages/rankings,pages/clan,pages/player}.js`,
`web/assets/css/style.css`, `.env.example`, `README.md`, `docs/{COMMANDS,DATABASE,ROADMAP}.md`, tests.

Verified:
- Season tests: S42 on the anchor, the last second before 13 weeks, S43 at 13 weeks, S41 before the
  anchor, the override, the names cycling at Season 14, no Pakistan season before S42, labels,
  and announcement decisions.
- Embed tests: every season has a badge file, the thumbnail attaches from S42 only, the season-start
  embed, and footers.
- API tests: `pakistan_season` on `/clan` for S42 and null before it.
- Repository test for `announced_season`.
- A migration test that season-1 rows either side of the anchor become 41 and 42, including the exact
  boundary second, with NULL left alone; Alembic round-trip.
- Playwright at 1440px and 390px: the banner with a loaded badge and Urdu name, the clan tile, the
  player season line, no overflow, no console errors.
