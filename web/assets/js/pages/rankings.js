// BRAWLISTAN Rankings (docs/DECISIONS.md ADR-105).
//
// One /rankings/pakistan payload backs the Pakistan, Global, 1v1 and 2v2 tabs:
// each tab keeps the rows that have the number it ranks by and sorts on it.
// Rising reads /pakistan/rising. Power has no data source, so it says so.
// Tab state lives in the URL hash (rankings.html#2v2), so boards are linkable
// and the old rankings.html#pakistan links still land on the Pakistan board.
(function () {
  const TABS = ["pakistan", "global", "1v1", "2v2", "power", "rising"];
  const TIERS = ["Valhallan", "Diamond", "Platinum", "Gold", "Silver", "Bronze", "Tin"];
  const UNAVAILABLE = '<p class="unavailable">Data unavailable</p>';

  const board = document.getElementById("board");
  const seasonSelect = document.getElementById("season-select");
  const seasonLine = document.getElementById("season-line");
  const filters = {
    search: document.getElementById("f-search"),
    region: document.getElementById("f-region"),
    tier: document.getElementById("f-tier"),
    legend: document.getElementById("f-legend"),
    team: document.getElementById("f-team"),
    claimed: document.getElementById("f-claimed"),
    verified: document.getElementById("f-verified"),
  };

  let data = null; // the /rankings/pakistan payload
  let rising = null; // the /pakistan/rising list
  let tab = tabFromHash();

  function tabFromHash() {
    const name = location.hash.replace("#", "");
    return TABS.includes(name) ? name : "pakistan";
  }

  // ---------- small renderers ----------
  function profileHref(row) {
    return `player.html?id=${encodeURIComponent(row.brawlhalla_id)}`;
  }

  function playerCell(row) {
    const claimed = row.is_verified
      ? '<span class="pill pill-verified" title="Staff confirmed the account owner">✓ Verified</span>'
      : row.is_claimed
        ? '<span class="pill pill-team" title="Claimed by its player in our Discord">Claimed</span>'
        : '<span class="pill pill-muted" title="Added by staff; not yet claimed">Unclaimed</span>';
    return `<a class="bl-player" href="${profileHref(row)}">${avatarHtml(row.player_name, 28)}<span class="bl-player-name">${escapeHtml(row.player_name)}</span></a> ${claimed}`;
  }

  function teamCell(row) {
    return row.team ? `<span class="pill pill-team">${escapeHtml(row.team)}</span>` : '<span class="muted">—</span>';
  }

  function trendCell(trend) {
    if (trend == null) return '<span class="muted" title="Not enough readings this week">—</span>';
    if (trend > 0) return `<span class="trend-up num">▲ ${trend}</span>`;
    if (trend < 0) return `<span class="trend-down num">▼ ${Math.abs(trend)}</span>`;
    return '<span class="muted num">0</span>';
  }

  function legendCell(key) {
    if (!key) return '<span class="muted">—</span>';
    return `<span class="legend-cell">${legendAvatarHtml(key, 24)}${escapeHtml(legendDisplayName(key))}</span>`;
  }

  function flag(country) {
    return country === "PK" ? '<span title="Pakistan">🇵🇰 PK</span>' : escapeHtml(country || "—");
  }

  function winRate(row) {
    return row.games ? `${Math.round((row.wins / row.games) * 100)}%` : "—";
  }

  function table(columns, rows) {
    const head = columns.map((c) => `<th scope="col"${c.cls ? ` class="${c.cls}"` : ""}>${c.label}</th>`).join("");
    const body = rows
      .map((row, i) => `<tr>${columns.map((c) => `<td${c.cls ? ` class="${c.cls}"` : ""}>${c.cell(row, i)}</td>`).join("")}</tr>`)
      .join("");
    return `<div class="bl-table-wrap"><table class="bl-table">
      <caption class="sr-only">${escapeHtml(tabLabel())} rankings</caption>
      <thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div>`;
  }

  function tabLabel() {
    return document.getElementById(`tab-${tab}`).textContent;
  }

  // ---------- filtering ----------
  function tierFamily(tier) {
    return TIERS.find((t) => (tier || "").toLowerCase().startsWith(t.toLowerCase())) || null;
  }

  function applyFilters(rows, { tierKey = "tier" } = {}) {
    const q = filters.search.value.trim().toLowerCase();
    return rows.filter((row) => {
      if (q && !row.player_name.toLowerCase().includes(q)) return false;
      if (filters.region.value && row.region !== filters.region.value) return false;
      if (filters.tier.value && tierFamily(row[tierKey]) !== filters.tier.value) return false;
      if (filters.legend.value && row.main_legend !== filters.legend.value) return false;
      if (filters.team.value === "_none" && row.team) return false;
      if (filters.team.value && filters.team.value !== "_none" && row.team !== filters.team.value) return false;
      if (filters.claimed.checked && !row.is_claimed) return false;
      if (filters.verified.checked && !row.is_verified) return false;
      return true;
    });
  }

  function fillSelect(select, values, label = (v) => v) {
    const keep = select.value;
    select.innerHTML = '<option value="">All</option>' + values.map((v) => `<option value="${escapeHtml(v)}">${escapeHtml(label(v))}</option>`).join("");
    if ([...select.options].some((o) => o.value === keep)) select.value = keep;
  }

  function fillFilterOptions(rows) {
    const uniq = (xs) => [...new Set(xs.filter(Boolean))].sort();
    fillSelect(filters.region, uniq(rows.map((r) => r.region)));
    fillSelect(filters.tier, TIERS.filter((t) => rows.some((r) => tierFamily(r.tier) === t || tierFamily(r.tier_2v2) === t)));
    fillSelect(filters.legend, uniq(rows.map((r) => r.main_legend)), legendDisplayName);
    const teams = uniq(rows.map((r) => r.team));
    filters.team.innerHTML = '<option value="">All</option>' + teams.map((t) => `<option value="${escapeHtml(t)}">${escapeHtml(t)}</option>`).join("") + '<option value="_none">No team</option>';
  }

  // ---------- boards ----------
  const VIEWS = {
    pakistan() {
      const rows = applyFilters(data.rows.filter((r) => r.rating != null));
      return {
        rows,
        html: table(
          [
            { label: "#", cell: (_r, i) => rankHtml(i + 1) },
            { label: "Player", cell: playerCell },
            { label: "Country", cls: "hide-sm", cell: (r) => flag(r.country) },
            { label: "Team", cls: "hide-sm", cell: teamCell },
            { label: "Rating", cls: "right", cell: (r) => `<span class="num">${formatNumber(r.rating)}</span>` },
            { label: "Tier", cls: "hide-sm", cell: (r) => tierBadge(r.tier) },
            { label: "7d", cls: "right", cell: (r) => trendCell(r.trend) },
            { label: "Main legend", cls: "hide-sm", cell: (r) => legendCell(r.main_legend) },
          ],
          rows
        ),
      };
    },
    global() {
      const rows = applyFilters(data.rows.filter((r) => r.global_rank != null)).sort((a, b) => a.global_rank - b.global_rank);
      return {
        rows,
        html: table(
          [
            { label: "Global #", cell: (r) => `<span class="num">${formatNumber(r.global_rank)}</span>` },
            { label: "Player", cell: playerCell },
            { label: "Region", cls: "hide-sm", cell: (r) => escapeHtml(r.region || "—") },
            { label: "Region #", cls: "right hide-sm", cell: (r) => `<span class="num">${formatNumber(r.region_rank)}</span>` },
            { label: "Rating", cls: "right", cell: (r) => `<span class="num">${formatNumber(r.rating)}</span>` },
            { label: "Tier", cls: "hide-sm", cell: (r) => tierBadge(r.tier) },
          ],
          rows
        ),
      };
    },
    "1v1"() {
      const rows = applyFilters(data.rows.filter((r) => r.rating != null));
      return {
        rows,
        html: table(
          [
            { label: "#", cell: (_r, i) => rankHtml(i + 1) },
            { label: "Player", cell: playerCell },
            { label: "Rating", cls: "right", cell: (r) => `<span class="num">${formatNumber(r.rating)}</span>` },
            { label: "Peak", cls: "right hide-sm", cell: (r) => `<span class="num">${formatNumber(r.peak_rating)}</span>` },
            { label: "Tier", cls: "hide-sm", cell: (r) => tierBadge(r.tier) },
            { label: "W / Games", cls: "right hide-sm", cell: (r) => `<span class="num">${r.wins} / ${r.games}</span>` },
            { label: "Win %", cls: "right", cell: (r) => `<span class="num">${winRate(r)}</span>` },
          ],
          rows
        ),
      };
    },
    "2v2"() {
      const rows = applyFilters(data.rows.filter((r) => r.rating_2v2 != null), { tierKey: "tier_2v2" }).sort(
        (a, b) => b.rating_2v2 - a.rating_2v2
      );
      return {
        rows,
        html: table(
          [
            { label: "#", cell: (_r, i) => rankHtml(i + 1) },
            { label: "Player", cell: playerCell },
            { label: "Partner", cls: "hide-sm", cell: (r) => escapeHtml(r.partner_2v2 || "—") },
            { label: "Rating", cls: "right", cell: (r) => `<span class="num">${formatNumber(r.rating_2v2)}</span>` },
            { label: "Peak", cls: "right hide-sm", cell: (r) => `<span class="num">${formatNumber(r.peak_rating_2v2)}</span>` },
            { label: "Tier", cls: "hide-sm", cell: (r) => tierBadge(r.tier_2v2) },
          ],
          rows
        ),
      };
    },
  };

  function renderPower() {
    board.innerHTML = `<div class="empty-panel">
      <h2>Power rankings</h2>
      <p>Power rankings are compiled from tournament results by the scene's organisers. BRAWLISTAN doesn't have a source for them yet, so there's nothing to show here rather than a made-up list.</p>
      <p class="unavailable">Data unavailable</p>
    </div>`;
  }

  function renderRising() {
    if (!rising) {
      board.innerHTML = '<p class="unavailable">Loading…</p>';
      return;
    }
    const q = filters.search.value.trim().toLowerCase();
    const rows = rising.filter((r) => (!q || r.player_name.toLowerCase().includes(q)) && (!filters.claimed.checked || r.is_claimed));
    if (!rows.length) {
      board.innerHTML = UNAVAILABLE;
      return;
    }
    board.innerHTML =
      table(
        [
          { label: "#", cell: (_r, i) => rankHtml(i + 1) },
          { label: "Player", cell: playerCell },
          { label: "Gain (7d)", cls: "right", cell: (r) => `<span class="trend-up num">▲ ${r.rating_gain}</span>` },
          { label: "Rating", cls: "right", cell: (r) => `<span class="num">${formatNumber(r.rating)}</span>` },
        ],
        rows
      ) + '<div class="table-foot"><span>Biggest rating gains on the Pakistan board over the last seven days.</span></div>';
  }

  function render() {
    TABS.forEach((name) => {
      const el = document.getElementById(`tab-${name}`);
      const active = name === tab;
      el.setAttribute("aria-selected", active ? "true" : "false");
      el.tabIndex = active ? 0 : -1;
    });
    board.setAttribute("aria-labelledby", `tab-${tab}`);
    // Bracket filters don't apply to Rising/Power; hide the ones that don't.
    const bracket = tab in VIEWS;
    ["region", "tier", "legend", "team"].forEach((k) => {
      filters[k].closest(".field").hidden = !bracket;
    });
    document.getElementById("filters").hidden = tab === "power";

    if (tab === "power") return renderPower();
    if (tab === "rising") return renderRising();
    if (!data) {
      board.innerHTML = '<p class="unavailable">Loading…</p>';
      return;
    }
    const view = VIEWS[tab]();
    if (!view.rows.length) {
      board.innerHTML = UNAVAILABLE;
      return;
    }
    const claimNote =
      tab === "pakistan" && view.rows.some((r) => !r.is_claimed)
        ? `<span>Unclaimed players were added by staff. If one is you, <a data-discord-invite href="${typeof DISCORD_INVITE_URL !== "undefined" ? DISCORD_INVITE_URL : "join.html"}" target="_blank" rel="noopener">join the Discord</a> and run <code>/pakistan join</code> to claim it.</span>`
        : "<span></span>";
    board.innerHTML = view.html + `<div class="table-foot">${claimNote}<span>${view.rows.length} of ${data.rows.length} players</span></div>`;
  }

  function seasonLabel(n) {
    return n >= 42 ? `Season ${n - 41} · Brawlhalla S${n}` : `Brawlhalla Season ${n}`;
  }

  function onData(payload) {
    data = payload;
    fillFilterOptions(payload.rows);
    if (payload.seasons && payload.seasons.length) {
      seasonSelect.innerHTML = payload.seasons.map((n) => `<option value="${n}">${escapeHtml(seasonLabel(n))}</option>`).join("");
      seasonSelect.value = String(payload.season);
      seasonSelect.disabled = false;
    }
    const s = payload.pakistan_season;
    seasonLine.textContent = s
      ? `Pakistan Season ${s.number} · Season of ${s.name}. Synced from the official Brawlhalla API every six hours.`
      : `Brawlhalla Season ${payload.season ?? "—"}. Synced from the official Brawlhalla API every six hours.`;
    render();
  }

  // ---------- wiring ----------
  TABS.forEach((name, index) => {
    const el = document.getElementById(`tab-${name}`);
    el.addEventListener("click", () => {
      history.replaceState(null, "", `#${name}`);
      tab = name;
      render();
    });
    el.addEventListener("keydown", (event) => {
      if (event.key !== "ArrowRight" && event.key !== "ArrowLeft") return;
      event.preventDefault();
      const next = TABS[(index + (event.key === "ArrowRight" ? 1 : TABS.length - 1)) % TABS.length];
      history.replaceState(null, "", `#${next}`);
      tab = next;
      render();
      document.getElementById(`tab-${next}`).focus();
    });
  });
  window.addEventListener("hashchange", () => {
    tab = tabFromHash();
    render();
  });
  Object.values(filters).forEach((el) => el.addEventListener(el.type === "search" ? "input" : "change", render));
  document.getElementById("filters").addEventListener("submit", (event) => event.preventDefault());
  document.getElementById("filters-toggle").addEventListener("click", (event) => {
    const form = document.getElementById("filters");
    const open = form.classList.toggle("is-open");
    event.currentTarget.setAttribute("aria-expanded", open ? "true" : "false");
  });
  seasonSelect.addEventListener("change", () => {
    board.innerHTML = '<p class="unavailable">Loading…</p>';
    ShaheenAPI.getRankings(seasonSelect.value)
      .then(onData)
      .catch(() => {
        board.innerHTML = UNAVAILABLE;
      });
  });

  render();
  ShaheenAPI.withSnapshot("rankings", () => ShaheenAPI.getRankings(), onData).catch(() => {
    if (!data && tab in VIEWS) board.innerHTML = UNAVAILABLE;
  });
  ShaheenAPI.withSnapshot("rising", () => ShaheenAPI.getPakistanRising(7, 25), (rows) => {
    rising = rows;
    if (tab === "rising") render();
  }).catch(() => {
    rising = rising || [];
    if (tab === "rising") render();
  });
})();
