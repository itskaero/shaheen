# BRAWLISTAN — Platform audit and product strategy

*Audit date: 17 October 2026. Recommendations only: nothing in this document has been implemented.*

**How this was done.** I read the whole repository: the bot (`src/bot`), services, the API (`src/api`), the
static site (`web/`), 134 ADRs in `docs/DECISIONS.md`, and `COMMANDS.md`, `DEPLOY_NAS.md` and `ROADMAP.md`.
I queried the live API (`api-brawlistan.rekorex.online`) and crawled all 17 live pages in headless Chromium,
at 390 px (phone) and 1440 px (desktop), recording load time, page weight, console errors, overflow and
small tap targets.

**What I could not verify:**
- the live Discord server itself (channels, activity, how members actually behave);
- the production `.env` (which announcement toggles are on);
- bot logs, and the NAS uptime history beyond the outage I observed;
- the Brawlhalla API quota headroom;
- traffic, because the site has no analytics at all.

Labels used below:
- **[observed]**: seen in the code, the live API or the live site;
- **[assumption]**: a judgement that needs validating.

---

## Deliverable 1 — Executive assessment

**Maturity.** BRAWLISTAN is technically mature and socially early.
- **[observed]** The engineering is unusually solid for a community project:
  - a layered Python codebase with ~640 tests and 29 migrations, and an audit log;
  - rate-limited write endpoints, nightly backups, and a static site that keeps working on cached
    snapshots when the API is down.
- **[observed]** The community using it is small. These numbers are live, 17 Oct 2026:

| Signal | Value | Source |
|---|---|---|
| Discord members | 59 | `GET /clan` |
| Members who linked a Brawlhalla account | **4** (3 verified) | `/rankings/pakistan` `is_claimed` |
| Players tracked | 90 | `/players` |
| …of which placed in ranked this season | **16** | `rating != null` |
| …tracked only because their in-game clan roster is synced | ~74 | `region: none`, team set |
| Players who set a city (City Wars) | **2**, both Bahawalpur | `/rankings/cities` |
| Confirmed matches ever (`/challenge`, `/match`) | **0** | `/community/matches` |
| Tournaments ever | **0** | `/tournaments` |
| Coaches listed | 1 | `/coaches` |
| Achievements ever earned (of 30) | 11, all by the same 4 members | `/achievements` |
| Clan Wars teams scoring this week | 3 of 5 (DE 272, SG 116, RW 21) | `/clan-wars` |
| Slash commands | 93 | `docs/COMMANDS.md` |
| Main nav destinations | 13 | `web/assets/js/shell.js` |

**Strongest features.** The ones that need nobody to do anything:
- **Pakistan rankings** from the official API;
- **team rosters** mirrored from in-game Brawlhalla clans;
- **Clan Wars and weekly quests**, scored automatically from ranked snapshots.

Every feature that needs a member to act (reporting a match, running a tournament, requesting a coach,
choosing a city) has close to zero usage.

**Biggest problems:**
1. **The platform is far ahead of its community.**
   - ~25 product surfaces serve 59 Discord members and 4 linked players.
   - Empty or near-empty surfaces (Tournaments 0, Coaches 1, City Wars 1 city, competition achievements
     0) tell a newcomer the scene is quiet, which works against growth.
2. **Linking is the bottleneck.**
   - 4 of 59 Discord members (≈7%) have linked.
   - Linking unlocks City Wars, quests on the profile, the Verified badge and the Founders panel, so
     almost nobody gets the personal parts of the product.
3. **Reliability.**
   - **[observed]** On 16 Oct the API returned Cloudflare 530 for hours, and the site fell back to
     6-hour-old snapshots.
   - ADR-130 records an earlier outage, where snapshots stopped for a week.
   - **[assumption]** A home NAS in Pakistan is exposed to load-shedding and ISP outages.
4. **No measurement.** There's no web analytics, so no one knows whether anyone visits, returns or comes
   from Discord.

**The most promising opportunity: Clan Wars.**
- It already works with zero manual input, and 87 of the 90 tracked players are already on a team.
- It gives in-game clan leaders a reason to recruit and push members to link.
- A weekly result is a natural thing to post and share in WhatsApp groups.

Make Clan Wars the flagship, make linking one tap, make the weekly result shareable, and stop building
new surfaces until the existing ones have people in them.

---

## Deliverable 2 — Existing feature audit

Key to the action column:
- **K**: Keep
- **I**: Improve
- **S**: Simplify
- **R**: Remove or hide
- **?**: Investigate

### 2a. Website, page by page (live crawl, phone and desktop)

All 17 pages load with **no horizontal overflow** and **no JavaScript errors**.
- Times are DOMContentLoaded and network-idle.
- "Small targets" counts links and buttons under 32 px in either dimension (phone).

| Page | Current implementation [observed] | User value | Problems or gaps | Action |
|---|---|---|---|---|
| Entrance `index.html` | Full-screen key art, headline, 2 CTAs, live stats tiles, top-10 carousel, legend mosaic, join panel | First impression; looks premium | 2.2 MB on phone (art + music), 1.8 s to DOM on mobile. The stat tile **"Cities at war: 1"** advertises emptiness. | **I** |
| Dashboard `home.html` | Ticker, season card, season banner + countdown, players/teams/cities lists, tournaments toggle, rising, legend meta, featured | One-screen overview | **404 console errors** on every load: `/featured` and `data/featured.json` don't exist when no player is featured. 34 small tap targets on phone. Tournaments panel shows "Data unavailable". | **I** |
| Rankings | Tabs Pakistan/Global/1v1/2v2/Power/Rising/Cities, filters, pager, season selector | **Core value: "who's best in Pakistan"** | Power tab always empty by design. Of 90 rows, 74 are unplaced this season, so most tabs are thin. The music pill (bottom right) **covers the rating column on phones**. | **K / S** (hide Power) |
| Players + generated player pages | Directory (grid/list, search, filters), profile with stats, history chart, legends, seasons, quests, compare, Share/WhatsApp, claim form | Identity and reputation | An unlinked player's profile shows a "Data unavailable" panel. The share preview image is the generic site card, not the player. | **I** |
| City Wars `cities.html` | Hero, podium, standings, how-to steps | Regional identity | **1 city with 2 players.** The podium renders one lonely card. Cities can be changed any time. | **I** (feed it via linking) |
| Clan Wars `clanwars.html` | Hero + countdown to Monday PKT, last winner, live standings with scorers, season table, how it works | **Strongest weekly loop** | Season table is empty until the first Monday result. Roster changes mid-week move points (see §8). 2 of 5 teams can't score (Clan Monke has 26 roster members, 0 placed; SHAHEEN has 0 members). | **I — invest** |
| Teams + team pages | Large slides, holographic cards (WebGPU), rosters synced from in-game clans | Clan identity | Founding team SHAHEEN shows 0 members (no in-game clan id). WebGPU cards are heavy for low-end phones **[assumption: fall back fine, not measured]**. | **K / ?** |
| Coaches | Directory of linked Coach-role holders | Mentorship | 1 coach, no profile filled in. | **R** from nav until ≥3 coaches |
| Seasons | 13 named seasons with art, current season details | Season identity | 451 KB of art. Fine. | **K** |
| Tournaments + bracket | List + bracket viewer for in-house tournaments | Event discovery | **0 tournaments ever.** The page is an empty state. | **R** from nav; rethink (§3) |
| Achievements | Gallery by category, rarity, holders | Recognition | 30 achievements, 11 ever earned, all by the same 4 people. Most are lifetime game counts awarded instantly on linking (all 4 got "5000 games" on day one). 49 small tap targets on phone. | **I** (redesign, §4) |
| Founding Team `clan.html` | SHAHEEN story, Founders & Admins (new, unmerged), roster, matches, chat activity | Origin story; trust | 1.1 MB. "Recent matches" is permanently empty (0 matches). Chat activity covers 3 people. | **S** |
| Music | Original tracks, beat-synced video | Brand flavour | 811 KB+ of media; not a reason to visit a rankings site. | **S** (footer link) |
| Discord `join.html` | Invite + 3 steps | Conversion | Good and concise. | **K** |
| 404 | Branded, redirects missing player pages | Robustness | Good. | **K** |
| Site-wide | Shell with sidebar, phone bottom bar + "More" sheet, background music toggle, stale-data banner, snapshot fallback | Consistency, resilience | 13 nav destinations for a small scene. The music toggle overlaps content on phones. **No analytics.** | **S / I** |

### 2b. Discord bot and integration [observed in code]

| Feature | Current implementation | User value | Problems or gaps | Action |
|---|---|---|---|---|
| Identity: `/link`, website claim code, `/verify`, `/pakistan join/leave` | Two linking paths through one service; codes hashed, single use, 15 min; no takeover; audit-logged; staff verification | Trustworthy identity | **4 of 59 members linked.** Linking takes 3–6 steps across two apps. Nothing in Discord pushes members to do it at the moment they arrive. | **I — top priority** |
| Ranking snapshots | Every 6 h (cron `17 */6`) and on link; season-scoped; site snapshots committed to git | Automatic data | 6 h staleness; acceptable. | **K** |
| Clan Wars scoring | Weekly, best 5, 10 pts/win plus rating gained, losses 0, recorded idempotently | Team competition, no admin work | Roster fluidity, smurf/alt farming, no recap post by default (`ANNOUNCE_CLAN_WARS=false`) | **I — invest** |
| Weekly quests + season level | 3 quests from snapshots, never self-reported, unique completions | Personal weekly goal | Only visible to linked players (4). Good design. | **K** |
| City Wars | `/city set` from a fixed list of 17; average of the best 5 placed | Regional pride | Requires linking first, then a second command; the city can be changed at will. | **I** |
| Teams / clan sync | Mirrors in-game clans; captains manage rosters | Rosters without admin work | SHAHEEN has no in-game clan; foreign players on PK clans need opting out. | **K** |
| Challenges, scrims, match reporting, `/rivalry` | Full report/confirm/dispute flow | Verified head-to-head records | **0 confirmed matches ever.** | **R** from promotion; keep the code dormant |
| Tournaments (in-house brackets) | Single elimination, 1v1/2v2 | Events | **0 ever.** Pakistani community events likely run elsewhere **[assumption]**. | **S** (see P2) |
| `#looking-for-game` kiosk / `/looking` | Joinable spar cards | Finding opponents | Usage unknown **[not verifiable]** | **?** |
| Chat XP / `/level` / `/chatboard` | XP per message | Activity signal | Rewards message volume. Conflicts with "don't reward spam". 3 linked people show on the site. | **S** (Discord-only, no website surface) |
| Achievements + Hall of Fame posts | Catalogue of 30; announcements | Recognition | Trivial lifetime milestones; competition and community ones unearned | **I** |
| Coaching | Role mirror, `/coach request` with buttons | Mentorship | 1 coach | **K** code, **R** nav |
| Moderation, reports, `/admin status`, access/approval | Complete, audit-logged | Safety and operations | `/admin status` is pull-only, so nobody is alerted when the API dies | **I** (alerting) |
| Announcements | Season start, weekly digest, Pakistan weekly, achievements, featured; quests and Clan Wars off by default | Distribution | The best shareable moment (the weekly Clan Wars result) is off | **I** |
| Founders & Admins mirror (ADR-135, on this branch, not merged) | Avatars and names of Founder/Admin holders | Trust, human faces | Needs migration 0029 deployed | **K** |
| 93 slash commands | — | Power | Discoverability burden for newcomers; `/help` is paginated | **S** (hide rarely used commands from non-staff) |

---

## Product vision

### What the platform should become

The automatic scoreboard of Pakistani Brawlhalla, where your clan and your city compete every week
just because you play ranked.

The defining property is **zero-effort competition**. Brawlhalla already produces the data (ranked
games). BRAWLISTAN's job is to:
1. attach identity to it (who, which clan, which city);
2. turn it into a weekly story people care about (Clan Wars, quests, risers);
3. make that story easy to share where Pakistani players already are (Discord and WhatsApp).

**What this deliberately is not:** a tournament platform, a social network or a chat-XP machine.

### Answers to the vision questions

1. **Strongest existing value proposition.**
   - An always-current Pakistan ranking and a weekly clan league that run themselves.
   - No other place answers "who's the best in Pakistan, and which clan is winning this week?" without
     anyone filling in a spreadsheet.
2. **What brings players back weekly.**
   - The Clan Wars week (it resets Monday 00:00 PKT, with a countdown and live standings), their own
     weekly quests, and a visible contribution to their team ("you scored 63 of DE's 272").
   - Daily return isn't realistic or necessary for a scene this size. Design for a weekly rhythm.
3. **What would make it indispensable.**
   - Becoming the official record: the weekly Clan Wars results, the season Hall of Fame, and verified
     identities.
   - Clan leaders recruiting by saying "join us, we're top 3 in Clan Wars".
   - Tournament organisers linking results here (see P2).
4. **What not to build.** See Deliverable 10. In short:
   - no in-house Elo;
   - no more in-house tournament tooling;
   - no website accounts or login;
   - no predictions;
   - no more pages;
   - no chat or voice XP rewards.
5. **Differentiation from a generic tournament site or a Discord server.**
   - Competition that happens without organising anything;
   - rosters and ratings that come from the game;
   - Pakistani city and clan identity;
   - shareable proof.
6. **The smallest valuable version.** Three pieces:
   - one-tap linking in Discord;
   - Clan Wars with fair rosters and a weekly result card posted to Discord;
   - a lean site (Rankings, Clan Wars, Players) that's always up.

---

## Deliverable 3 — Top 10 recommended improvements

Scored by **Impact × Confidence ÷ Effort**, with each score explained rather than given as a number.

| # | Improvement | Impact | Confidence | Effort | Why this rank |
|---|---|---|---|---|---|
| 1 | **One-tap linking in Discord**: a persistent "Link your account" button in #welcome opens a modal (Brawlhalla/Steam ID and city), then confirm | Very high: unlocks every personal feature for the other ~93% of members | High: the current funnel (≈7%) is the measured bottleneck | Low–Med: reuses `LinkService`, CityService, ConfirmView | Highest leverage per hour |
| 2 | **Uptime alerting + analytics baseline**: external health check posting to a staff channel; Cloudflare Web Analytics (cookie-less, the domain is already on Cloudflare) | High: outages have silently lasted hours to days | High | Low | Nothing else can be measured or trusted without it |
| 3 | **Clan Wars integrity**: roster lock at week start, a per-account eligibility floor | High: the flagship needs to be trusted before it's promoted | High: concrete exploits exist (§8) | Medium | Must precede promotion |
| 4 | **Weekly Clan Wars recap + share card** (Monday post with an image; site OG image) | High: a weekly story plus a WhatsApp distribution channel | Medium–High | Medium: `image_service` (Pillow) and the announcement plumbing exist | The growth engine |
| 5 | **Mobile fixes**: music pill overlap, tap targets ≥ 40 px, featured 404s, unlinked-profile "Data unavailable" | Medium | High: observed directly | Low | Cheap and removes friction |
| 6 | **Navigation diet**: 13 → 5 primary (Home, Rankings, Clan Wars, Players, Discord); City Wars/Teams/Seasons/Achievements under More; hide Tournaments/Coaches/Power until they have content | Medium | Medium–High | Low | Stops empty pages from undercutting credibility |
| 7 | **Entrance stats that don't undercut**: replace "Cities at war: 1" with live Clan Wars leaders and "90 players tracked" | Medium | High | Low | First impression |
| 8 | **City at link time + city lock per season** | Medium: City Wars can't work with 2 tagged players | Medium | Low | Feeds City Wars without a new feature |
| 9 | **Season-based achievements** replacing trivial lifetime ones | Medium | Medium | Medium | Recognition that means something |
| 10 | **Captain loop**: Monday DM or post to each team's captain with standings and who hasn't linked | Medium–High: captains are the real recruiters | Medium | Low–Med | Turns clan leaders into the growth team |

---

## Deliverable 4 — MVP roadmap (sequence and dependencies, no dates)

### P0 — Immediate fixes

| Item | User problem | Solution | Impact | Complexity | Dependencies | Bot? | New backend? | Risks | Success metric | Why P0 |
|---|---|---|---|---|---|---|---|---|---|---|
| Uptime alerting | Site silently serves stale data for hours or days | External HTTP check on `/health` and the site, posting to a staff Discord webhook. Optionally a bot loop that posts `/admin status` problems proactively. | Fewer and shorter outages | Low | Webhook URL kept as a secret, never in the repo | Optional | No | Alert noise: alert only after 2 failed checks | Hours of API downtime per month | Trust in every number depends on it |
| Analytics baseline | No idea whether anyone visits | Cloudflare Web Analytics beacon (no cookies) on every page | Enables every later decision | Low | Cloudflare account | No | No | Privacy: choose cookie-less | Weekly visitors, return rate, Discord referrals | Baseline before changing anything |
| Mobile overlap and targets | The music pill covers rankings data; tiny targets | Move the pill into the "More" sheet on phones; min 40 px targets | Readability | Low | — | No | No | — | 0 overlaps in a 390 px crawl | Observed defect |
| Featured 404s | Console errors on every dashboard load | Return `null` with 200, or ship `featured.json` with `null` | Clean | Low | — | No | API tweak | — | 0 console errors | Observed defect |
| Hide empty surfaces | Tournaments 0, Coaches 1, Power tab permanently empty | `ready: false` until there's content; hide the Power tab | Credibility | Low | — | No | No | Content later needs re-enabling | — | Cheap credibility |
| Deploy ADR-135 | Founders & Admins waiting | Merge, run migration 0029, restart the bot | Human faces on the site | Low | NAS access | Yes | Yes (done) | — | Panel shows ≥1 Founder | Already built |

### P1 — First MVP release (in this order)

1. **One-tap onboarding and link**. Spec A below.
2. **Clan Wars integrity: roster lock and eligibility.** Spec B, part 1.
3. **Weekly Clan Wars recap, share cards and captain loop.** Spec B part 2, and spec C.
4. **City at link time and city lock.**
   - Folded into spec A.
   - City changes are limited to once per season through `/city set`. Staff can override.
5. **Navigation diet and entrance stats** (#6, #7).

Dependencies: P0 analytics before P1, so impact can be measured. Item 2 before item 3, so nothing unfair
gets promoted.

### P2 — Second iteration (once linking reaches ≈25% and 4+ teams score weekly)

- **Season Hall of Fame:**
  - Clan Wars champions, top quest earners and city winners per Pakistan season;
  - one page, fed by the existing `clan_war_results` and quest completions.
- **Season-based achievements** (Deliverable 5).
- **External tournament listing:**
  - staff record an event by name, date, an external bracket link (start.gg/Challonge) and the top 3
    results, linked to player profiles;
  - this replaces promoting the in-house bracket tool. It records what happens in the scene without
    asking organisers to change tools.
- **Per-player share images** (dynamic OG card with rating, tier and team).
- **Recognition roles in Discord:**
  - a current-season "Clan Wars Champion" role for the winning team's scorers;
  - a "Season N Top 10" role.
  - Both are synced from data and removed when the season ends.

### P3 — Experiments (small, reversible)

| Experiment | Hypothesis | How to test small | Kill criterion |
|---|---|---|---|
| City Wars "weekend surge" | A weekend City Wars score (rating gain by city) creates more noise than the season average | Run 2 weekends behind a flag | Fewer than 3 cities with ≥2 scorers |
| Newcomer buddy | Pairing new linkers with a volunteer increases week-2 activity | Manually for 10 newcomers | No difference in week-2 ranked activity |
| Clan vs clan featured match | A pre-announced exhibition between the top 2 clans drives viewing | Once, streamed by a member | Fewer than 15 live viewers [assumption threshold] |
| Rivalry card | Auto "rivals" between players within ±25 rating | Show on 10 profiles | No clicks (needs analytics) |

---

## Deliverable 5 — Gamification specification

### Principles

1. **Three separate ledgers, never mixed:**
   - **Skill**: Brawlhalla rating and tier, imported and never computed by BRAWLISTAN. It can't be
     farmed on the platform.
   - **Participation**: season level from weekly quests and Clan Wars points. Computed only from ranked
     snapshots, never self-reported.
   - **Contribution**: reputation granted by staff (organiser, helper, caster, mentor). Rare,
     audit-logged, shown as a title.
2. **Activity never looks like skill.**
   - Season level is labelled "Season level" with a play icon, never next to the rating.
   - Clan Wars points are labelled "activity points".
3. **No reward for message volume.** Chat XP stays a Discord curiosity and is removed from the website.
   Voice XP stays unbuilt.
4. **Everything resets each Pakistan season**, so newcomers can compete. History moves to the Hall of
   Fame.

### Mechanics

| Mechanic | Player motivation | How it works | Verification | Abuse risk | MVP or later |
|---|---|---|---|---|---|
| Linked identity + Verified badge | Belonging, credibility | One-tap link (spec A); staff `/verify` | Discord control (code/confirm) + staff check | Claiming someone else's account: blocked by no-takeover and staff verify | **MVP** |
| Weekly quests (exists) | A personal weekly goal | 15 games / 8 wins / +50 rating, from snapshots | Snapshots | Alt accounts: quests only count for the linked account | **MVP** (surface in Discord) |
| Season level (exists) | Progress over a season | 100 XP per quest, level up to 30, resets each season | Derived | Low | **MVP** |
| Clan Wars points (exists) | Team contribution | 10 per win + rating gained, best 5 per team | Snapshots + roster lock | Smurf farming, roster hopping (§8) | **MVP** with fixes |
| Weekly Clan Wars recap + MVP of the week | Recognition | Top scorer of the winning team named in the post | Derived | Low | **MVP** |
| City representation | Regional pride | City chosen at link; one change per season | Self-declared (honour system) + staff override | City hopping late in the season: lock | **MVP** |
| Season Hall of Fame | Legacy | Clan champion, top scorer, top quest earners, city winner | Derived | Low | Later (P2) |
| Season achievements | Recognition with meaning | e.g. "Won a Clan Wars week", "Top scorer of a week", "All 3 quests 4 weeks running", "First to put a new city on the board", "Linked + verified" | Derived from stored results | Low | Later (P2) |
| Contribution titles | Status for helpers | Staff grant: Organiser, Caster, Mentor, Helper | Staff + audit log | Favouritism: publish the criteria | Later |
| Discord recognition roles | Visible status | Season champion and top 10 roles, auto-synced and expiring | Derived | Low | Later (P2) |
| Profile cosmetics (frame by season level, champion frame) | Expression | Frame tiers at levels 5/15/30; champion frame | Derived | None | Later |
| Predictions, voting, daily login | — | — | — | Superficial engagement, gambling optics | **Don't build** |
| Elo from in-house matches | — | — | — | 0 matches to rate; disputes | **Don't build** |

### The progression loop

1. **Arrive** from a Discord invite or a shared result card.
2. **Link** in one tap, picking a city. You appear on the Pakistan rankings, on your clan's roster and
   on City Wars.
3. **Play ranked as usual.** Your games count, with no extra steps:
   - toward your weekly quests (season level);
   - toward your clan's Clan Wars score;
   - toward your city's average.
4. **Monday recap.** Discord shows the winning clan, the MVP and the risers. Your contribution is
   visible ("you scored 63 for DE"), and your captain sees who hasn't linked.
5. **Share** the result card in your clan's WhatsApp group. Friends join to help the top 5.
6. **Season end.** Hall of Fame, champion roles and frames. Everything resets, and you come back
   because the board is level again.

Recognised members emerge from three paths: consistent contribution (MVPs, season level), skill (top
10), or service (contribution titles).

---

## Deliverable 6 — Discord integration roadmap

**The division of responsibilities already exists and is sound [observed]:**
- **Discord:** linking, roles, notifications, announcements, captains' roster commands, moderation.
- **Website:** persistent profiles, official boards, history, shareable pages.
- Both read the same Postgres through the same services. The website never sees Discord identities
  (ADR-040), except Founders and Admins (ADR-135).
- **No rewrite is warranted.**

**Investigation answers [observed]:**

| Question | Answer |
|---|---|
| How are Discord users linked to the website? | `member_player_links` via `/link <ID>` (with a confirm step) or a hashed one-time code entered on the profile page |
| Can identities be verified? | Yes: staff `/verify`. A claim proves Discord control, not Brawlhalla ownership, and the site says so. |
| How do results enter? | Automatically, from Brawlhalla API snapshots every 6 h (plus on link). Manual match reports exist but are unused. |
| Do bot and site stay in sync? | They share one database. The site's fallback snapshots refresh every 6 h through GitHub Actions. |
| What happens when a command fails? | `ShaheenError` is shown to the user; unexpected errors are reported to staff (ADR-126) |
| Can updates duplicate? | Quest completions and Clan Wars results have unique constraints; links have a unique active index (ADR-107) |
| Permissions and admin actions? | Role checks (`require_staff_authorized` and setup-level); destructive actions confirm; the audit log records them |
| Public API? | Read-only FastAPI, CORS open for GET; `POST /link/claim` is rate-limited. No webhooks. |
| Secrets? | Kept in `.env` on the NAS; the API key was removed from logs (ADR-123); nothing in the repo |

**Smallest valuable integrations:**

| Integration | Trigger | Bot behaviour | Website behaviour | Data stored | Failure handling | Verification and permissions | Effort |
|---|---|---|---|---|---|---|---|
| One-tap link (spec A) | Click "Link your account" in #welcome | Opens a modal (ID, city), looks up the player, confirms, links, sets the city, grants Player | Profile shows Claimed and the city | Existing link + city | Brawlhalla API down: "try again"; no partial link | Member themselves; no-takeover rule | Low–Med |
| Weekly Clan Wars recap | Monday tick after the week is recorded | Posts the winner, standings, MVP, image card | Season table; card as the OG image | Existing `clan_war_results` + card PNG | Post failure is logged, retried next tick; idempotent per week | System | Med |
| Captain digest | Same tick | DM or team-channel post to each captain: standings, unlinked roster names | — | None | DMs closed: fall back to the team channel or skip | Captains only | Low–Med |
| Outage alert | Health check fails twice | (external) webhook to #staff | — | None | — | Webhook secret | Low |
| Champion roles | Season end / week end | Grant or revoke roles from the results | Badges on the profile | Results | Best-effort, logged, re-checked each tick | System | Med (P2) |

**Not recommended:**
- rank-change notifications per game (spam);
- website login through Discord OAuth (adds sessions, a write API and an attack surface, for a
  benefit the claim code already provides);
- bot-side tournament brackets (unused).

---

## UX/UI and mobile — Top 10 by impact

| # | Current friction [observed] | Change | Success measure |
|---|---|---|---|
| 1 | Linking requires Discord command → website → code → back. Only 4 did it. | One-tap Discord modal (spec A); the website claim stays as an alternative | Linked members ÷ Discord members |
| 2 | The music pill covers the rankings rating column and the City Wars score on phones | Move it into the More sheet on phones, or dock it in the top bar | No overlap in a 390 px crawl |
| 3 | 13 nav destinations; several empty | 5 primary + More; hide empty pages | Clicks into Rankings and Clan Wars (analytics) |
| 4 | The entrance tile "Cities at war: 1" and the empty podium signal a dead scene | Show the live Clan Wars race and "90 players tracked"; City Wars podium only at ≥3 cities | Entrance → Enter click-through |
| 5 | Share previews are the generic card | Player and Clan Wars result images | Visits with a WhatsApp/Discord referrer |
| 6 | Up to 49 sub-32 px targets per page on phones | 40 px minimum; bigger pills and chips | Crawl count → 0 for primary actions |
| 7 | Entrance 2.2 MB, Founding page 1.1 MB on phone | Smaller hero crop for phones, lazy media, music only after the user taps | Mobile bytes; Core Web Vitals in Cloudflare |
| 8 | Unlinked profiles show "Data unavailable" for quests | Replace with "Link to see weekly quests" plus a CTA | Profile → link conversions |
| 9 | Clan Wars points unexplained per player on the profile | "This week: 63 points for DE (#2 scorer)" panel on the profile | Profile views during the week |
| 10 | A dashboard 404 for the featured player logs console errors | Return null; hide the panel | 0 console errors |

**Kept as is:**
- the brand system (ADR-132 palette, Inter + Instrument Serif);
- the stale-data banner;
- the generated player and team pages;
- the phone "More" sheet.

The design isn't what limits engagement. The empty states and the size of the navigation are.

---

## Community growth and retention

**Segments:**

| Segment | Primary need | Best feature | Why they return |
|---|---|---|---|
| Casual players | See themselves on a Pakistan board; low effort | One-tap link + weekly quests | Monday quest reset, visible progress |
| Competitive players | Know where they stand in Pakistan | Rankings + 7-day trend + Global tab | Rank changes; season end |
| Newcomers | Find people to play with | `#looking-for-game` + one-tap link + clan list | A clan invite; weekly quests |
| Clan members | Help their team win | Clan Wars + recap + MVP | Weekly result |
| Clan captains (key) | Recruit and motivate | Captain digest, roster commands, shareable standings | Their team's position |
| Tournament organisers | Visibility for their events | P2 external listing with results on profiles | Results appear on players' records |
| Creators and spectators | Stories to talk about | Weekly recap, risers, Hall of Fame | Weekly content hooks |
| Moderators and volunteers | Low-effort operations, recognition | Audit log, `/admin status` + alerts, contribution titles | Recognition; less toil |

**Tactics that need no budget:**
1. Make captains the growth team. Five in-game clans already have 87 roster players between them.
2. Post a weekly result card in Discord, and encourage captains to forward it to clan WhatsApp groups.
3. One clear newcomer path: join → tap Link → pick a city → done.
4. Season-start "fresh board" announcements to bring back inactive players. The season reset is the
   natural win-back moment, every 13 weeks.
5. Feature organisers' events (P2) so organisers promote BRAWLISTAN back.

**Avoid:**
- DMs to non-consenting members;
- daily notifications;
- engagement bait such as polls or predictions;
- "invite 5 friends" rewards.

---

## Competitive integrity and governance

**Three things never mixed:**
- **Competitive ranking:** Brawlhalla rating, imported.
- **Participation rewards:** quests, season level, Clan Wars activity points.
- **Community reputation:** staff-granted titles.

### Essential for the MVP

1. **Clan Wars roster lock.**
   - **[observed]** "A player scores for the team they're on now", so a strong player can switch clans
     on Sunday and carry their week's points over.
   - Fix: score each player for the team they were on at week start, Monday 00:00 PKT.
2. **Clan Wars eligibility floor.**
   - **[assumption, needs data]** A fresh alt account climbs rating fast and wins easily at low ratings,
     earning more "rating gained" points than a main account.
   - Options:
     - count only accounts that were placed last season or have ≥N lifetime ranked games;
     - and/or cap points per player per week (e.g. at the 95th percentile of observed weeks, once there's
       data).
   - The top-5 cap already limits headcount inflation **[observed]**.
3. **City lock:** one change per season, with staff override and an audit log.
4. **Published rules.** The Clan Wars and City Wars pages already explain scoring **[observed]**. Add
   the eligibility rule and the lock.
5. **Alerting and backups.**
   - **[observed]** Nightly `pg_dump` with 7/4/3 retention exists.
   - Add an offsite copy (the docs recommend it but it isn't automated) and the outage alert.

### Already in place [observed]

- audit log;
- role-gated admin commands and confirm steps;
- rate limits on claims and reports;
- no-takeover linking;
- Discord identity kept off the site;
- the season-scoped data model.

### Can wait

- **A dispute process for Clan Wars:** scores are machine-derived, so disputes are about eligibility,
  which goes to a staff decision with an audit entry.
- **Penalties beyond exclusion** (`/pakistan remove`, team removal already exist).

### Not appropriate

Anti-cheat beyond the above. BRAWLISTAN can't see gameplay, so it relies on Brawlhalla's own systems.

---

## Technical feasibility and architecture [observed unless marked]

**Stack:**

| Layer | What runs it |
|---|---|
| Bot | Python 3.12, discord.py 2 |
| API | FastAPI |
| Data | PostgreSQL + SQLAlchemy 2 + Alembic |
| Website | Static HTML/JS on GitHub Pages, behind a Cloudflare DNS custom domain |
| Hosting | API, bot and DB in Docker on a home NAS (ZimaOS), behind a Cloudflare Tunnel |
| Fallback data | GitHub Actions snapshot every 6 h |
| Images | Pillow |

**Constraints:**
- A single NAS is a single point of failure: power, ISP and tunnel.
- The Brawlhalla API rate limit is shared by every snapshot. Team rosters add ~74 players for free
  (ADR-125), but each snapshot still costs calls **[quota headroom not verified]**.
- There's no website authentication, by design.

### What each recommendation needs

| Recommendation | Existing data enough? | New work |
|---|---|---|
| One-tap link | Yes | Discord modal view; city choice inside link |
| Roster lock | Partly | Store team membership history per week (a `team_members` history table or a weekly roster snapshot) |
| Eligibility floor | Yes | Snapshots have games and season; a pure rule in `services/clan_wars.py` |
| Weekly recap + card | Yes | Pillow card renderer (pattern exists); announcement toggle |
| Captain digest | Yes | Uses existing team captains |
| Analytics | No | Cloudflare beacon; no backend |
| Outage alert | No | External check or a bot loop |
| Hall of Fame | Yes (`clan_war_results`, quest completions) | One endpoint, one page |
| External tournament listing | No | Small table (event, link, date, top-3 player ids) + staff command |

**Recommendation:** incremental changes only. If outages continue after alerting is in place,
reconsider moving the API and DB to a cheap VPS, with the NAS as backup. ADR-127 already keeps a
rollback path.

---

## Metrics and success criteria

No baselines are invented. Where one is listed, it's the live value from 17 Oct.

| Metric | How to measure | Decision it informs | Baseline |
|---|---|---|---|
| **Link rate** (linked ÷ Discord members) | `/clan` members + count of claimed rows | Whether onboarding works | **4 / 59 ≈ 7%** |
| Weekly active players (tracked players with ≥1 ranked game that week) | Snapshot deltas (the quest code already computes games) | Overall health | Needs a weekly job (P0) |
| Clan Wars participation | Teams with ≥1 scorer; scorers per team per week | Whether the flagship engages | 3 teams; 3/3/1 scorers (week of 12 Oct) |
| City Wars coverage | Cities with ≥1 / ≥3 placed players | When to promote City Wars | 1 city / 2 players |
| Website weekly visitors and returning % | Cloudflare analytics | Site value | None (no analytics) |
| Discord → site referrals | Analytics referrers | Integration value | None |
| Recap reach | Reactions and clicks on the Monday post; share-card visits | Growth loop | None |
| Season retention | Players active in season N who are active in N+1 | Long-term health | First measurable at the end of Season 1 (23 Dec) |
| API uptime | External check | Infrastructure decision | Unknown; outage observed 16 Oct |

---

## Deliverable 7 — Sample user journeys

1. **New player from Discord.**
   - *Today:* joins, reads #welcome, maybe runs `/link`, gets a code, opens the website, finds
     themselves, enters the code. It's long, and most stop.
   - *Proposed:* joins → taps **Link your account** → types an ID, picks Lahore → confirms → "You're on
     the Pakistan rankings, Lahore's board and Delight Esports' Clan Wars roster" with a profile link.
     One minute, without leaving Discord.
2. **Competitive player checking their rank.**
   - Opens Rankings on a phone and sees their row, ▲ trend and Pakistan rank.
   - Taps through to the profile: rating history, a Compare button.
   - **Fixed:** the music pill no longer hides the rating column.
3. **Clan member in Clan Wars.**
   - Plays ranked as usual all week.
   - On Sunday, `/clanwars` or the site shows "You: 48 pts, #3 for your team; your team needs 30 to
     pass SG".
   - On Monday the recap names the MVP. Their captain forwards the card to the clan WhatsApp group.
4. **Player representing their city.**
   - Picks a city while linking.
   - City Wars shows their rating among the best 5 for their city.
   - The page encourages recruiting: "Lahore needs 3 more placed players to enter the podium".
5. **Tournament organiser (P2).**
   - Runs the bracket on start.gg as now.
   - Afterwards, staff run `/event record` with the link and the top 3.
   - The players' profiles show "🥇 Karachi Cup", and the event appears on a Tournaments page that's
     no longer empty.
6. **Inactive player returning for a new season.**
   - Season 2 starts. The Discord announcement says the board is reset and quests are fresh.
   - They play a few ranked games, and by the next snapshot they're placed on a level board, with
     their clan counting on them.

---

## Deliverable 8 — Feature specifications

### Spec A — One-tap onboarding and link

**Problem.** Linking is the gateway to every personal feature, and only ≈7% of Discord members have
done it. The path spans two apps and up to six steps.

**User stories:**
- As a new member, I can link my Brawlhalla account from #welcome in under a minute without leaving
  Discord.
- As a member, I can pick my city in the same step.
- As staff, I can see the link rate.

**Functional requirements:**
1. A persistent message in #welcome with a **Link your account** button. It survives restarts (a
   DynamicItem, as the coaching buttons do).
2. The button opens a modal asking for a Brawlhalla ID or Steam64 ID (required). Then comes the city:
   - inside the modal as a select, if the installed discord.py version supports selects in modals;
   - otherwise as a follow-up ephemeral select of the 17 cities (optional, with "Skip").
3. Validation and lookup through `LinkService.resolve_candidate`. Show the player name for
   confirmation. Confirm links through `LinkService.attach`, which keeps the no-takeover and
   Pakistan-board rules.
4. On success:
   - grant the Player role and take the initial snapshot (as `/link` does);
   - set the city if chosen;
   - reply with the profile link and what they're now part of (board, team, city).
5. Already linked: show the current link with "Change city" and "Relink" options.
6. Staff: `/admin status` shows the link rate.

**Acceptance criteria:**
- A new member completes the link in ≤3 interactions.
- A takeover is refused with the existing message.
- The audit log records `link.discord_button`.
- Restarting the bot keeps the button working.
- Tests cover the service path, the city set and the duplicate guard.

**Data:** none new (existing link, city and audit tables).

**Failure states:**
- Brawlhalla API down: "Brawlhalla isn't answering, try again in a few minutes", and nothing is
  stored.
- Unknown ID: "No Brawlhalla account with that ID".
- The modal times out: nothing is stored.

**Abuse prevention:**
- The existing no-takeover rule and staff `/verify`.
- At most 5 attempts per member per 10 minutes.
- City changes follow the per-season lock.

**Success metrics:** link rate (baseline 7%); time from joining Discord to linking.

### Spec B — Clan Wars, fair and weekly

**Problem.** Clan Wars is the best weekly loop, but rosters can change mid-week and fresh accounts can
farm points, so it isn't ready to be promoted.

**User stories:**
- As a clan member, my points count for the team I started the week with.
- As a captain, I trust the standings enough to share them.

**Functional requirements:**
1. **Roster lock.** At week start (Monday 00:00 PKT, `quests.week_bounds`), store each team's roster.
   The week's points use that roster. A player who joins mid-week starts counting next week.
2. **Eligibility.** A player's points count only if:
   - the account is placed this season;
   - and the account had ≥K ranked games before the week. K is configurable, default to be set from
     data.
3. **Cap (configurable, off by default).** An optional per-player weekly point cap.
4. **Transparency.** The page and `/clanwars` show the eligibility rule and a "not counted: reason" note
   on ineligible scorers.

**Acceptance criteria:**
- Moving a player mid-week doesn't change either team's points that week.
- An account below the floor shows 0 with a reason.
- Recording last week stays idempotent.
- Tests cover the lock, the floor and the cap.

**Data:** new `clan_war_rosters` (team_id, week_start, player_id); config values in settings.

**Failure states:**
- A snapshot gap at week start: fall back to the roster at the first tick after the start, logged.
- A team with no roster: 0 points, as now.

**Abuse prevention:** the lock, the floor and the top-5 cap together. Staff exclusion stays audit-logged.

**Success metrics:**
- teams scoring each week;
- scorers per team;
- zero integrity complaints.

### Spec C — Weekly recap, share cards and captain digest

**Problem.** The week's result is the most shareable thing BRAWLISTAN produces, but nobody sees it
unless they visit the site (`ANNOUNCE_CLAN_WARS=false`), and there's no image to forward.

**User stories:**
- As a member, I see Monday's result in Discord with an image I can forward.
- As a captain, I get my team's position and the names of roster players who haven't linked.

**Functional requirements:**
1. After the week is recorded, render a 1200×630 PNG with Pillow in the brand style (pattern:
   `image_service`):
   - winner, top 3 standings, MVP, week dates and the site URL;
   - served at a stable URL and committed by the snapshot workflow as `data/clan-wars-latest.png`;
   - used as the Clan Wars page's OG image.
2. Post once in #announcements: card, standings and a link. Idempotent per week (unique on
   week_start). Mentions are off.
3. Captain digest:
   - each team captain gets an ephemeral-style DM, or a post in the team channel if DMs are closed;
   - it contains rank, points and gap to the next team, scorers, and roster players not yet linked
     (Brawlhalla names only).
   - Opt out with `/team digest off`.

**Acceptance criteria:**
- One post per week, even after restarts.
- The card renders long team names without overflow.
- The digest is skipped for teams with no captain.
- Everything is audit-logged.

**Data:** a recap-posted marker per week; captain opt-out flag.

**Failure states:**
- Card rendering fails: post the text only.
- The channel is missing: log, and retry next tick.
- DM blocked: fall back or skip.

**Abuse prevention:** no pings; captain digests go only to captains.

**Success metrics:**
- reactions and clicks on the recap;
- visits with a WhatsApp or Discord referrer to `clanwars.html`;
- linking spikes on Mondays.

---

## Deliverable 9 — Risks and assumptions to validate

| # | Risk or assumption | How to validate |
|---|---|---|
| 1 | The community is small enough that weekly (not daily) engagement is the right target | Analytics + weekly-active metric for 4 weeks |
| 2 | Captains will act as recruiters | Ask the 5 captains; pilot the digest with one |
| 3 | Low linking is caused by friction, not lack of interest | Compare the link rate before and after spec A |
| 4 | Alt/smurf farming is a real Clan Wars risk | Inspect per-account games and gains after 4 recorded weeks |
| 5 | NAS reliability will keep causing outages (power, ISP) | Uptime check for a month |
| 6 | Brawlhalla API quota covers more tracked players | Log API call counts per snapshot |
| 7 | Pakistani events happen outside BRAWLISTAN (Challonge, start.gg, WhatsApp) | Ask organisers; list known events |
| 8 | Roster-synced players (~74) are mostly Pakistani | Ask captains; a team can opt out of PK (ADR-125) |
| 9 | City self-declaration will stay honest | Spot-check; a lock limits the damage |
| 10 | Showing Discord avatars of Founders/Admins is acceptable to them (ADR-135) | Ask them before deploying |

---

## Deliverable 10 — Final recommendation

**What to build first:**
1. Uptime alerting and analytics (P0).
2. **One-tap linking in Discord.**

Everything personal depends on linking. Measure before and after.

**What to avoid:**
- **No new pages.** Statistics and Legends are already marked not ready in `shell.js`; leave them unbuilt.
- **No in-house rating or Elo** (0 matches to rate), and no more in-house tournament tooling (0 used).
- **No website login.**
- **No predictions, voting or daily-login rewards**, and no chat or voice XP rewards.
- **No new commands** until the 93 are trimmed for non-staff.

**What deserves the most investment:** **Clan Wars.**
- It already works without staff, it involves the clans that hold 87 of 90 tracked players, and it
  produces a weekly story.
- Make it fair (spec B), then make it loud (spec C).

**The single change that would most improve retention:** the **Monday Clan Wars recap with a shareable
card**. It turns ranked games players already play into a weekly team result they see, talk about and
forward. One-tap linking improves *activation*; the recap improves *return*.

**In 6–12 months, if the MVP works:**
- most active Discord members are linked;
- all five clans score every week;
- the Monday recap is a ritual, forwarded to clan WhatsApp groups;
- Season 1 and 2 champions sit in a Hall of Fame;
- City Wars has 3+ competitive cities;
- local tournaments run elsewhere but their results appear on player profiles;
- the site stays small (Rankings, Clan Wars, Players, Hall of Fame), fast on phones, and up.

The goal isn't the site with the most features. It's the one the scene treats as the record.
