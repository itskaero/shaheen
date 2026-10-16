# BRAWLISTAN Discord recruitment trailer — production package

**Goal:** a Pakistani Brawlhalla player watches 30 seconds, recognises their
scene, and joins the Discord. The Discord invite is the main call to action;
the website supports it.

**Working title:** *FIND YOUR FIGHTERS*

**Format:** 9:16 master (1080×1920) for TikTok, Reels, Shorts and WhatsApp
Status, plus a 16:9 cut (1920×1080) for YouTube and Discord. 30 s, 30 fps.

---

## 0. What's verified, and what to fix first

Checked against this repository (`web/`, `docs/DECISIONS.md`, `src/bot/constants.py`):

| Claim used in the trailer | Source |
|---|---|
| Discord invite `https://discord.gg/UXVDWxBzy` | `web/assets/js/config.js` (`DISCORD_INVITE_URL`) |
| Discord has #looking-for-game (with a spar kiosk), #general, #clips, #tournaments, #rankings, #achievements | ADR-109, `docs/DISCORD_SPEC.md` |
| **Clan Wars:** a weekly team league scored from ranked play, ending Monday 00:00 PKT | `web/clanwars.html`, ADR-131 |
| **City Wars:** 17 Pakistani cities and regions; a city's score is the average of its best 5 placed 1v1 ratings | `web/cities.html`, `src/services/cities.py`, ADR-128 |
| **Pakistan rankings**, player profiles, teams, seasons (Season 1: Markhor) | `web/rankings.html`, `players.html`, `teams.html`, `seasons.html` |

**Fix before publishing:**
- **City Wars link:** the page is `https://brawlistan.rekorex.online/cities.html`.
  `citywars.html` doesn't exist and would land on the 404 page.
  Clan Wars (`/clanwars.html`) is correct.
- **Invite:** I can't see from the repo whether `discord.gg/UXVDWxBzy` is set to
  *never expire* with no use limit. Check it in Discord → Invite People → Edit
  invite link before a campaign points thousands of people at it.

**What the trailer never states:** member counts, prize money, tournament
results or "the biggest" anything. None of these are verified, and counts go
out of date.

---

## 1. Concept

**"Find your fighters."** Every Pakistani Brawlhalla player knows the feeling:
grinding ranked alone at 2 a.m. on a laggy ME/SEA server, never knowing who
else from Karachi or Lahore is out there. The trailer opens in that isolation
(darkness, one green spark) and turns it into rivalry (*your next rival is out
there*), then belonging. Cities light up across a map and clans clash in Clan
Wars. The beat drops on the BRAWLISTAN logo, and the video ends with the one
thing to do: **join the Discord.**

**Colour story.** It starts in shadow, Scene 2's fight is **red and ember**
(the site's own key art), and from the reveal on everything turns **emerald and
white** (the logo's colours and Pakistan's), with magenta only as a spark
accent. The shift from red to green carries the story: rivalry, then home.

**Lines used (the strongest, no more):**
- Hook: *PAKISTANI BRAWLHALLA PLAYERS…*
- *YOUR NEXT RIVAL IS OUT THERE.*
- *FIND YOUR PEOPLE. BUILD YOUR RIVALRIES.*
- *REPRESENT YOUR CITY. BECOME PART OF BRAWLISTAN.*
- *YOUR COMMUNITY IS WAITING.* → **JOIN THE BRAWLISTAN DISCORD**
- Saved for the caption and alternative hooks: *Pakistan, it's time to fight.*
  · *Find your fighters.*

---

## 2. Assets to use (already in the repo)

| Asset | Path (repo) / URL | Use |
|---|---|---|
| **Logo, transparent, high-res** | `video/explainer/public/img/logo.png` (keyed from the 1254 px master `docs/brand/brawlistan-logo-master.png`) | Scene 4 reveal, end card. Don't use the site's 720 px 256-colour `logo.png` in video. |
| Key art: three warriors, red/black, green-white flag ribbons | `web/assets/img/brawlistan/warriors.jpg` (1672×941) · https://brawlistan.rekorex.online/assets/img/brawlistan/warriors.jpg | Scene 2 start frame |
| Night Pakistani landscape, mosques, green/magenta sky | `web/assets/img/brawlistan/hero-scene.jpg` (1920×1080) | Scene 3 start frame, end-card background |
| Wide banner: Minar-e-Pakistan, floating islands (logo baked in) | `web/assets/img/brawlistan/banner.jpg` (1600×640) | Optional Scene 3 flash, cropped to avoid the baked-in logo |
| Team logos: Sigma Grinders, Delight Esports, Clan Monke, Revenant Wolf, SHAHEEN | `web/assets/img/teams/*.png` (512 px) | Scene 3 Clan Wars "VS" flash |
| Real site screenshots (City Wars, Clan Wars, dashboard) | `video/explainer/public/shots/` | Scene 3 UI flashes, 0.5 s each |
| Season 1 "Markhor" card | `web/assets/img/seasons/01.jpg` | Optional Scene 3 flash |
| The 64 s explainer (already made) | `video/explainer/out/brawlistan-explainer.mp4` | Cut 0.5 s UI moments from it |
| **End cards (ready)** | `video/recruitment/end-cards/` | Scene 5 (see §7) |
| Fonts | Inter (Black/ExtraBold), Instrument Serif Italic, Noto Nastaliq Urdu (all Google Fonts, OFL) | Text in CapCut |

Palette: emerald `#1EE08A`, logo green `#3DF26E`, magenta `#F0168C` (accent
only), cream `#FBF9D8`, black `#040806`. Scene 2 only: red `#FF2E3A`, ember
`#FF6A1F`.

**Real gameplay beats AI gameplay.** AI can't reproduce Brawlhalla
convincingly, and players will notice. For Scene 2, ask members in #clips for
2–3 of their best KO clips (with permission, and credit them in the caption),
and use 0.4 s of each between the AI shots. Check Ubisoft's current video
content policy for Brawlhalla footage in promotional posts. Don't use Brawlhalla
legend art or the Brawlhalla logo as the visual focus of an ad: they belong to
Blue Mammoth and Ubisoft.

---

## 3. Timestamped storyboard (30 s, 9:16)

Music: ~120 BPM. The **drop lands at 0:15.0** on the logo, and the last hit
lands at 0:29.

| Time | Scene | Picture | On-screen text (added in CapCut) | Sound |
|---|---|---|---|---|
| 0:00–0:01.5 | 1 The Call | Pure black. A thin emerald crack of light splits the frame, fog lit from inside | — | Sub-bass swell, one heartbeat kick |
| 0:01.5–0:04 | 1 | Clip H1: green energy bleeds through the shadows, embers rise | **PAKISTANI BRAWLHALLA PLAYERS…** (typed in letter by letter, cream, ellipsis blinks) | Kick every beat, riser starts |
| 0:04–0:06 | 2 The Action | Clip H2a: push in on the warriors key art, sparks, ribbons whipping | **YOUR NEXT RIVAL** (slams in on the beat) | Impact + whoosh at 0:04 |
| 0:06–0:09 | 2 | Clip H2b fighter clash, cut on beats with 3 × 0.4 s real KO clips, white impact frames between | **IS OUT THERE.** (0:06, shake) | Hits on every cut, glass-crack at 0:08.5 |
| 0:09–0:11.5 | 3 The Community | Clip H3: slow pan across the night landscape; colour turns from red to emerald | **FIND YOUR PEOPLE.** | Whoosh, pads open up, drums half-time |
| 0:11.5–0:13 | 3 | Clip H3b: city constellation lighting up; labels pop: KARACHI · LAHORE · ISLAMABAD · PESHAWAR · QUETTA · MULTAN | **BUILD YOUR RIVALRIES.** | Tick per city label |
| 0:13–0:15 | 3 | Three 0.6 s flashes: City Wars page → two team logos VS → Clan Wars standings, each with a small label: **CITY WARS** · **CLAN WARS** · **PAKISTAN RANKINGS** | (labels only) | Riser peaks, 0.3 s of silence before the drop |
| **0:15–0:17** | **4 The Identity** | **DROP.** White flash → logo PNG slams onto the H4 emerald energy burst, camera shake, particles | (logo only) | **Drop**, big impact, sub boom |
| 0:17–0:19 | 4 | Logo settles, slow push, light trails orbit | **REPRESENT YOUR CITY.** | Full beat |
| 0:19–0:21 | 4 | Same, logo drifts up | **BECOME PART OF BRAWLISTAN.** | Full beat, reverse cymbal into 0:21 |
| 0:21–0:23.5 | 5 The Recruitment | H5 calm landscape loop, embers | **YOUR COMMUNITY IS WAITING.** (large, centred) | Beat thins out, pads |
| 0:23.5–0:30 | 5 | **End card** (§7) slides up and holds for 6.5 s, long enough to scan the QR | **JOIN THE BRAWLISTAN DISCORD** + invite + QR + website | Final hit at 0:29, ring-out, music ends at 0:30 |

16:9 cut: the same timeline. Use the full-width art instead of the crops, and
the 16:9 end card.

---

## 4. Hailuo AI image-to-video prompts

General settings: Hailuo 02, image-to-video, 6 s, 1080p, aspect from the start
frame. Crop start frames to 9:16 before uploading, centred on the subject.
Every prompt ends with the same line, because the logo and all text are added
in editing.

**H1 — The Call (start frame: IMG-1, generated in §5)**
```
Dark empty arena platform floating in black void, thick low fog. A single thin crack of emerald green light splits the darkness and spreads like lightning through the fog, illuminating it from inside. Tiny glowing green embers rise slowly upward. Cinematic, high contrast, deep blacks, volumetric light. [Push in] slow and steady. No text, no letters, no logos, no watermark.
```

**H2a — The Action, key art (start frame: `warriors.jpg`, 9:16 crop on the gold-armoured knight)**
```
The armoured warrior in the centre holds a battle stance as red embers and sparks blow past the camera. Green and white cloth ribbons whip violently in the wind behind the fighters, hair and capes flutter, glowing ember particles swirl. Anime-style painted key art comes alive, dramatic red rim lighting. [Push in] fast, then subtle [Shake]. Keep faces and armour consistent. No text, no letters, no logos, no watermark.
```

**H2b — The Action, clash (start frame: IMG-2)**
```
Two original fantasy fighters leap at each other above a floating stone platform and their weapons collide in the centre, releasing a bright shockwave of emerald and magenta energy sparks. Speed lines, debris, glowing particles frozen for a split second, then continuing. Anime fighting-game key art style, dynamic and fast. [Truck left] with the motion, [Zoom in] on the impact. No text, no letters, no logos, no watermark.
```

**H3 — The Community, landscape (start frame: `hero-scene.jpg`, 9:16 crop)**
```
Night Pakistani landscape with mosques and minarets under a starry sky. Fireflies and soft green lights drift through the trees, the sky aurora slowly shifts between emerald and violet, faint lights flicker on in the distant city as if people are coming online. Calm, warm, inviting. [Pan right] slowly, gentle [Push in]. No text, no letters, no logos, no watermark.
```

**H3b — City constellation (start frame: IMG-3)**
```
Glowing map of points connected by thin light lines on a dark textured background. One by one each point ignites with an emerald flash and pulses of light race along the lines between them, like a network coming alive. Fine particles drift. Clean, cinematic, high contrast. [Static] then slight [Push in]. No text, no letters, no labels, no logos, no watermark.
```

**H4 — Identity plate behind the logo (start frame: IMG-4)**
```
A powerful burst of emerald green energy explodes outward from the centre of a dark frame, with white light trails spiralling around the empty centre, magenta sparks scattering, smoke rings expanding, particles flying toward the camera. The centre stays clear and dark for a logo. Cinematic esports intro, volumetric light. [Push in] slight, [Shake] on the burst. No text, no letters, no logos, no watermark.
```

**H5 — End loop (start frame: `hero-scene.jpg`, darker crop)**
```
Very slow, calm movement: fireflies drift, a soft emerald glow breathes in the sky, leaves sway gently. Subtle and loopable, nothing dramatic. [Static] with almost imperceptible [Push in]. No text, no letters, no logos, no watermark.
```

Make 2–3 generations per clip and keep the steadiest one. Hailuo sometimes
invents text or logos: if it does, crop or blur them, or regenerate.

---

## 5. Image prompts for the missing start frames

The repo has no dark arena plate, clash image, city map or logo-burst plate.
Make these with any image model (Midjourney, Flux, Ideogram), 9:16. They're
styled to match the existing anime-painted key art.

**IMG-1 — Dark arena**
```
Cinematic dark fantasy arena, a floating stone fighting platform in a black void, thick low-lying fog, a thin crack of emerald green light (#1EE08A) running through the fog, deep blacks, volumetric haze, anime-inspired painterly key art style, moody, minimal, vertical 9:16 composition, no text, no logos, no characters
```

**IMG-2 — The clash**
```
Two original fantasy warriors mid-air clashing weapons above a floating stone platform, one in emerald and white armour with a flowing green and white scarf, one in dark armour with magenta accents, bright shockwave of emerald and magenta sparks at the point of impact, speed lines, debris, night sky with distant South Asian architecture silhouettes, anime fighting-game key art, dramatic rim lighting, vertical 9:16, no text, no logos, not any existing video game character
```

**IMG-3 — City constellation**
```
Abstract stylised map of Pakistan made of glowing points of light connected by thin luminous lines like a constellation, dark charcoal background with subtle topographic contour lines, emerald green (#1EE08A) and white glow, a few magenta (#F0168C) sparks, clean, cinematic, minimal, vertical 9:16, no text, no labels, no borders drawn, no flag
```
(Approximate city positions are enough: Karachi south, Hyderabad just
northeast, Quetta west, Multan centre, Lahore and Faisalabad east,
Islamabad/Rawalpindi and Peshawar north. City names go on in CapCut.)

**IMG-4 — Logo burst plate**
```
Explosive burst of emerald green energy radiating from the centre of a dark frame, white light trails spiralling around a clear empty dark centre, magenta sparks, smoke rings, particles flying toward the camera, esports intro background, volumetric light, vertical 9:16, empty centre for a logo, no text, no logos
```

---

## 6. Soundtrack (Suno)

**Style prompt**
```
cinematic esports trailer, hybrid trap and dubstep, heavy sub bass, aggressive electronic percussion, taiko and dhol hits, tabla accents, dark synth riser, big beat drop, epic, instrumental, 120 bpm
```

**Lyrics field (instrumental structure)**
```
[Instrumental]
[Intro: dark sub-bass swell, single heartbeat kick, distant dhol]
[Build: kicks every beat, rising synth, tabla rolls, metallic hits]
[Break: half-time drums, open pads, short silence]
[Drop: massive bass drop, dhol and taiko groove, distorted synth lead]
[Outro: final impact, ring-out]
[End]
```

Generate a few takes, pick one with a clear drop, and in CapCut slide it so the
**drop lands at 0:15.0**. Trim from the end, add a 0.3 s cut to silence just
before the drop, and fade the last 0.5 s after the final hit.

*Alternative with a sound people will recognise:* use the site's own original
anthem, `web/assets/audio/brawlistan.mp3`. Its drop is at 157.06 s, so a clip
from **2:22.06 to 2:52.06** puts the drop at 0:15.

**Mix:** music around −14 LUFS overall. Duck the music 3–4 dB under the end card
so the final hit and the CTA read clearly. No voice-over is needed.

---

## 7. Final screen (0:23.5–0:30)

Ready-made PNGs, with the logo, invite, URL and QR exact. Rendered from
`video/explainer/src/EndCard.tsx`, and the QR is checked to decode to the invite:

| File | Use |
|---|---|
| `end-cards/end-card-9x16.png` | 9:16 master, with the invite and QR |
| `end-cards/end-card-16x9.png` | 16:9 cut, with the invite and QR |
| `end-cards/end-card-*-blank-slot.png` | Same layout with an empty invite and QR slot, if you use a different invite |

Layout, top to bottom (9:16):
1. **BRAWLISTAN logo** (largest graphic, emerald glow)
2. **YOUR COMMUNITY IS WAITING.**
3. **CTA panel** (the most prominent element: emerald border, glowing):
   **JOIN THE BRAWLISTAN DISCORD** · Discord-blue pill `discord.gg/UXVDWxBzy` · white **QR code**
4. `brawlistan.rekorex.online` (smaller, cream)
5. بلندیوں کی جانب
6. Small print: *Fan community · Not affiliated with Blue Mammoth Games*

Everything important sits above the bottom ~350 px of the 9:16 frame, which
TikTok and Reels cover with captions and buttons. To re-render after changing
the invite, in `video/explainer`: edit `INVITE` in `src/EndCard.tsx`, run
`python3 scripts/make_qr.py https://discord.gg/NEW`, then
`npx remotion still src/index.ts EndCardVertical ../recruitment/end-cards/end-card-9x16.png`
(and `EndCardWide` for 16:9).

---

## 8. CapCut editing plan

**Project:** 1080×1920, 30 fps. Import H1–H5, the gameplay clips, the
screenshots, the team logos, `logo.png`, the end cards, the music and the fonts
(CapCut desktop → Text → Add font → Inter Black, Instrument Serif Italic).

**Tracks:** V1 clips · V2 overlays (logo, UI flashes, team logos) · V3 FX
(flashes, light leaks) · Text · A1 music · A2 SFX.

Run **Beat → Auto-generate** on the music, then snap every cut to a beat marker.

| Time | Edit | Transition / effect | Text (style) | SFX |
|---|---|---|---|---|
| 0:00 | Black → H1 | Fade from black, 0.5 s | — | Sub swell ("Cinematic boom" at 0:00.3) |
| 0:01.5 | H1 continues | Glow effect, low | "PAKISTANI BRAWLHALLA PLAYERS…": Inter Black 92 pt, cream, animation *Typewriter* 1.2 s, out *Fade* at 3.9 | Soft typing tick |
| 0:04.0 | Cut to H2a | **Flash (white), 2 frames** + *Shake* effect 0.3 s | "YOUR NEXT RIVAL": 120 pt, in *Zoom in* (fast, 0.2 s) | Impact + Whoosh |
| 0:06.0 | H2b | Hard cut, *Chromatic aberration* 3 frames | "IS OUT THERE.": ember-red `#FF6A1F`, in *Pop up* | Impact |
| 0:06.8–0:08.8 | 3 × 0.4 s gameplay + H2b | Hard cuts on beats, 1-frame white impact frames, speed ramp (Curve → Bullet) on the last one | — | Punch hit on every cut, glass crack 0:08.5 |
| 0:09.0 | H3 | *Whip pan* transition 0.3 s; keyframe a colour adjustment red → emerald over 0.8 s | "FIND YOUR PEOPLE.": cream, *Blur in* | Whoosh, pad swell |
| 0:11.5 | H3b | *Zoom* transition | "BUILD YOUR RIVALRIES.": *Slide up*; city labels Inter Bold 36 pt pop on each node | Tick ×6 |
| 0:13.0 / 13.6 / 14.2 | UI flashes: City Wars, logos VS, Clan Wars | *Glitch* transition 0.15 s each; screens on a tilted 3D card (keyframe rotation ±8°) | Labels: CITY WARS / CLAN WARS / PAKISTAN RANKINGS, emerald, 54 pt | Digital sweep ×3, riser peaks |
| 0:14.7 | Cut to black | 0.3 s of silence | — | Silence (cut the music to zero) |
| **0:15.0** | **H4 + logo PNG** | **Flash (white) 3 frames, Shake (strong) 0.5 s**; keyframe the logo scale 160% → 100% over 6 frames; *Lens flare* overlay | — | **Drop + "Huge impact"** |
| 0:17.0 | H4 continues, logo drifts | Slow keyframed push 100% → 106% | "REPRESENT YOUR CITY.": 96 pt, *Slide up*, under the logo | — |
| 0:19.0 | — | — | "BECOME PART OF BRAWLISTAN.": "BRAWLISTAN" in `#3DF26E` | Reverse cymbal into 0:21 |
| 0:21.0 | H5 | *Dissolve* 0.4 s | "YOUR COMMUNITY IS WAITING.": 104 pt, centred, *Fade in* | Pad swell |
| 0:23.5 | End card PNG over H5 (blend Screen at 0% → Normal) | Card *Slide up* 0.4 s with a slight bounce; keyframe a breathing glow (light leak overlay at 30%) | (on the card) | Whoosh + click |
| 0:29.0 | Hold | White flash 2 frames at 20% opacity | — | Final impact, ring-out |
| 0:30.0 | End | — | — | Music out |

**Text rules:** at most 5 words on screen at a time, all caps, Inter Black,
and hold each line for at least 1.2 s. Keep text inside the middle 80% of the
frame.

**Export:** 1080×1920 and 1920×1080, 30 fps, high bitrate. Upload the 9:16 to
TikTok, Reels, Shorts and WhatsApp Status, and the 16:9 to YouTube and the
Discord #announcements channel.

---

## 9. Alternative opening hooks (first 2 seconds)

1. **"PAKISTAN, IT'S TIME TO FIGHT."** Black frame, three hard impacts, one word
   per beat (PAKISTAN · IT'S TIME · TO FIGHT.), then a white flash into Scene 2.
   Direct, national, impossible to scroll past.
2. **"KARACHI OR LAHORE?"** Two city names slam in from opposite sides and crash
   in the middle with a spark burst. Sub-line: *Who's got the better Brawlhalla
   players?* City rivalry is the strongest bait in Pakistan, and City Wars
   actually answers the question.
3. **"STILL PLAYING BRAWLHALLA ALONE?"** A lone glowing screen in a dark room
   (or a solo player's real gameplay), a mouse click, silence, then a Discord
   notification ping and the screen floods emerald. It speaks straight to the
   player the server is for.

---

## 10. Social caption

```
Pakistani Brawlhalla players — find your fighters. 🇵🇰⚔️

BRAWLISTAN is where Pakistan's Brawlhalla scene lives: looking-for-game, City Wars, weekly Clan Wars and the Pakistan rankings.

Join the Discord 👉 discord.gg/UXVDWxBzy
🌐 brawlistan.rekorex.online

#Brawlhalla #BrawlhallaPakistan #PakistaniGamers #Brawlistan #Esports
```
