// BRAWLISTAN Players directory (docs/DECISIONS.md ADR-106): every tracked
// player as cards (after the owner's Members reference) or a dense list.
// Search covers name, team and country; the sidebar search lands here as
// ?q=. The chosen view is remembered per browser.
(function () {
  const el = document.getElementById("players");
  const count = document.getElementById("players-count");
  const search = document.getElementById("p-search");
  const team = document.getElementById("p-team");
  const country = document.getElementById("p-country");
  const claimed = document.getElementById("p-claimed");
  const VIEW_KEY = "brawlistan.players.view";
  const COUNTRIES = { PK: "Pakistan" };

  let players = null;
  let view = "grid";
  try {
    view = localStorage.getItem(VIEW_KEY) === "list" ? "list" : "grid";
  } catch {
    /* storage blocked: default view */
  }

  const initialQuery = new URLSearchParams(location.search).get("q");
  if (initialQuery) search.value = initialQuery;

  function profileHref(p) {
    return `player.html?p=${encodeURIComponent(p.slug)}`;
  }

  function countryName(code) {
    return code ? COUNTRIES[code] || code : null;
  }

  function rolePill(p) {
    if (p.team) return teamPillHtml(p.team, p.team_slug, "card-pill");
    if (p.is_verified) return '<span class="pill pill-verified card-pill">✓ Verified</span>';
    if (p.is_claimed) return '<span class="pill pill-muted card-pill">Claimed</span>';
    return '<span class="pill pill-muted card-pill">Unclaimed</span>';
  }

  function matches(p) {
    const q = search.value.trim().toLowerCase();
    if (q) {
      const haystack = [p.player_name, p.team, p.country, countryName(p.country)].filter(Boolean).join(" ").toLowerCase();
      if (!haystack.includes(q)) return false;
    }
    if (team.value === "_none" && p.team) return false;
    if (team.value && team.value !== "_none" && p.team !== team.value) return false;
    if (country.value === "_none" && p.country) return false;
    if (country.value && country.value !== "_none" && p.country !== country.value) return false;
    if (claimed.checked && !p.is_claimed) return false;
    return true;
  }

  function gridHtml(list) {
    return `<div class="player-grid">${list
      .map(
        (p) => `<a class="player-card" href="${profileHref(p)}">
          ${rolePill(p)}
          ${avatarHtml(p.player_name, 76)}
          <h3>${escapeHtml(p.player_name)}</h3>
          <span class="sub">${p.country === "PK" ? "🇵🇰 " : ""}${escapeHtml(countryName(p.country) || "Country not set")}${p.region ? ` · ${escapeHtml(p.region)}` : ""}</span>
          <div class="card-stats">
            <div><strong class="num">${formatNumber(p.rating)}</strong><span>Rating</span></div>
            <div><strong title="${escapeHtml(p.tier || "Unranked")}">${p.tier ? escapeHtml(p.tier.split(" ")[0]) : "Unranked"}</strong><span>Tier</span></div>
            <div><strong>${p.main_legend ? escapeHtml(legendDisplayName(p.main_legend)) : "—"}</strong><span>Main</span></div>
          </div>
        </a>`
      )
      .join("")}</div>`;
  }

  function listHtml(list) {
    return `<div class="panel panel-pad"><div class="bl-table-wrap"><table class="bl-table">
      <caption class="sr-only">Players</caption>
      <thead><tr>
        <th scope="col">Player</th><th scope="col" class="hide-sm">Country</th><th scope="col" class="hide-sm">Team</th>
        <th scope="col" class="right">Rating</th><th scope="col" class="hide-sm">Tier</th><th scope="col" class="hide-sm">Main legend</th>
      </tr></thead>
      <tbody>${list
        .map(
          (p) => `<tr>
            <td><a class="bl-player" href="${profileHref(p)}">${avatarHtml(p.player_name, 28)}<span class="bl-player-name">${escapeHtml(p.player_name)}</span></a>
              ${p.is_claimed ? '<span class="pill pill-verified">✓ Claimed</span>' : ""}</td>
            <td class="hide-sm">${escapeHtml(countryName(p.country) || "—")}</td>
            <td class="hide-sm">${p.team ? teamPillHtml(p.team, p.team_slug) : '<span class="muted">—</span>'}</td>
            <td class="right num">${formatNumber(p.rating)}</td>
            <td class="hide-sm">${tierBadge(p.tier)}</td>
            <td class="hide-sm">${p.main_legend ? `<span class="legend-cell">${legendAvatarHtml(p.main_legend, 24)}${escapeHtml(legendDisplayName(p.main_legend))}</span>` : '<span class="muted">—</span>'}</td>
          </tr>`
        )
        .join("")}</tbody></table></div></div>`;
  }

  function render() {
    document.querySelectorAll(".view-toggle button").forEach((b) => b.setAttribute("aria-pressed", b.dataset.view === view ? "true" : "false"));
    if (!players) return;
    const list = players.filter(matches);
    count.textContent = `${list.length} of ${players.length} players tracked by BRAWLISTAN.`;
    if (!list.length) {
      el.innerHTML = '<div class="panel empty-panel"><h2>No players match</h2><p>Try a different name, or clear the filters.</p></div>';
      return;
    }
    el.innerHTML = view === "list" ? listHtml(list) : gridHtml(list);
  }

  function fillOptions(list) {
    const teams = [...new Set(list.map((p) => p.team).filter(Boolean))].sort();
    team.innerHTML = '<option value="">All</option>' + teams.map((t) => `<option value="${escapeHtml(t)}">${escapeHtml(t)}</option>`).join("") + '<option value="_none">No team</option>';
    const codes = [...new Set(list.map((p) => p.country).filter(Boolean))].sort();
    country.innerHTML = '<option value="">All</option>' + codes.map((c) => `<option value="${escapeHtml(c)}">${escapeHtml(countryName(c))}</option>`).join("") + '<option value="_none">Not set</option>';
  }

  document.querySelectorAll(".view-toggle button").forEach((button) =>
    button.addEventListener("click", () => {
      view = button.dataset.view;
      try {
        localStorage.setItem(VIEW_KEY, view);
      } catch {
        /* storage blocked: view lasts for this visit */
      }
      render();
    })
  );
  search.addEventListener("input", render);
  [team, country, claimed].forEach((c) => c.addEventListener("change", render));
  document.getElementById("filters").addEventListener("submit", (e) => e.preventDefault());
  document.getElementById("filters-toggle").addEventListener("click", (event) => {
    const open = document.getElementById("filters").classList.toggle("is-open");
    event.currentTarget.setAttribute("aria-expanded", open ? "true" : "false");
  });

  render();
  ShaheenAPI.withSnapshot("players", () => ShaheenAPI.getPlayers(), (list) => {
    players = list || [];
    fillOptions(players);
    render();
  }).catch(() => {
    if (!players) el.innerHTML = '<p class="unavailable">Data unavailable</p>';
  });
})();
