# Holographic cards (docs/DECISIONS.md ADR-117)

WebGPU holographic cards for the BRAWLISTAN site, built on the official vGPU
`holographic-card` example (verbatim copy and provenance in `upstream/`).

| File | What it is |
|---|---|
| `shader.wgsl` | The example's fragment shader, adapted: team colours, logo artwork instead of baked text, transparent backdrop. The optics are unchanged. |
| `scene.ts` | Creates the effect and uploads the logo texture. |
| `renderer.ts` | One shared GPU for the page: surfaces, pooled effects, shared textures, a single frame loop that only runs for visible, moving cards, device-loss fallback. |
| `pointer.ts`, `color.ts` | Pure helpers (upstream pointer maths, hex colours), unit-tested. |
| `index.ts` | DOM layer: mounts every `[data-holo]` element, follows DOM changes, CSS fallback without WebGPU. |

Build and check (Node 22+):

    npm install
    npm run build   # -> web/assets/js/holo.js (commit it: Pages serves web/ as-is)
    npm run lint    # tsc
    npm test        # node --test

Card markup is produced by `holoTeamCardHtml()` in `web/assets/js/theme.js`
(team cards) or written directly (the landing identity card in `index.html`).
