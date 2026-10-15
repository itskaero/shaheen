// City Wars page (docs/DECISIONS.md ADR-130), from GET /rankings/cities
// (ADR-128). The city list and labels come from the API, never copied here.
(function () {
  const UNAVAILABLE = '<p class="unavailable">Data unavailable</p>';

  function seasonLabel(n) {
    return n >= 42 ? `Season ${n - 41}` : `Brawlhalla S${n}`;
  }

  function renderPodium(cities) {
    const box = document.getElementById("podium");
    if (!box) return;
    const top = cities.slice(0, 3);
    if (!top.length) {
      box.hidden = true;
      return;
    }
    // Silver, gold, bronze from left to right, like a real podium.
    const order = top.length === 3 ? [1, 0, 2] : top.map((_, i) => i);
    box.hidden = false;
    box.innerHTML = order
      .map((i) => {
        const c = top[i];
        return `<article class="ar-podium-step is-${i + 1}" id="${escapeHtml(c.key)}">
          <span class="ar-podium-place">${i + 1}</span>
          <h3>${escapeHtml(c.label)}</h3>
          <strong class="num">${formatNumber(c.rating)}</strong>
          <span class="muted">${c.players} placed player${c.players === 1 ? "" : "s"}</span>
          <span class="ar-podium-names">${c.top.slice(0, 3).map(escapeHtml).join(" &middot; ")}</span>
        </article>`;
      })
      .join("");
  }

  function renderStandings(cities, topN) {
    const el = document.getElementById("standings");
    const count = document.getElementById("cw-count");
    if (count) count.textContent = `${cities.length} cit${cities.length === 1 ? "y" : "ies"}`;
    if (!cities.length) {
      el.innerHTML = '<p class="unavailable">No city has placed players yet. Be the first to represent yours.</p>';
      return;
    }
    const best = cities[0].rating || 1;
    el.innerHTML = `<div class="bl-table-wrap"><table class="ar-table">
      <thead><tr><th scope="col">#</th><th scope="col">City</th><th scope="col" class="right">Score</th><th scope="col" class="right hide-sm">Placed</th><th scope="col" class="hide-sm">Top players</th></tr></thead>
      <tbody>${cities
        .map(
          (c, i) => `<tr${i > 2 ? ` id="${escapeHtml(c.key)}"` : ""}>
            <td>${rankHtml(i + 1)}</td>
            <td><strong>${escapeHtml(c.label)}</strong>
              <span class="ar-meter"><span style="width:${Math.max(4, Math.round((c.rating / best) * 100))}%"></span></span></td>
            <td class="right num">${formatNumber(c.rating)}</td>
            <td class="right num hide-sm">${c.players}</td>
            <td class="hide-sm muted">${c.top.map(escapeHtml).join(", ")}</td>
          </tr>`
        )
        .join("")}</tbody>
    </table></div>
    <p class="ar-hint">Score: the average of each city's best ${topN} placed 1v1 ratings this season.</p>`;
  }

  function render(board) {
    const cities = (board && board.cities) || [];
    const season = document.getElementById("cw-season");
    if (season && board && board.season) season.textContent = seasonLabel(board.season);
    renderPodium(cities);
    renderStandings(cities, (board && board.top_n) || 5);
  }

  ShaheenAPI.withSnapshot("cities", () => ShaheenAPI.getCityBoard(), render).catch(() => {
    const el = document.getElementById("standings");
    if (el && el.textContent.trim() === "Loading…") el.innerHTML = UNAVAILABLE;
    const podium = document.getElementById("podium");
    if (podium) podium.hidden = true;
  });
})();
