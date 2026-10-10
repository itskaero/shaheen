// Coaches (docs/DECISIONS.md ADR-126): the coach directory. Coaches are the
// members holding the Coach role in Discord, listed by their linked
// Brawlhalla account; sessions are booked in Discord with /coach request.
// Accepting coaches come first, as the API sorts them.
(function () {
  const UNAVAILABLE = '<p class="unavailable">Data unavailable</p>';
  const grid = document.getElementById("coach-grid");
  const search = document.getElementById("c-search");
  let coaches = [];

  function profileHref(c) {
    return `player.html?p=${encodeURIComponent(c.slug)}`;
  }

  function legendsHtml(keys) {
    if (!keys || !keys.length) return "";
    return `<div class="coach-legends">${keys
      .map((k) => `<span class="coach-legend">${legendAvatarHtml(k, 26)}<span>${escapeHtml(legendDisplayName(k))}</span></span>`)
      .join("")}</div>`;
  }

  function cardHtml(c) {
    const status = c.accepting
      ? '<span class="pill pill-live card-pill">Taking students</span>'
      : '<span class="pill pill-muted card-pill">Full</span>';
    const avatar = c.legends && c.legends.length ? legendAvatarHtml(c.legends[0], 76) : avatarHtml(c.player_name, 76);
    return `<article class="coach-card">
      ${status}
      <a class="coach-who" href="${profileHref(c)}">
        ${avatar}
        <h3>${tagChipHtml(c.team_tag)}${escapeHtml(c.player_name)}</h3>
      </a>
      <span class="sub">${c.specialty ? escapeHtml(c.specialty) : "Coach"}</span>
      ${c.team ? `<div class="coach-team">${teamPillHtml(c.team, c.team_slug)}</div>` : ""}
      ${legendsHtml(c.legends)}
      ${c.bio ? `<p class="coach-bio">${escapeHtml(c.bio)}</p>` : ""}
      <div class="card-stats">
        <div><strong class="num">${formatNumber(c.rating)}</strong><span>Rating</span></div>
        <div><strong title="${escapeHtml(c.tier || "Unranked")}">${c.tier ? escapeHtml(c.tier.split(" ")[0]) : "Unranked"}</strong><span>Tier</span></div>
        <div><strong class="num">${formatNumber(c.sessions)}</strong><span>Sessions</span></div>
      </div>
      ${c.availability ? `<p class="coach-when"><span aria-hidden="true">🗓️</span> ${escapeHtml(c.availability)}</p>` : ""}
    </article>`;
  }

  function matches(c, q) {
    if (!q) return true;
    const legends = (c.legends || []).map(legendDisplayName);
    return [c.player_name, c.specialty, c.team, c.team_tag, c.availability, ...legends]
      .filter(Boolean)
      .join(" ")
      .toLowerCase()
      .includes(q);
  }

  function render() {
    const q = (search.value || "").trim().toLowerCase();
    const shown = coaches.filter((c) => matches(c, q));
    if (shown.length) {
      grid.innerHTML = `<div class="player-grid">${shown.map(cardHtml).join("")}</div>`;
    } else if (coaches.length) {
      grid.innerHTML = '<p class="unavailable">No coach matches.</p>';
    } else {
      grid.innerHTML = '<p class="unavailable">No coaches listed yet. Coaches appear here once they link their Brawlhalla account.</p>';
    }
  }

  search.addEventListener("input", render);
  ShaheenAPI.withSnapshot("coaches", () => ShaheenAPI.getCoaches(), (list) => {
    coaches = Array.isArray(list) ? list : [];
    render();
  }).catch(() => {
    if (!coaches.length) grid.innerHTML = UNAVAILABLE;
  });
})();
