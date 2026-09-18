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
    getPlayerAchievements: (brawlhallaId) =>
      get(`/players/${encodeURIComponent(brawlhallaId)}/achievements`),
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
  if (typeof DISCORD_INVITE_URL === "undefined" || !DISCORD_INVITE_URL) {
    return;
  }

  // The header CTA, hidden until there's an invite to point it at.
  const link = document.getElementById("discord-link");
  if (link) {
    link.href = DISCORD_INVITE_URL;
    link.hidden = false;
  }

  // Any other in-content invite button opts in with [data-discord-invite]
  // rather than hardcoding the URL. join.html had the invite written into
  // its markup twice and both copies went stale when the invite changed
  // (ADR-082) — config.js is the single source of truth now.
  document.querySelectorAll("[data-discord-invite]").forEach((el) => {
    el.href = DISCORD_INVITE_URL;
  });
}

// Live member/online-count badge, fed by Discord's own public widget
// endpoint (docs/DECISIONS.md ADR-066, diagnostics added in ADR-082) — no
// bot/API involvement at all. Best-effort: the badge stays hidden if
// DISCORD_GUILD_ID isn't set, the widget isn't enabled on the server, or
// the request fails. Fills every element carrying [data-discord-widget]
// on the page (header, footer, and clan.html's injected third one).
//
// Failures are no longer silent. Every bail-out logs a specific reason,
// because the previous version's bare `return`/`catch {}` made "widget
// disabled" indistinguishable from "wrong guild ID" from "network error"
// without opening the Network tab — which is exactly the state that left
// this badge dark and undiagnosed for three rounds.
async function wireDiscordWidgets() {
  const targets = document.querySelectorAll("[data-discord-widget]");
  if (!targets.length) {
    return;
  }
  if (typeof DISCORD_GUILD_ID === "undefined" || !DISCORD_GUILD_ID) {
    console.warn("[shaheen] Discord widget: DISCORD_GUILD_ID is not set in assets/js/config.js.");
    return;
  }
  try {
    const response = await fetch(
      `https://discord.com/api/guilds/${encodeURIComponent(DISCORD_GUILD_ID)}/widget.json`
    );
    if (!response.ok) {
      if (response.status === 403) {
        console.warn(
          "[shaheen] Discord widget: the server widget is disabled. Enable it in Discord under " +
            "Server Settings -> Widget -> Enable Server Widget."
        );
      } else if (response.status === 404) {
        console.warn(
          `[shaheen] Discord widget: no guild found for ID ${DISCORD_GUILD_ID}. Check ` +
            "DISCORD_GUILD_ID in assets/js/config.js."
        );
      } else {
        console.warn(`[shaheen] Discord widget: Discord returned HTTP ${response.status}.`);
      }
      return;
    }
    const widget = await response.json();
    // presence_count is the real online total, and a genuine 0 from it is
    // real data worth showing. widget.members is capped at 100 by Discord
    // and omits members who opted out, so it's only a fallback — and an
    // empty one is treated as "no usable signal" rather than zero, since
    // Discord always sends presence_count on a healthy response. That
    // keeps a malformed reply from rendering a misleading "0 online now".
    let online = null;
    if (typeof widget.presence_count === "number") {
      online = widget.presence_count;
    } else if (Array.isArray(widget.members) && widget.members.length > 0) {
      online = widget.members.length;
    }
    if (online === null) {
      console.warn(
        "[shaheen] Discord widget: response carried no usable online count " +
          "(no presence_count, no members)."
      );
      return;
    }
    targets.forEach((el) => {
      el.innerHTML = `<span class="dot" aria-hidden="true"></span>${online.toLocaleString()} online now`;
      el.hidden = false;
    });
  } catch (err) {
    console.warn(`[shaheen] Discord widget: request failed (${err.message}).`);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  setYear();
  wireDiscordLink();
  wireDiscordWidgets();
});
