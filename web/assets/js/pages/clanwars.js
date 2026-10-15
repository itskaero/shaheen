// Clan Wars page (docs/DECISIONS.md ADR-131), from GET /clan-wars. Snapshot
// first, then the live API.
(function () {
  const UNAVAILABLE = '<p class="unavailable">Data unavailable</p>';
  let timer = 0;

  function logoHtml(team, size) {
    return team.logo
      ? `<img class="ar-logo" src="assets/img/teams/${encodeURIComponent(team.logo)}.webp" alt="" width="${size}" height="${size}" loading="lazy" />`
      : `<span class="team-monogram" style="--size:${size}px" aria-hidden="true">${escapeHtml(team.tag)}</span>`;
  }

  function weekLabel(isoDate) {
    const d = new Date(`${isoDate}T00:00:00`);
    return `week of ${d.toLocaleDateString(undefined, { day: "numeric", month: "short" })}`;
  }

  function countdown(endsAt) {
    const box = document.getElementById("cw-countdown");
    if (!box) return;
    const end = Date.parse(endsAt);
    function paint() {
      let left = Math.max(0, Math.floor((end - Date.now()) / 1000));
      const parts = [
        [Math.floor(left / 86400), "Day"],
        [Math.floor((left % 86400) / 3600), "Hrs"],
        [Math.floor((left % 3600) / 60), "Min"],
        [left % 60, "Sec"],
      ];
      box.innerHTML = parts
        .map(([v, l]) => `<div class="ar-count"><strong class="num">${String(v).padStart(2, "0")}</strong><span>${l}</span></div>`)
        .join("");
      box.setAttribute("aria-label", `War ends in ${parts[0][0]} days, ${parts[1][0]} hours`);
    }
    paint();
    clearInterval(timer);
    timer = setInterval(paint, 1000);
  }

  function renderStandings(board) {
    const el = document.getElementById("cw-standings");
    const rows = board.standings || [];
    if (!rows.length) {
      el.innerHTML = '<p class="unavailable">No teams yet. Staff create them with <code>/team</code>.</p>';
      return;
    }
    const best = Math.max(1, ...rows.map((t) => t.points));
    el.innerHTML = `<ol class="ar-war-list">${rows
      .map((t) => {
        const counted = t.scorers.slice(0, board.top_n);
        const bench = t.scorers.length - counted.length;
        const chips = counted
          .map((s) => `<a class="ar-war-chip" href="player.html?id=${encodeURIComponent(s.brawlhalla_id)}">${escapeHtml(s.player_name)} <b class="num">${formatNumber(s.points)}</b></a>`)
          .join("");
        return `<li class="ar-war-row${t.place === 1 && t.points > 0 ? " is-leading" : ""}">
          <span class="ar-rank${t.place === 1 && t.points > 0 ? " is-top" : ""}">${t.place}</span>
          <a class="ar-war-team" href="${teamHref(t.slug)}">${logoHtml(t, 40)}
            <span><strong>${escapeHtml(t.name)}</strong><span class="muted">[${escapeHtml(t.tag)}]</span></span>
          </a>
          <div class="ar-war-score">
            <strong class="num">${formatNumber(t.points)}</strong><span class="muted">pts</span>
            <span class="ar-meter"><span style="width:${t.points ? Math.max(3, Math.round((t.points / best) * 100)) : 0}%"></span></span>
          </div>
          <div class="ar-war-chips">${chips || '<span class="muted">Nobody has played ranked yet this week.</span>'}${bench > 0 ? `<span class="muted">+${bench} more</span>` : ""}</div>
        </li>`;
      })
      .join("")}</ol>`;
  }

  function renderSeason(board) {
    const el = document.getElementById("cw-season");
    const rows = board.season_table || [];
    if (!rows.length) {
      el.innerHTML = '<p class="unavailable">No finished weeks yet. The first result lands Monday.</p>';
      return;
    }
    el.innerHTML = `<ol class="ar-list">${rows
      .map(
        (r, i) => `<li><a class="ar-row" href="${teamHref(r.slug)}">
          ${logoHtml(r, 36)}
          <span class="ar-row-main"><strong>${escapeHtml(r.name)}</strong><span class="muted num">${formatNumber(r.points)} pts &middot; ${r.weeks} week${r.weeks === 1 ? "" : "s"}</span></span>
          <span class="ar-delta${r.wins ? " is-up" : ""}">🏆 ${r.wins}</span>
          <span class="ar-rank${i === 0 ? " is-top" : ""}">${i + 1}</span>
        </a></li>`
      )
      .join("")}</ol>`;
  }

  function renderLast(board) {
    const el = document.getElementById("cw-last");
    const last = board.last_winner;
    if (!last) {
      el.hidden = true;
      return;
    }
    el.hidden = false;
    el.innerHTML = `<a href="${teamHref(last.slug)}">
      ${logoHtml(last, 56)}
      <span><span class="ar-eyebrow">Last week's winner &middot; ${escapeHtml(weekLabel(last.week_start))}</span>
      <strong>${escapeHtml(last.name)}</strong></span>
      <span class="ar-war-banner-pts"><b class="num">${formatNumber(last.points)}</b> pts</span>
    </a>`;
  }

  function render(board) {
    if (!board) return;
    const week = document.getElementById("cw-week");
    if (week) week.textContent = weekLabel(board.week_start);
    const rules = document.getElementById("cw-rules");
    if (rules) {
      rules.textContent = `Each member scores ${board.win_points} points per ranked win plus every rating point gained this week. A team's best ${board.top_n} members count.`;
    }
    countdown(board.ends_at);
    renderLast(board);
    renderStandings(board);
    renderSeason(board);
  }

  ShaheenAPI.withSnapshot("clan-wars", () => ShaheenAPI.getClanWars(), render).catch(() => {
    ["cw-standings", "cw-season"].forEach((id) => {
      const el = document.getElementById(id);
      if (el && el.textContent.trim() === "Loading…") el.innerHTML = UNAVAILABLE;
    });
  });
})();
