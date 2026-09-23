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

const RANK_MEDALS = ["gold", "silver", "bronze"];

function rankHtml(position) {
  const medal = RANK_MEDALS[position - 1];
  if (medal) {
    return `<span class="rank-medal rank-${medal}">${position}</span>`;
  }
  return `<span class="rank-plain">#${position}</span>`;
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
      <img class="season-badge" src="${badge}.png" alt="Season of ${escapeHtml(season.name)} badge" width="152" height="136" />
    </picture>
    <div class="season-copy">
      <span class="season-kicker">Pakistan Season ${season.number}</span>
      <h2 class="season-name">Season of <span class="season-name-word">${escapeHtml(season.name)}</span></h2>
      <span class="season-urdu" lang="ur">${escapeHtml(season.name_urdu)}</span>
      <span class="season-meta">Brawlhalla Season ${season.brawlhalla_season} &middot; until about ${until} &middot; a new season every 13 weeks</span>
    </div>`;
}
