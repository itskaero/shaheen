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
    getPlayer: (brawlhallaId) => get(`/players/${encodeURIComponent(brawlhallaId)}`),
    getPlayerHistory: (brawlhallaId, limit = 20) =>
      get(`/players/${encodeURIComponent(brawlhallaId)}/history?limit=${limit}`),
    getPlayerLegends: (brawlhallaId, limit = 6) =>
      get(`/players/${encodeURIComponent(brawlhallaId)}/legends?limit=${limit}`),
    getPlayerMatches: (brawlhallaId, limit = 10) =>
      get(`/players/${encodeURIComponent(brawlhallaId)}/matches?limit=${limit}`),
    getTournaments: (limit = 20) => get(`/tournaments?limit=${limit}`),
    getTournamentBracket: (id) => get(`/tournaments/${encodeURIComponent(id)}`),
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

document.addEventListener("DOMContentLoaded", () => {
  setYear();
  wireDiscordLink();
});
