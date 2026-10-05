// Visual helpers shared by the leaderboard/player pages — tier badges,
// deterministic player avatars, and top-3 rank medals. Pure presentation,
// no network calls.

const TIER_META = [
  { match: /valhallan/i, label: "Valhallan", cls: "tier-valhallan" },
  { match: /diamond/i, label: "Diamond", cls: "tier-diamond" },
  { match: /platinum/i, label: "Platinum", cls: "tier-platinum" },
  { match: /gold/i, label: "Gold", cls: "tier-gold" },
  { match: /silver/i, label: "Silver", cls: "tier-silver" },
  { match: /bronze/i, label: "Bronze", cls: "tier-bronze" },
  { match: /tin/i, label: "Tin", cls: "tier-tin" },
];

function tierMeta(tier) {
  if (!tier) {
    return { label: "Unranked", cls: "tier-unranked" };
  }
  const found = TIER_META.find((t) => t.match.test(tier));
  return found ? { label: tier, cls: found.cls } : { label: tier, cls: "tier-unranked" };
}

function tierBadge(tier) {
  const meta = tierMeta(tier);
  return `<span class="tier-badge ${meta.cls}">${escapeHtml(meta.label)}</span>`;
}

// Deterministic hue from a player's name so the same player always gets the
// same avatar color across visits, without storing anything.
function nameHue(name) {
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = (hash << 5) - hash + name.charCodeAt(i);
    hash |= 0;
  }
  return Math.abs(hash) % 360;
}

function avatarHtml(name, size = 44) {
  const hue = nameHue(name || "?");
  const initial = (name || "?").trim().charAt(0).toUpperCase() || "?";
  const style = `width:${size}px;height:${size}px;font-size:${size * 0.42}px;background:linear-gradient(155deg, hsl(${hue} 55% 24%), hsl(${(hue + 40) % 360} 45% 14%));`;
  return `<span class="avatar" style="${style}">${escapeHtml(initial)}</span>`;
}

// Portrait art for the roster, cut from the owner's Legend sheet
// (docs/DECISIONS.md ADR-098) — the same crops the bot renders into its
// /profile and /legends strips. A Legend missing from this set (a new
// release) falls back to the initial avatar, never a broken image.
const LEGEND_PORTRAITS = new Set([
  "ada", "asuri", "aurus", "azoth", "baobao", "barraza", "bodvar", "brynn", "caspian",
  "cassidy", "cross", "diana", "ember", "ezio", "fait", "gnash", "hattori", "imugi", "jaeyun",
  "jhala", "jiro", "kaya", "king_zuva", "koji", "kor", "lady_vera", "lin_fei", "loki",
  "lord_vraxx", "lucien", "magyar", "mako", "mirage", "mordex", "munin", "nix", "onyx",
  "orion", "petra", "priya", "qinghua", "queen_nai", "ragnir", "ransom", "rayman", "reno",
  "rupture", "sandstorm", "scarlet", "sentinel", "seven", "sidra", "sir_roland", "teros",
  "tezca", "thatch", "thea", "ulgrim", "val", "vector", "volkov", "wu_shang", "xull", "yumiko",
  "zariel",
]);

// The API's legend_name_key is lowercase but a multi-word Legend may come
// through with a space or an underscore ("lord vraxx" / "lord_vraxx"), and
// Bödvar may keep its umlaut — portraits are named in the underscored form.
function normalizeLegendKey(legendNameKey) {
  return (legendNameKey || "")
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[-_]/g, " ")
    .trim()
    .split(/\s+/)
    .join("_");
}

function legendPortraitUrl(legendNameKey) {
  const key = normalizeLegendKey(legendNameKey);
  return LEGEND_PORTRAITS.has(key) ? `assets/img/legend-portraits/${key}.webp` : null;
}

function legendAvatarHtml(legendNameKey, size = 32) {
  const url = legendPortraitUrl(legendNameKey);
  if (url) {
    return `<img class="legend-avatar" src="${url}" alt="" width="${size}" height="${size}" loading="lazy" />`;
  }
  return avatarHtml(legendDisplayName(legendNameKey), size);
}

// Rank chip (brawlistan.css): the top three get a subtle medal tint and
// nothing louder (docs/DECISIONS.md ADR-104).
function rankHtml(position) {
  const medal = position >= 1 && position <= 3 ? ` rank-${position}` : "";
  return `<span class="rank${medal}">${position}</span>`;
}

// Same heuristic as src/bot/content/profile_embeds.py's _legend_display_name
// — the API sends the raw legend_name_key (e.g. "wu_shang"), not a display
// name, so both surfaces format it the same simple way.
function legendDisplayName(legendNameKey) {
  return normalizeLegendKey(legendNameKey)
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

// Chat-gamification rank titles (services/chat_gamification.py's
// RANK_TITLES, docs/DECISIONS.md ADR-065/066) — a badge in the same visual
// language as tierBadge() above, keyed to its own CSS class set
// (.rank-hatchling..rank-valhallan in style.css) since this is a distinct
// ladder from Brawlhalla's own ranked tiers.
const CHAT_RANK_CLASS = {
  Hatchling: "rank-hatchling",
  Brawler: "rank-brawler",
  Warrior: "rank-warrior",
  Veteran: "rank-veteran",
  Elite: "rank-elite",
  Legend: "rank-legend",
  Valhallan: "rank-valhallan",
};

function chatRankBadge(rankTitle) {
  const cls = CHAT_RANK_CLASS[rankTitle] || "rank-hatchling";
  return `<span class="rank-title-badge ${cls}">${escapeHtml(rankTitle)}</span>`;
}

// Mirrors services/chat_gamification.py's xp_for_level exactly (xp_for_level(n)
// = 100 * (n-1)**2) — used only to compute progress-to-next-level for the
// Community Activity progress bar; the API itself sends level/xp/rank_title,
// not a next-level threshold, so this stays a tiny duplicated pure function
// rather than a new API field for one progress bar.
function xpForLevel(level) {
  return level <= 1 ? 0 : 100 * (level - 1) ** 2;
}

// Pakistan Season banner (docs/DECISIONS.md ADR-102). `season` is the API's
// pakistan_season object; names and badge keys come from the server so the
// site never keeps its own copy of the season list.
function seasonBannerHtml(season) {
  if (!season) return "";
  const until = new Date(season.ends_at).toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
  const badge = `assets/img/seasons/${encodeURIComponent(season.badge)}`;
  return `
    <picture>
      <source srcset="${badge}.webp" type="image/webp" />
      <img class="season-badge" src="${badge}.jpg" alt="Season of ${escapeHtml(season.name)} card" width="152" height="136" />
    </picture>
    <div class="season-copy">
      <span class="season-kicker">Pakistan Season ${season.number}</span>
      <h2 class="season-name">Season of <span class="season-name-word">${escapeHtml(season.name)}</span></h2>
      <span class="season-urdu" lang="ur">${escapeHtml(season.name_urdu)}</span>
      <span class="season-meta">Brawlhalla Season ${season.brawlhalla_season} &middot; until about ${until} &middot; a new season every 13 weeks</span>
    </div>`;
}

// A team pill that links to the team's page (ADR-114); plain text when the
// team has no slug.
function teamPillHtml(name, slug, extraClass = "") {
  if (!name) return "";
  const cls = `pill pill-team${extraClass ? ` ${extraClass}` : ""}`;
  return slug
    ? `<a class="${cls}" href="${teamHref(slug)}">${escapeHtml(name)}</a>`
    : `<span class="${cls}">${escapeHtml(name)}</span>`;
}

// "[SHN]" before a player's name, when they wear their team tag (ADR-115).
// The Rankings page can hide every tag (body.hide-tags).
function tagChipHtml(tag) {
  return tag ? `<span class="clan-tag" title="Team tag">[${escapeHtml(tag)}]</span> ` : "";
}

// A team's page: the pre-rendered teams/<slug>/ (scripts/team_pages.py, ADR-117).
function teamHref(slug) {
  return `teams/${encodeURIComponent(slug)}/`;
}

const HOLO_DEFAULT_ACCENTS = ["#3df26e", "#f0168c"];

function hexToRgbList(hex, fallback) {
  const m = /^#?([0-9a-f]{6})$/i.exec(hex || "");
  const v = m ? m[1] : fallback.replace("#", "");
  return [0, 2, 4].map((i) => parseInt(v.slice(i, i + 2), 16)).join(", ");
}

// HolographicTeamCard (ADR-117): the WebGPU card from assets/js/holo.js with
// the team's logo and colours; every word on it is this HTML. `link` makes
// the whole card one link (nothing inside may then be a link).
function holoTeamCardHtml(team, { link = true, dpr = 1.5, ambient = 0.28, cta = "View team" } = {}) {
  const [a1, a2] = [team.accent || HOLO_DEFAULT_ACCENTS[0], team.accent_secondary || HOLO_DEFAULT_ACCENTS[1]];
  const art = team.logo ? `assets/img/teams/${encodeURIComponent(team.logo)}.webp` : "";
  const fallbackArt = team.logo
    ? `<img class="holo-fallback-art" src="assets/img/teams/${encodeURIComponent(team.logo)}.webp" alt="" loading="lazy" />`
    : `<span class="holo-fallback-art team-monogram" aria-hidden="true">${escapeHtml(team.tag)}</span>`;
  const position = team.rank ? `#${team.rank}` : "";
  const rank = team.is_founding ? `${position} Founding`.trim() : position ? `${position} team` : "Unranked";
  const country = team.country === "PK" ? "🇵🇰 Pakistan" : escapeHtml(team.country || "");
  const tag = link ? "a" : "div";
  const attrs = link
    ? `href="${teamHref(team.slug)}" aria-label="${escapeHtml(team.name)}, ${escapeHtml(rank)}, view team"`
    : `aria-label="${escapeHtml(team.name)} team card"`;
  return `<${tag} class="holo-card team-holo${team.is_founding ? " is-founding" : ""}" ${attrs}
      data-holo ${art ? `data-holo-art="${art}"` : ""} data-holo-accent="${a1}" data-holo-accent2="${a2}"
      data-holo-ambient="${ambient}" data-holo-dpr="${dpr}"
      style="--accent: ${hexToRgbList(a1, HOLO_DEFAULT_ACCENTS[0])}; --accent-2: ${hexToRgbList(a2, HOLO_DEFAULT_ACCENTS[1])}">
    <div class="holo-stage">
      <canvas class="holo-canvas" aria-hidden="true"></canvas>
      <div class="holo-face">
        <div class="holo-fallback" aria-hidden="true">${fallbackArt}</div>
        <div class="holo-content">
          <p class="holo-meta"><span class="holo-tag">[${escapeHtml(team.tag)}]</span><span>${country}</span><span>${escapeHtml(rank)}</span></p>
          <h3 class="holo-title">${escapeHtml(team.name)}</h3>
          <div class="holo-stats">
            <div><strong>${team.rating != null ? formatNumber(team.rating) : "—"}</strong><span>Power</span></div>
            <div><strong>${formatNumber(team.members)}</strong><span>Players</span></div>
          </div>
          ${link && cta ? `<span class="holo-cta">${escapeHtml(cta)} &rarr;</span>` : ""}
        </div>
      </div>
    </div>
  </${tag}>`;
}
