// Teams (docs/DECISIONS.md ADR-114, ADR-116): one large slide per team in a
// swipeable row, the founding team first, then by team rating. A team with
// nobody placed shows no rating rather than 0.
(function () {
  const UNAVAILABLE = '<p class="unavailable">Data unavailable</p>';
  const track = document.getElementById("team-grid");
  const dots = document.getElementById("team-dots");
  const prev = document.getElementById("team-prev");
  const next = document.getElementById("team-next");
  const search = document.getElementById("t-search");
  let teams = [];

  // Each team's own glow, taken from its logo. A team without an entry
  // gets the BRAWLISTAN emerald.
  const ACCENTS = {
    shaheen: ["61, 242, 110", "240, 22, 140"],
    "delight-esports": ["42, 212, 255", "192, 60, 255"],
  };

  function logoHtml(team) {
    if (!team.logo) {
      return `<span class="team-monogram" aria-hidden="true">${escapeHtml(team.tag)}</span>`;
    }
    const stem = `assets/img/teams/${encodeURIComponent(team.logo)}`;
    return `<picture>
      <source srcset="${stem}.webp" type="image/webp" />
      <img class="team-logo" src="${stem}.png" alt="${escapeHtml(team.name)} logo" width="512" height="512" loading="lazy" />
    </picture>`;
  }

  // The whole slide is one link, so nothing inside it may be a link too.
  function slide(t, index) {
    const [a, b] = ACCENTS[t.slug] || ["30, 224, 138", "61, 242, 110"];
    const best = t.best
      ? `<span class="team-best">${avatarHtml(t.best.player_name, 22)}<span>${escapeHtml(t.best.player_name)}</span></span>`
      : '<span class="muted">—</span>';
    return `<a class="team-slide${t.is_founding ? " is-founding" : ""}" href="team.html?t=${encodeURIComponent(t.slug)}"
        style="--accent: ${a}; --accent-2: ${b}" aria-roledescription="slide" aria-label="${index + 1} of ${teams.length}: ${escapeHtml(t.name)}">
      <div class="team-slide-art">${logoHtml(t)}</div>
      <div class="team-slide-body">
        <div class="team-slide-pills">
          ${t.is_founding ? '<span class="pill pill-founding">Founding team</span>' : ""}
          <span class="pill pill-muted">${escapeHtml(t.tag)}</span>
          <span class="pill pill-muted">${t.country === "PK" ? "🇵🇰 Pakistan" : escapeHtml(t.country)}</span>
        </div>
        <strong class="team-slide-name">${escapeHtml(t.name)}</strong>
        <div class="team-slide-stats">
          <div><strong class="num">${t.rating != null ? formatNumber(t.rating) : "—"}</strong><span>Team rating</span></div>
          <div><strong class="num">${t.members}</strong><span>Players</span></div>
        </div>
        <div class="team-card-best"><span class="muted">Best player</span>${best}</div>
        <span class="team-slide-cta">View team &rarr;</span>
      </div>
    </a>`;
  }

  function shown() {
    const q = (search.value || "").trim().toLowerCase();
    return teams.filter((t) => !q || t.name.toLowerCase().includes(q) || t.tag.toLowerCase().includes(q));
  }

  function render() {
    const list = shown();
    track.innerHTML = list.length ? list.map(slide).join("") : teams.length ? '<p class="unavailable">No team matches.</p>' : UNAVAILABLE;
    dots.innerHTML = list.length > 1
      ? list.map((t, i) => `<button type="button" role="tab" aria-label="${escapeHtml(t.name)}" data-i="${i}"></button>`).join("")
      : "";
    track.scrollLeft = 0;
    sync();
  }

  function slides() {
    return [...track.querySelectorAll(".team-slide")];
  }

  // The slide snapped to the start of the row.
  function current() {
    const all = slides();
    const left = track.scrollLeft;
    let best = 0;
    all.forEach((el, i) => {
      if (Math.abs(el.offsetLeft - left) < Math.abs(all[best].offsetLeft - left)) best = i;
    });
    // At the far end the last slides can't reach the start; light the last dot.
    if (left + track.clientWidth >= track.scrollWidth - 2) best = all.length - 1;
    return best;
  }

  function go(i) {
    const all = slides();
    if (!all.length) return;
    const target = all[Math.max(0, Math.min(all.length - 1, i))];
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    track.scrollTo({ left: target.offsetLeft - 4, behavior: reduce ? "auto" : "smooth" });
  }

  function sync() {
    const all = slides();
    const i = all.length ? current() : 0;
    dots.querySelectorAll("button").forEach((d, n) => d.setAttribute("aria-selected", String(n === i)));
    const fits = track.scrollWidth <= track.clientWidth + 2;
    prev.hidden = next.hidden = fits || all.length < 2;
    prev.disabled = track.scrollLeft <= 2;
    next.disabled = track.scrollLeft + track.clientWidth >= track.scrollWidth - 2;
  }

  prev.addEventListener("click", () => go(current() - 1));
  next.addEventListener("click", () => go(current() + 1));
  dots.addEventListener("click", (e) => {
    const d = e.target.closest("button");
    if (d) go(Number(d.dataset.i));
  });
  track.addEventListener("keydown", (e) => {
    if (e.key === "ArrowRight" || e.key === "ArrowLeft") {
      e.preventDefault();
      go(current() + (e.key === "ArrowRight" ? 1 : -1));
    }
  });
  let raf = 0;
  track.addEventListener("scroll", () => {
    cancelAnimationFrame(raf);
    raf = requestAnimationFrame(sync);
  });
  window.addEventListener("resize", sync);
  search.addEventListener("input", render);

  ShaheenAPI.withSnapshot("teams", () => ShaheenAPI.getTeams(), (list) => {
    teams = Array.isArray(list) ? list : [];
    render();
  }).catch(() => {
    if (!teams.length) track.innerHTML = UNAVAILABLE;
  });
})();
