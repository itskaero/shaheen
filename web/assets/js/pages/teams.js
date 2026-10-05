// Teams list (docs/DECISIONS.md ADR-114): the founding team first, then by
// team rating. A team with nobody placed shows no rating rather than 0.
(function () {
  const UNAVAILABLE = '<p class="unavailable">Data unavailable</p>';
  const grid = document.getElementById("team-grid");
  const search = document.getElementById("t-search");
  let teams = [];

  function logoHtml(team, size) {
    if (!team.logo) {
      return `<span class="team-monogram" style="--size:${size}px" aria-hidden="true">${escapeHtml(team.tag)}</span>`;
    }
    const stem = `assets/img/teams/${encodeURIComponent(team.logo)}`;
    return `<picture>
      <source srcset="${stem}.webp" type="image/webp" />
      <img class="team-logo" src="${stem}.png" alt="" width="${size}" height="${size}" loading="lazy" />
    </picture>`;
  }

  // The whole card is one link, so nothing inside it may be a link too.
  function card(t) {
    const best = t.best
      ? `<span class="team-best">${avatarHtml(t.best.player_name, 22)}<span>${escapeHtml(t.best.player_name)}</span></span>`
      : '<span class="muted">—</span>';
    return `<a class="team-card${t.is_founding ? " is-founding" : ""}" href="team.html?t=${encodeURIComponent(t.slug)}">
      <div class="team-card-logo">${logoHtml(t, 112)}</div>
      <div class="team-card-name">
        <strong>${escapeHtml(t.name)}</strong>
        <span class="muted">${escapeHtml(t.tag)} &middot; ${t.country === "PK" ? "🇵🇰 Pakistan" : escapeHtml(t.country)}</span>
      </div>
      ${t.is_founding ? '<span class="pill pill-founding">Founding team</span>' : ""}
      <div class="team-card-stats">
        <div><strong class="num">${t.rating != null ? formatNumber(t.rating) : "—"}</strong><span>Team rating</span></div>
        <div><strong class="num">${t.members}</strong><span>Players</span></div>
      </div>
      <div class="team-card-best"><span class="muted">Best player</span>${best}</div>
    </a>`;
  }

  function render() {
    const q = (search.value || "").trim().toLowerCase();
    const shown = teams.filter((t) => !q || t.name.toLowerCase().includes(q) || t.tag.toLowerCase().includes(q));
    grid.innerHTML = shown.length ? shown.map(card).join("") : teams.length ? '<p class="unavailable">No team matches.</p>' : UNAVAILABLE;
  }

  search.addEventListener("input", render);
  ShaheenAPI.withSnapshot("teams", () => ShaheenAPI.getTeams(), (list) => {
    teams = Array.isArray(list) ? list : [];
    render();
  }).catch(() => {
    if (!teams.length) grid.innerHTML = UNAVAILABLE;
  });
})();
