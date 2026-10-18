# BRAWLISTAN explainer video

A ~64-second, 1080p kinetic-typography explainer for **brawlistan.rekorex.online**:
how to link your Brawlhalla profile, what City Wars and Clan Wars are, and how
to get started. Built with [Remotion](https://www.remotion.dev/) from the site's
own screenshots, art, fonts, palette and original music. Nothing in `web/` was
changed.

**Output:** `out/brawlistan-explainer.mp4` (1920×1080, 30 fps, H.264 + AAC,
64 s, audio mastered to −14 LUFS / −1.5 dBTP by `scripts/master.sh`).

## What the video says, and where it was verified

Everything on screen was checked against the code and docs in this repository.

| Topic | What the video shows | Source |
|---|---|---|
| Linking (website route) | Join the Discord → `/link` with no ID → one-time `XXXX-XXXX` code (15 min, single use, a new one replaces it) → open your profile on Players → **Claim this profile** → enter the code → "Linked." | `src/bot/cogs/link.py`, `src/bot/content/profile_embeds.py`, `web/assets/js/pages/player.js`, ADR-107 |
| Linking (Discord route) | `/link <Brawlhalla or Steam64 ID>` → check the player → Confirm | same, `docs/COMMANDS.md` |
| After linking | On the BRAWLISTAN Pakistan rankings (unless you left with `/pakistan leave`); profile shows Claimed; staff `/verify` makes it ✓ Verified; rating syncs every 6 hours | ADR-107, ADR-125, `web/join.html` |
| City Wars | Linked players pick one of 17 fixed cities/regions with `/city set` (`/city clear` to change); score = average of the city's best 5 placed 1v1 ratings this season; unplaced/no-city players don't count; standings on the City Wars page, Rankings → Cities, `/rankings board:city` | `src/services/cities.py`, `src/bot/cogs/network.py`, `web/cities.html`, ADR-128/130 |
| Clan Wars | Weekly team league, Monday 00:00 → Monday 00:00 PKT; 10 points per ranked 1v1 win + 1 per rating point gained; losses count 0; a team's best 5 members count; be on a team (captains use `/team`, or the roster follows the in-game clan); weekly wins build the season table; `/clanwars` | `src/services/clan_wars.py`, `web/clanwars.html`, ADR-131 |

### Real vs. illustrative

- **Real:** every website screenshot (captured from `web/` with the committed
  data snapshots of 2026-10-16), the City Wars page, the Clan Wars standings
  (Sigma Grinders 70, Delight Esports 63, others 0 — week of Oct 12, in
  progress), the team logos, bot reply texts and command descriptions.
- **Labelled on screen:** the link code `ABCD-EFGH` ("Example code"), the
  profile "YourName" ("Demo profile" — the real `player.html` UI driven by a
  mocked API, so no real player is shown claiming anything), the `/city set`
  pick of Lahore ("Example pick"), and the five ratings in the City score demo
  ("Illustrative values").
- The Discord chat is a recreation of Discord's UI with the bot's real text.

## Storyboard

| Time | Scene | Beat |
|---|---|---|
| 0:00–0:05.8 | Hook | Silence and a slash of light; the drop hits on **FIGHT FOR YOUR city.**, whip to **REPRESENT YOUR clan.**, logo slam with the motto |
| 0:05.8–0:12.7 | Meet the site | The real entrance page flies in; the camera drops onto the real sidebar as Rankings, City Wars, Clan Wars, Players, Teams, Seasons hit on the beat |
| 0:12.7–0:27.7 | Link your profile | Four-step rail: Join Discord (real button), `/link` → code, Claim this profile (real form, demo profile), Linked → what you get |
| 0:27.7–0:40.4 | City Wars | City names flicker, the track's drop slams **CITY WARS** over a green-and-white ribbon; `/city set`; best-5 average; the real City Wars page |
| 0:40.4–0:52.5 | Clan Wars | Gold **CLAN WARS** slam; the five real teams; +10 / +1 / 0 / top 5; real standings and the Monday deadline; City Wars vs Clan Wars split (from 0:50.2) |
| 0:52.5–1:04.2 | Call to action | 1 Join the Discord · 2 `/link` · 3 `/city set` · 4 Play ranked → logo, URL, motto, final hit |

City Wars uses the Pakistan-green accent and Clan Wars gold, so the two are
visually distinct throughout.

## Audio

- **Music:** 129.3 s → 193.5 s of the site's original anthem
  `web/assets/audio/brawlistan.mp3`. Scene cuts sit on its beat map
  (`web/assets/audio/brawlistan.beats.json`, see `src/beats.ts`); the drop at
  157 s lands on City Wars.
- **SFX:** synthesised from scratch by `scripts/make_sfx.py` (no samples, no
  licensing). Cue sheet: `src/cues.ts`.

## Re-rendering

Requirements: Node 20+, Python 3 with Pillow and NumPy, ffmpeg, and a Chromium
(Playwright's is used automatically if present; otherwise set
`REMOTION_BROWSER=/path/to/chrome`).

```bash
cd video/explainer
npm install

# Optional: refresh assets (only needed if the site, art or music changed)
python3 -m http.server 8090 --directory ../../web &   # serve the site
npm run capture                                       # screenshots -> public/shots
python3 scripts/prepare_assets.py                     # logo, art, music window -> public/
python3 scripts/beats_ts.py                           # src/beats.ts from the beat map
npm run sfx                                           # public/sfx/*.wav

npm run studio    # preview / scrub in the browser
npm run render    # Remotion -> out/render-raw.mp4, then master.sh -> out/brawlistan-explainer.mp4
```

A single frame: `npx remotion still src/index.ts Explainer out/frame.jpg --frame=900`.

## Layout

```
video/explainer/
  src/            Remotion source: Explainer.tsx (timeline + audio), scenes/, components/, theme.ts, cues.ts, beats.ts
  public/shots/   real screenshots of the site (scripts/capture*.mjs)
  public/img/     logo (keyed from docs/brand), key art, team logos
  public/audio/   music window; public/sfx/ synthesised effects
  scripts/        capture, asset prep, beat map, SFX, contact sheet
  out/            the rendered MP4
```
