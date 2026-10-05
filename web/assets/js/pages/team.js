// One team (docs/DECISIONS.md ADR-114, ADR-117): the holographic team card
// as its identity, roster with the captain, season results, tournament
// results and achievements. Brawlhalla identity only. The slug comes from
// ?t=<slug>, or from the pre-rendered teams/<slug>/ page (data-team-slug).
(function () {
  const UNAVAILABLE = '<p class="unavailable">Data unavailable</p>';
  const slug = (new URLSearchParams(location.search).get("t") || document.body.dataset.teamSlug || "").toLowerCase();

  function setHtml(id, html) {
    const el = document.getElementById(id);
    if (el) el.innerHTML = html;
  }

  function notFound() {
    setHtml(
      "team-hero",
      `<div><h1>Team not found</h1><p class="muted">No team at this address. <a href="teams.html">See all teams &rarr;</a></p></div>`
    );
    ["team-roster", "team-seasons", "team-achievements", "team-tournaments"].forEach((id) => setHtml(id, ""));
  }

  function render(t) {
    if (!t) return notFound();
    document.title = `${t.name} — Pakistan Brawlhalla Team | BRAWLISTAN`;
    const captain = t.roster.find((p) => p.role === "captain");
    setHtml(
      "team-hero",
      `<div class="team-hero-card">${holoTeamCardHtml(t, { link: false, dpr: 2, ambient: 0.32 })}</div>
      <div class="team-hero-copy">
        <div class="team-hero-pills">
          ${t.is_founding ? '<span class="pill pill-founding">Founding team</span>' : ""}
          <span class="pill pill-muted">${escapeHtml(t.tag)}</span>
          <span class="pill pill-muted">${t.country === "PK" ? "🇵🇰 Pakistan" : escapeHtml(t.country)}</span>
        </div>
        <h1>${escapeHtml(t.name)}</h1>
        ${t.description ? `<p class="muted">${escapeHtml(t.description)}</p>` : ""}
        ${t.brawlhalla_clan_id ? `<p class="muted team-clan-note">Roster synced from in-game clan #${escapeHtml(String(t.brawlhalla_clan_id))} every few hours.</p>` : ""}
        <div class="team-hero-stats">
          <div><strong class="num">${t.rank ? `#${t.rank}` : "—"}</strong><span>Ranking</span></div>
          <div><strong class="num">${t.rating != null ? formatNumber(t.rating) : "—"}</strong><span>Power rating</span></div>
          <div><strong class="num">${t.members}</strong><span>Players</span></div>
          <div><strong>${captain ? escapeHtml(captain.player_name) : "—"}</strong><span>Captain</span></div>
        </div>
      </div>`
    );

    setHtml(
      "team-roster",
      t.roster.length
        ? `<div class="bl-table-wrap"><table class="bl-table">
            <thead><tr><th scope="col">Player</th><th scope="col" class="hide-sm">Tier</th><th scope="col" class="hide-sm">Main</th><th scope="col" class="right">Rating</th></tr></thead>
            <tbody>${t.roster
              .map(
                (p) => `<tr>
                  <td><a class="bl-player" href="player.html?id=${encodeURIComponent(p.brawlhalla_id)}">${avatarHtml(p.player_name, 28)}<span class="bl-player-name">${p.role === "captain" ? '<span title="Captain" aria-label="Captain">👑</span> ' : ""}${escapeHtml(p.player_name)}</span></a>${p.clan_rank ? ` <span class="pill pill-muted clan-rank">${escapeHtml(p.clan_rank)}</span>` : ""}</td>
                  <td class="hide-sm">${tierBadge(p.tier)}</td>
                  <td class="hide-sm">${p.main_legend ? `<span class="legend-cell">${legendAvatarHtml(p.main_legend, 24)}${escapeHtml(legendDisplayName(p.main_legend))}</span>` : '<span class="muted">—</span>'}</td>
                  <td class="right num">${formatNumber(p.rating)}</td>
                </tr>`
              )
              .join("")}</tbody>
          </table></div>`
        : '<p class="unavailable">No players yet. Staff add them in Discord with /team add.</p>'
    );

    setHtml(
      "team-seasons",
      t.seasons.length
        ? `<ul class="list-rows">${t.seasons
            .map((s) => {
              const ps = s.pakistan_season;
              const label = ps ? `Season ${ps.number} · ${escapeHtml(ps.name)}` : `Brawlhalla S${s.season}`;
              return `<li><a href="seasons.html?s=${encodeURIComponent(s.season)}">${label}</a>
                <span class="num">${formatNumber(s.average)} <span class="muted">avg &middot; best ${formatNumber(s.best)}</span></span></li>`;
            })
            .join("")}</ul>`
        : UNAVAILABLE
    );

    setHtml(
      "team-achievements",
      t.achievements.length
        ? `<ul class="list-rows">${t.achievements
            .map((a) => `<li><span>🏅 ${escapeHtml(a.name)}</span><span class="muted">${escapeHtml(a.player_name)}</span></li>`)
            .join("")}</ul>`
        : '<p class="unavailable">No achievements yet</p>'
    );
  }

  if (!/^[a-z0-9-]{1,48}$/.test(slug)) {
    notFound();
    return;
  }
  ShaheenAPI.getTeam(slug)
    .then(render)
    .catch(() => {
      setHtml("team-hero", UNAVAILABLE);
      ["team-roster", "team-seasons", "team-achievements"].forEach((id) => setHtml(id, UNAVAILABLE));
    });
})();
