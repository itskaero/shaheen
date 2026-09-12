// Thin fetch wrapper around Shaheen's public API (src/api/). Mirrors the
// response shapes in src/api/schemas.py — kept in sync by hand since this
// is a plain static site with no shared type generation.

// Render's free tier sleeps after 15 min idle and can take ~30-60s to wake
// on the next request (README.md's "Deploying to production" section) —
// without a timeout, a cold-start request and a genuinely broken one look
// identical to a page: both just sit on "Loading…" forever. This gives
// every request an upper bound so the UI can tell the difference.
const REQUEST_TIMEOUT_MS = 50_000;

const ShaheenAPI = (() => {
  async function get(path) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
    let response;
    try {
      response = await fetch(`${API_BASE_URL}${path}`, {
        headers: { Accept: "application/json" },
        signal: controller.signal,
      });
    } catch (err) {
      if (err.name === "AbortError") {
        throw new Error("Shaheen's server is waking up — try again in a moment.");
      }
      throw err;
    } finally {
      clearTimeout(timeout);
    }
    if (response.status === 404) {
      return null;
    }
    if (!response.ok) {
      throw new Error(`Request to ${path} failed (${response.status})`);
    }
    return response.json();
  }

  return {
    getClan: () => get("/clan"),
    getLeaderboard: (limit = 25) => get(`/leaderboard?limit=${limit}`),
    getRoster: () => get("/roster"),
    getAchievements: () => get("/achievements"),
    getPlayer: (brawlhallaId) => get(`/players/${encodeURIComponent(brawlhallaId)}`),
    getPlayerHistory: (brawlhallaId, limit = 20) =>
      get(`/players/${encodeURIComponent(brawlhallaId)}/history?limit=${limit}`),
    getPlayerLegends: (brawlhallaId, limit = 6) =>
      get(`/players/${encodeURIComponent(brawlhallaId)}/legends?limit=${limit}`),
    getPlayerMatches: (brawlhallaId, limit = 10) =>
      get(`/players/${encodeURIComponent(brawlhallaId)}/matches?limit=${limit}`),
    getTournaments: (limit = 20) => get(`/tournaments?limit=${limit}`),
    getTournamentBracket: (id) => get(`/tournaments/${encodeURIComponent(id)}`),
    getCommunityActivity: (limit = 10) => get(`/community/activity?limit=${limit}`),
  };
})();

function formatTier(tier) {
  return tier || "Unranked";
}

function formatNumber(value) {
  return value === null || value === undefined ? "—" : value.toLocaleString();
}

function formatDate(isoString) {
  return new Date(isoString).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = value;
  return div.innerHTML;
}

function setYear() {
  const el = document.getElementById("year");
  if (el) {
    el.textContent = new Date().getFullYear();
  }
}

function wireDiscordLink() {
  const link = document.getElementById("discord-link");
  if (!link) {
    return;
  }
  if (typeof DISCORD_INVITE_URL !== "undefined" && DISCORD_INVITE_URL) {
    link.href = DISCORD_INVITE_URL;
    link.hidden = false;
  }
}

// Live member/online-count badge, fed by Discord's own public widget
// endpoint (docs/DECISIONS.md ADR-066) — no bot/API involvement at all.
// Best-effort only: silently stays hidden if DISCORD_GUILD_ID isn't set,
// the widget isn't enabled on the server, or the request fails for any
// reason. Fills every element carrying [data-discord-widget] on the page
// (the header and footer both have one).
async function wireDiscordWidgets() {
  const targets = document.querySelectorAll("[data-discord-widget]");
  if (!targets.length || typeof DISCORD_GUILD_ID === "undefined" || !DISCORD_GUILD_ID) {
    return;
  }
  try {
    const response = await fetch(
      `https://discord.com/api/guilds/${encodeURIComponent(DISCORD_GUILD_ID)}/widget.json`
    );
    if (!response.ok) {
      return;
    }
    const widget = await response.json();
    const online = Array.isArray(widget.members) ? widget.members.length : 0;
    targets.forEach((el) => {
      el.innerHTML = `<span class="dot" aria-hidden="true"></span>${online.toLocaleString()} online now`;
      el.hidden = false;
    });
  } catch {
    // Widget disabled, network hiccup, whatever — the badge just never
    // appears. Never surface an error for a purely decorative element.
  }
}

document.addEventListener("DOMContentLoaded", () => {
  setYear();
  wireDiscordLink();
  wireDiscordWidgets();
});
