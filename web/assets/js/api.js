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

  // Cold-start cover (docs/DECISIONS.md ADR-087). The API runs on Render's
  // free tier, which sleeps after 15 minutes idle and can take 30-60s to
  // wake — so a first visitor used to sit on "Loading…" for a minute on
  // every data page. A scheduled GitHub Action writes the last known
  // response for each of these into web/data/*.json, which ships with the
  // site and therefore loads instantly from the same origin.
  //
  // withSnapshot renders that immediately, then refreshes from the live API
  // and re-renders. If the live call fails but the snapshot rendered, the
  // page keeps the snapshot and says how old it is rather than throwing
  // away good data for an error message.
  async function loadSnapshot(name) {
    try {
      const response = await fetch(`data/${encodeURIComponent(name)}.json`, {
        cache: "no-cache",
      });
      if (!response.ok) {
        return null;
      }
      const payload = await response.json();
      return payload && payload.data !== undefined ? payload : null;
    } catch {
      // No snapshot committed yet, or the site is being opened from file://.
      return null;
    }
  }

  async function withSnapshot(name, liveFetch, render) {
    const snapshot = await loadSnapshot(name);
    if (snapshot) {
      render(snapshot.data, { live: false, capturedAt: snapshot.captured_at });
    }
    try {
      render(await liveFetch(), { live: true, capturedAt: null });
    } catch (err) {
      if (!snapshot) {
        throw err;
      }
      console.warn(`[shaheen] live refresh of ${name} failed (${err.message}); showing snapshot.`);
    }
  }

  return {
    withSnapshot,
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

// The live community badge. Two sources, in order of preference
// (docs/DECISIONS.md ADR-066 -> ADR-082 -> ADR-086):
//
//   1. Discord's own public widget endpoint — real *online* count, but it
//      only answers if "Enable Server Widget" is switched on in Discord's
//      Server Settings -> Widget. That is a portal toggle outside this
//      repo, and for three rounds it was the single point of failure: with
//      it off the badge simply never appeared.
//   2. Shaheen's own API (`GET /clan`) — the bot writes a guild snapshot
//      (member count, boost tier) into the database on every scheduled
//      tick (ADR-079), so the site can show a real *member* count with no
//      Discord involvement at all. This is the fallback, so the badge is
//      no longer hostage to a setting nobody can verify from here.
//
// Nothing here can break a page: on total failure the badge stays hidden.
// Append ?widget-debug=1 to any URL to render the failure reason in the
// badge itself instead of hiding it — for diagnosing this without opening
// devtools.
function discordWidgetDebugEnabled() {
  try {
    return new URLSearchParams(window.location.search).has("widget-debug");
  } catch {
    return false;
  }
}

function renderDiscordBadge(targets, label) {
  targets.forEach((el) => {
    el.innerHTML = `<span class="dot" aria-hidden="true"></span>${label}`;
    el.hidden = false;
  });
}

function failDiscordBadge(targets, reason, debug) {
  console.warn(`[shaheen] Discord widget: ${reason}`);
  if (debug) {
    targets.forEach((el) => {
      el.textContent = `widget: ${reason}`;
      el.hidden = false;
    });
  }
}

// Returns an online count, or null with the reason logged.
async function fetchDiscordOnlineCount(targets, debug) {
  if (typeof DISCORD_GUILD_ID === "undefined" || !DISCORD_GUILD_ID) {
    failDiscordBadge(targets, "DISCORD_GUILD_ID is not set in assets/js/config.js.", debug);
    return null;
  }
  let response;
  try {
    response = await fetch(
      `https://discord.com/api/guilds/${encodeURIComponent(DISCORD_GUILD_ID)}/widget.json`
    );
  } catch (err) {
    failDiscordBadge(targets, `request failed (${err.message}).`, debug);
    return null;
  }
  if (!response.ok) {
    if (response.status === 403) {
      failDiscordBadge(
        targets,
        "the server widget is disabled. Enable it in Discord under Server Settings -> " +
          "Widget -> Enable Server Widget.",
        debug
      );
    } else if (response.status === 404) {
      failDiscordBadge(
        targets,
        `no guild found for ID ${DISCORD_GUILD_ID}. Check DISCORD_GUILD_ID in ` +
          "assets/js/config.js.",
        debug
      );
    } else {
      failDiscordBadge(targets, `Discord returned HTTP ${response.status}.`, debug);
    }
    return null;
  }

  const widget = await response.json();
  // presence_count is the real online total, and a genuine 0 from it is
  // real data worth showing. widget.members is capped at 100 by Discord and
  // omits members who opted out, so it is only a fallback — and an empty one
  // counts as "no usable signal" rather than zero, since Discord always
  // sends presence_count on a healthy response. That keeps a malformed reply
  // from rendering a misleading "0 online now".
  if (typeof widget.presence_count === "number") {
    return widget.presence_count;
  }
  if (Array.isArray(widget.members) && widget.members.length > 0) {
    return widget.members.length;
  }
  failDiscordBadge(
    targets,
    "response carried no usable online count (no presence_count, no members).",
    debug
  );
  return null;
}

async function wireDiscordWidgets() {
  const targets = document.querySelectorAll("[data-discord-widget]");
  if (!targets.length) {
    return;
  }
  const debug = discordWidgetDebugEnabled();

  const online = await fetchDiscordOnlineCount(targets, debug);
  if (online !== null) {
    renderDiscordBadge(targets, `${online.toLocaleString()} online now`);
    return;
  }

  // Discord said no. Fall back to the member count the bot recorded.
  try {
    const clan = await ShaheenAPI.getClan();
    if (clan && typeof clan.discord_member_count === "number") {
      renderDiscordBadge(targets, `${clan.discord_member_count.toLocaleString()} members`);
      return;
    }
    failDiscordBadge(
      targets,
      "fallback: Shaheen's API has no guild snapshot yet (the bot writes one on its " +
        "scheduled tick).",
      debug
    );
  } catch (err) {
    failDiscordBadge(targets, `fallback to Shaheen's API also failed (${err.message}).`, debug);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  setYear();
  wireDiscordLink();
  wireDiscordWidgets();
});
