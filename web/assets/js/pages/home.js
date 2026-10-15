// BRAWLISTAN home dashboard (docs/DECISIONS.md ADR-130; ADR-104 before it).
// Every panel reads the cached site snapshot first (web/data/*.json) and then
// the live API, and a panel with nothing real to show says "Data
// unavailable" rather than inventing a number.
(function () {
  const UNAVAILABLE = '<p class="unavailable">Data unavailable</p>';
  const INVITE = typeof DISCORD_INVITE_URL !== "undefined" && DISCORD_INVITE_URL ? DISCORD_INVITE_URL : "join.html";
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function setHtml(id, html) {
    const el = document.getElementById(id);
    if (el) el.innerHTML = html;
  }

  function profileHref(entry) {
    return `player.html?id=${encodeURIComponent(entry.brawlhalla_id)}`;
  }

  // A green or red change pill, crypto-ticker style.
  function deltaPill(change) {
    if (change == null || change === 0) return '<span class="ar-delta">0</span>';
    const up = change > 0;
    return `<span class="ar-delta ${up ? "is-up" : "is-down"}">${up ? "▲" : "▼"} ${Math.abs(change).toLocaleString()}</span>`;
  }

  function rankBox(n, highlight) {
    return `<span class="ar-rank${highlight ? " is-top" : ""}">${n}</span>`;
  }

  // ---- season card + countdown ------------------------------------------
  let countdownTimer = 0;

  function renderSeason(clan) {
    const season = clan && clan.pakistan_season;
    if (!season) {
      setHtml("season-card", UNAVAILABLE);
      setHtml("countdown", "");
      return;
    }
    const start = Date.parse(season.starts_at);
    const end = Date.parse(season.ends_at);
    const now = Date.now();
    const total = Math.max(1, end - start);
    const pct = Math.min(100, Math.max(0, ((now - start) / total) * 100));
    const day = Math.min(Math.ceil(total / 864e5), Math.max(1, Math.ceil((now - start) / 864e5)));
    const badge = `assets/img/seasons/${encodeURIComponent(season.badge)}`;
    const stat = (value, label) =>
      typeof value === "number" ? `<div><strong class="num">${value.toLocaleString()}</strong><span>${label}</span></div>` : "";

    setHtml(
      "season-card",
      `<div class="ar-season-top">
        <picture><source srcset="${badge}.webp" type="image/webp" /><img src="${badge}.jpg" alt="" width="64" height="58" /></picture>
        <div>
          <h2 id="season-title">${escapeHtml(season.name)}</h2>
          <span class="muted">Season ${season.number} &middot; <span lang="ur">${escapeHtml(season.name_urdu)}</span></span>
        </div>
      </div>
      <div class="ar-progress" role="progressbar" aria-label="Season progress" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${Math.round(pct)}">
        <span style="width:${pct.toFixed(1)}%"></span>
      </div>
      <div class="ar-progress-label"><span>Day ${day}</span><span class="num">${Math.round(pct)}%</span></div>
      <div class="ar-duo">
        ${stat(clan.discord_member_count, "in the Discord")}
        ${stat(clan.member_count, "linked players")}
      </div>
      <a class="ar-btn ar-btn-fire ar-btn-block" data-discord-invite href="${INVITE}" target="_blank" rel="noopener">Join the Discord</a>`
    );

    const title = document.getElementById("event-title");
    if (title) title.textContent = `Season ${season.number} · ${season.name}`;
    startCountdown(end);
  }

  function startCountdown(end) {
    const box = document.getElementById("countdown");
    if (!box) return;
    const date = new Date(end);
    const dateBox = `<div class="ar-count is-date"><strong>${date.getDate()}</strong><span>${date
      .toLocaleString(undefined, { month: "short" })
      .toUpperCase()}</span></div>`;
    function paint() {
      let left = Math.max(0, Math.floor((end - Date.now()) / 1000));
      if (!left) {
        const eyebrow = document.getElementById("event-eyebrow");
        if (eyebrow) eyebrow.textContent = "Season complete";
      }
      const days = Math.floor(left / 86400);
      left %= 86400;
      const parts = [
        [days, "Day"],
        [Math.floor(left / 3600), "Hrs"],
        [Math.floor((left % 3600) / 60), "Min"],
        [left % 60, "Sec"],
      ];
      box.innerHTML =
        dateBox +
        parts
          .map(([v, l]) => `<div class="ar-count"><strong class="num">${String(v).padStart(2, "0")}</strong><span>${l}</span></div>`)
          .join("");
      box.setAttribute("aria-label", `${parts[0][0]} days, ${parts[1][0]} hours left`);
    }
    paint();
    clearInterval(countdownTimer);
    countdownTimer = setInterval(paint, 1000);
  }

  // ---- ticker + top players, from the Rankings board ----------------------
  function renderBoard(payload) {
    const rows = ((payload && payload.rows) || []).filter((r) => r.rating != null);
    if (!rows.length) {
      setHtml("ticker", '<span class="muted">Data unavailable</span>');
      setHtml("top-players", UNAVAILABLE);
      return;
    }
    const items = rows
      .slice(0, 14)
      .map(
        (r, i) => `<a class="ar-tick" href="${profileHref(r)}">
          <span class="muted num">#${i + 1}</span>
          <strong>${escapeHtml(r.player_name)}</strong>
          <span class="num">${formatNumber(r.rating)}</span>
          ${deltaPill(r.trend)}
        </a>`
      )
      .join("");
    const track = document.getElementById("ticker");
    if (track) {
      // Two copies make the marquee seamless; the copy is hidden from screen readers.
      track.innerHTML = reduceMotion
        ? `<div class="ar-ticker-row">${items}</div>`
        : `<div class="ar-ticker-row is-moving">${items}<span class="ar-ticker-copy" aria-hidden="true">${items.replace(/<a /g, '<a tabindex="-1" ')}</span></div>`;
    }

    setHtml(
      "top-players",
      `<ol class="ar-list">${rows
        .slice(0, 5)
        .map(
          (r, i) => `<li>
            <a class="ar-row" href="${profileHref(r)}">
              ${r.main_legend ? legendAvatarHtml(r.main_legend, 36) : avatarHtml(r.player_name, 36)}
              <span class="ar-row-main">
                <strong>${r.team_tag ? `<span class="ar-tag">${escapeHtml(r.team_tag)}</span>` : ""}${escapeHtml(r.player_name)}</strong>
                <span class="muted num">${formatNumber(r.rating)} &middot; ${escapeHtml(r.tier || "Unranked")}</span>
              </span>
              ${rankBox(i + 1, i === 0)}
            </a>
          </li>`
        )
        .join("")}</ol>`
    );
    topFirst = rows[0];
    paintFeatured();
  }

  // ---- featured player: staff's /feature pick (ADR-111), else #1 ---------
  let staffPick = null;
  let topFirst = null;

  function paintFeatured() {
    const pick = staffPick || topFirst;
    if (!pick) return;
    const why = staffPick ? escapeHtml(staffPick.note || "Picked by BRAWLISTAN staff") : "Pakistan #1 this season";
    setHtml(
      "featured",
      `<a class="ar-featured" href="${profileHref(pick)}">
        ${pick.main_legend ? legendAvatarHtml(pick.main_legend, 72) : avatarHtml(pick.player_name, 72)}
        <span>
          <strong>${escapeHtml(pick.player_name)}</strong>
          <span class="muted">${why}</span>
          <span class="ar-featured-meta">${tierBadge(pick.tier)}${pick.rating != null ? `<span class="num">${formatNumber(pick.rating)}</span>` : ""}</span>
        </span>
      </a>`
    );
  }

  // ---- teams -------------------------------------------------------------
  function renderTeams(list) {
    const teams = (Array.isArray(list) ? list : []).slice().sort((a, b) => (a.rank || 99) - (b.rank || 99));
    if (!teams.length) {
      setHtml("teams", UNAVAILABLE);
      return;
    }
    setHtml(
      "teams",
      `<ol class="ar-list">${teams
        .slice(0, 5)
        .map((t, i) => {
          const logo = t.logo
            ? `<img class="ar-logo" src="assets/img/teams/${encodeURIComponent(t.logo)}.webp" alt="" width="36" height="36" loading="lazy" />`
            : `<span class="team-monogram" style="--size:36px" aria-hidden="true">${escapeHtml(t.tag)}</span>`;
          return `<li>
            <a class="ar-row" href="${teamHref(t.slug)}">
              ${logo}
              <span class="ar-row-main">
                <strong>${escapeHtml(t.name)}</strong>
                <span class="muted num">${t.rating != null ? formatNumber(t.rating) : "—"} power &middot; ${formatNumber(t.members)} players</span>
              </span>
              ${rankBox(t.rank || i + 1, (t.rank || i + 1) === 1)}
            </a>
          </li>`;
        })
        .join("")}</ol>`
    );
  }

  // ---- tournaments -------------------------------------------------------
  const STATUS = {
    registration: ["Registration open", "is-open"],
    in_progress: ["Live", "is-live"],
    completed: ["Completed", "is-done"],
    cancelled: ["Cancelled", "is-done"],
  };
  let tournaments = null;
  let tview = "upcoming";

  function renderTournaments() {
    if (!tournaments) return;
    const rows = tournaments.filter((t) =>
      tview === "upcoming" ? t.status === "registration" || t.status === "in_progress" : t.status === "completed"
    );
    if (!rows.length) {
      setHtml(
        "tournaments",
        `<p class="unavailable">${tview === "upcoming" ? "No tournament is open right now. Staff announce new ones in the Discord." : "No finished tournaments yet."}</p>`
      );
      return;
    }
    setHtml(
      "tournaments",
      `<div class="bl-table-wrap"><table class="ar-table">
        <thead><tr><th scope="col">#</th><th scope="col">Name</th><th scope="col" class="hide-sm">Type</th><th scope="col" class="hide-sm">Date</th><th scope="col">Status</th></tr></thead>
        <tbody>${rows
          .slice(0, 6)
          .map((t, i) => {
            const [label, cls] = STATUS[t.status] || [t.status, ""];
            const when = t.completed_at || t.started_at;
            return `<tr>
              <td class="muted num">${i + 1}</td>
              <td><a href="tournament.html?id=${encodeURIComponent(t.id)}"><strong>${escapeHtml(t.name)}</strong></a></td>
              <td class="hide-sm muted">${escapeHtml(t.kind)}</td>
              <td class="hide-sm muted num">${when ? formatDate(when) : "—"}</td>
              <td><span class="ar-status ${cls}">${escapeHtml(label)}</span></td>
            </tr>`;
          })
          .join("")}</tbody>
      </table></div>`
    );
  }

  document.querySelectorAll("[data-tview]").forEach((button) => {
    button.addEventListener("click", () => {
      tview = button.dataset.tview;
      document.querySelectorAll("[data-tview]").forEach((b) => b.setAttribute("aria-selected", String(b === button)));
      renderTournaments();
    });
  });

  // ---- City Wars (ADR-128) -----------------------------------------------
  function renderCities(board) {
    const cities = (board && board.cities) || [];
    if (!cities.length) {
      setHtml(
        "cities",
        `<p class="unavailable">No city has placed players yet.</p>
         <p class="ar-hint">Represent your city: run <code>/city set</code> in the <a data-discord-invite href="${INVITE}" target="_blank" rel="noopener">Discord</a>.</p>`
      );
      return;
    }
    setHtml(
      "cities",
      `<ol class="ar-list">${cities
        .slice(0, 5)
        .map(
          (c, i) => `<li>
            <a class="ar-row" href="cities.html#${encodeURIComponent(c.key)}">
              <span class="ar-city-mark" aria-hidden="true">${escapeHtml(c.label.charAt(0))}</span>
              <span class="ar-row-main">
                <strong>${escapeHtml(c.label)}</strong>
                <span class="muted num">${formatNumber(c.rating)} score &middot; ${c.players} placed</span>
              </span>
              ${rankBox(i + 1, i === 0)}
            </a>
          </li>`
        )
        .join("")}</ol>`
    );
  }

  // ---- rising + legend meta ---------------------------------------------
  function renderRising(entries) {
    if (!entries || !entries.length) {
      setHtml("rising", UNAVAILABLE);
      return;
    }
    setHtml(
      "rising",
      `<ol class="ar-list">${entries
        .slice(0, 5)
        .map(
          (e) => `<li>
            <a class="ar-row" href="${profileHref(e)}">
              ${avatarHtml(e.player_name, 32)}
              <span class="ar-row-main"><strong>${escapeHtml(e.player_name)}</strong><span class="muted num">${formatNumber(e.rating)}</span></span>
              ${deltaPill(e.rating_gain)}
            </a>
          </li>`
        )
        .join("")}</ol>`
    );
  }

  function renderLegendMeta(entries) {
    if (!entries || !entries.length) {
      setHtml("legend-meta", UNAVAILABLE);
      return;
    }
    const most = Math.max(...entries.map((e) => e.total_games));
    setHtml(
      "legend-meta",
      `<ol class="ar-list">${entries
        .slice(0, 5)
        .map(
          (e) => `<li class="ar-row">
            ${legendAvatarHtml(e.legend_name_key, 32)}
            <span class="ar-row-main">
              <strong>${escapeHtml(legendDisplayName(e.legend_name_key))}</strong>
              <span class="ar-meter"><span style="width:${Math.max(4, Math.round((e.total_games / most) * 100))}%"></span></span>
            </span>
            <span class="ar-delta ${e.win_rate >= 50 ? "is-up" : "is-down"}">${e.win_rate}%</span>
          </li>`
        )
        .join("")}</ol>`
    );
  }

  // A failed fetch leaves its panels saying "Data unavailable" instead of
  // "Loading…" forever. Panels that already rendered from a snapshot stay.
  function guard(ids, promise) {
    promise.catch(() => {
      ids.forEach((id) => {
        const el = document.getElementById(id);
        if (el && el.textContent.trim() === "Loading…") el.innerHTML = UNAVAILABLE;
      });
    });
  }

  guard(["season-card"], ShaheenAPI.withSnapshot("clan", () => ShaheenAPI.getClan(), renderSeason));
  guard(["ticker", "top-players", "featured"], ShaheenAPI.withSnapshot("rankings", () => ShaheenAPI.getRankings(), renderBoard));
  ShaheenAPI.withSnapshot("featured", () => ShaheenAPI.getFeatured(), (pick) => {
    staffPick = pick && pick.player_name ? pick : null;
    paintFeatured();
  }).catch(() => {});
  guard(["teams"], ShaheenAPI.withSnapshot("teams", () => ShaheenAPI.getTeams(), renderTeams));
  guard(["cities"], ShaheenAPI.withSnapshot("cities", () => ShaheenAPI.getCityBoard(), renderCities));
  guard(["rising"], ShaheenAPI.withSnapshot("rising", () => ShaheenAPI.getPakistanRising(7, 10), renderRising));
  guard(["legend-meta"], ShaheenAPI.withSnapshot("legend-meta", () => ShaheenAPI.getLegendMeta(10), renderLegendMeta));
  guard(
    ["tournaments"],
    ShaheenAPI.getTournaments(20).then((list) => {
      tournaments = Array.isArray(list) ? list : [];
      renderTournaments();
    })
  );
})();
