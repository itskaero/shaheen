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
