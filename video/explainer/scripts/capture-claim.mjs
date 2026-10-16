// Captures the real "Claim this profile" UI on player.html, driven by a
// DEMO player ("YourName", Brawlhalla id 10000001) served from a mocked API.
// No real player is shown claiming anything. Serve web/ on :8090 first.
import { createRequire } from "node:module";
import { readFileSync } from "node:fs";
const require = createRequire(import.meta.url);
let chromium;
try { ({ chromium } = require("playwright")); }
catch { ({ chromium } = require("/opt/node22/lib/node_modules/playwright")); }

const base = process.argv[2] || "http://127.0.0.1:8090";
const web = new URL("../../../web/", import.meta.url).pathname;
const out = process.argv[3] || new URL("../public/shots/", import.meta.url).pathname;
const ID = 10000001;
const demoRow = {
  brawlhalla_id: ID, player_name: "YourName", country: "PK", team: null, team_slug: null, team_tag: null,
  is_claimed: false, is_verified: false, region: "SEA", rating: 1500, peak_rating: 1540, tier: "Gold 3",
  wins: 40, games: 80, global_rank: null, region_rank: null, rating_2v2: null, peak_rating_2v2: null,
  tier_2v2: null, partner_2v2: null, trend: 0, main_legend: "jaeyun", city: null, city_label: null,
};
const demoDir = { ...demoRow, slug: "yourname-10000001", on_pakistan_board: true };

function snapshot(name, mutate) {
  const json = JSON.parse(readFileSync(`${web}data/${name}.json`, "utf8"));
  mutate(json.data);
  return JSON.stringify(json);
}

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1600, height: 900 }, deviceScaleFactor: 1.5, reducedMotion: "reduce" });
await ctx.addInitScript(() => { try { sessionStorage.setItem("bl-stale-dismissed", "1"); } catch {} });
await ctx.route("**/data/rankings.json", (r) => r.fulfill({ contentType: "application/json", body: snapshot("rankings", (d) => d.rows.push(demoRow)) }));
await ctx.route("**/data/players.json", (r) => r.fulfill({ contentType: "application/json", body: snapshot("players", (d) => d.push(demoDir)) }));
await ctx.route("https://api-brawlistan.rekorex.online/**", async (r) => {
  const url = new URL(r.request().url());
  const p = url.pathname;
  const json = (body, status = 200) => r.fulfill({ status, contentType: "application/json", body: JSON.stringify(body), headers: { "access-control-allow-origin": "*" } });
  if (r.request().method() === "OPTIONS") return r.fulfill({ status: 204, headers: { "access-control-allow-origin": "*", "access-control-allow-methods": "GET,POST", "access-control-allow-headers": "content-type" } });
  if (p === `/players/${ID}`) return json({ brawlhalla_id: ID, player_name: "YourName", region: "SEA", rating: 1500, peak_rating: 1540, tier: "Gold 3", global_rank: null, region_rank: null, season: 42, pakistan_season: null, achievements: [], playstyle_tags: [] });
  if (p.startsWith(`/players/${ID}/`)) return json([]);
  if (p === "/link/claim") return json({ brawlhalla_id: ID, player_name: "YourName" });
  return r.fulfill({ status: 503, body: "", headers: { "access-control-allow-origin": "*" } });
});
const page = await ctx.newPage();
page.on("pageerror", (e) => console.warn("pageerror", e.message));
await page.goto(`${base}/player.html?p=yourname-10000001`, { waitUntil: "networkidle" });
await page.waitForTimeout(2000);
await page.addStyleTag({ content: "#bl-stale{display:none!important}" });
await page.addStyleTag({ content: ".bl-music,.site-music,[class*=music-toggle]{display:none!important}" });
// Element shots: the profile header, then the Discord panel in its three states.
await page.locator(".profile-head").screenshot({ path: `${out}claim-head.png` });
const panel = page.locator("section", { has: page.locator("#claim-result") }).last();
await panel.scrollIntoViewIfNeeded();
await page.waitForTimeout(300);
await panel.screenshot({ path: `${out}claim-1-form.png` });
await page.fill("#claim-code", "ABCD-EFGH");
await page.locator("#claim-code").blur();
await panel.screenshot({ path: `${out}claim-2-typed.png` });
const pb = await panel.boundingBox();
const bb = await page.locator('#claim-form button[type="submit"]').boundingBox();
const ib = await page.locator("#claim-code").boundingBox();
console.log(JSON.stringify({ panel: pb, button: bb, input: ib }));
await page.click('#claim-form button[type="submit"]');
await page.waitForTimeout(800);
await panel.screenshot({ path: `${out}claim-3-linked.png` });
console.log(await page.locator("#claim-result").innerText());
await browser.close();
