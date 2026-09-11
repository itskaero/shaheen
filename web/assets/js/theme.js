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
  return legendNameKey
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
