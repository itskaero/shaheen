// Thin fetch wrapper around Shaheen's public API (src/api/). Mirrors the
// response shapes in src/api/schemas.py — kept in sync by hand since this
// is a plain static site with no shared type generation.

const ShaheenAPI = (() => {
  async function get(path) {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      headers: { Accept: "application/json" },
    });
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

document.addEventListener("DOMContentLoaded", setYear);
