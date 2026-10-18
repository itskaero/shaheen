// Captures real screenshots of the BRAWLISTAN site for the explainer.
// Serve web/ first: python3 -m http.server 8090 --directory web
// Usage: node scripts/capture.mjs [baseUrl] [outDir]
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
let chromium;
try { ({ chromium } = require("playwright")); }
catch { ({ chromium } = require("/opt/node22/lib/node_modules/playwright")); }

const base = process.argv[2] || "http://127.0.0.1:8090";
const out = process.argv[3] || new URL("../public/shots/", import.meta.url).pathname;

const pages = [
  ["entrance", "index.html"],
  ["home", "home.html"],
  ["rankings", "rankings.html"],
  ["players", "players.html"],
  ["cities", "cities.html"],
  ["clanwars", "clanwars.html"],
  ["join", "join.html"],
  ["teams", "teams.html"],
  ["player-unclaimed", "player.html?p=arman-56008741"],
  ["player-claimed", "player.html?p=kaero-5734378"],
];

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1600, height: 900 }, deviceScaleFactor: 1.5, reducedMotion: "reduce" });
await ctx.addInitScript(() => { try { sessionStorage.setItem("bl-stale-dismissed", "1"); } catch {} });
const page = await ctx.newPage();
page.on("pageerror", (e) => console.warn("pageerror", e.message));
for (const [name, path] of pages) {
  await page.goto(`${base}/${path}`, { waitUntil: "networkidle", timeout: 60000 }).catch(() => {});
  await page.waitForTimeout(2500);
  // Hide the music toggle pill: it only invites a click, it isn't content.
  await page.addStyleTag({ content: "#bl-stale, .bl-music, [data-site-music], .site-music{display:none!important}" });
  await page.screenshot({ path: `${out}${name}.png` });
  await page.screenshot({ path: `${out}${name}-full.png`, fullPage: true });
  console.log("captured", name);
}
await browser.close();
