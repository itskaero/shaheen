// Seasons page (docs/DECISIONS.md ADR-113): every Pakistan season's card,
// and for the selected one its champion, rising player, Legend of the
// season, top 10 and tournaments. Numbers come only from stored readings; a
// part with nothing real to show says so.
(function () {
  const UNAVAILABLE = '<p class="unavailable">Data unavailable</p>';
  const UPCOMING = '<p class="unavailable">Upcoming season</p>';
  const DAY = 24 * 60 * 60 * 1000;

  const params = new URLSearchParams(location.search);
  let selected = Number(params.get("s")) || null; // a Brawlhalla season number
  let cards = [];

  function setHtml(id, html) {
    const el = document.getElementById(id);
    if (el) el.innerHTML = html;
  }

  function badgeImg(season, cls, size) {
    const stem = `assets/img/seasons/${encodeURIComponent(season.badge)}`;
    return `<picture>
      <source srcset="${stem}.webp" type="image/webp" />
      <img class="${cls}" src="${stem}.jpg" alt="" width="${size}" height="${Math.round(size * 0.97)}" loading="lazy" />
    </picture>`;
  }

  function date(iso) {
    return new Date(iso).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
  }

  const STATUS = {
    current: '<span class="pill pill-live">● Live</span>',
    past: '<span class="pill pill-muted">Completed</span>',
    upcoming: '<span class="pill pill-muted">Upcoming</span>',
  };

  function profileHref(id) {
    return `player.html?id=${encodeURIComponent(id)}`;
  }

  // ---- the strip of season cards ----
  function renderStrip() {
    setHtml(
      "season-strip",
      cards
        .map((c) => {
          const s = c.season;
          const note =
            c.status === "current" ? "Live now" : c.status === "upcoming" ? "Upcoming" : c.champion ? `👑 ${escapeHtml(c.champion)}` : "Completed";
          return `<button type="button" class="season-chip is-${c.status}" data-season="${s.brawlhalla_season}"
              aria-pressed="${s.brawlhalla_season === selected}" aria-label="Pakistan Season ${s.number}, ${escapeHtml(s.name)}">
            ${badgeImg(s, "season-chip-img", 92)}
            <span class="season-chip-num">Season ${s.number}</span>
            <strong>${escapeHtml(s.name)}</strong>
            <span class="season-chip-note">${note}</span>
          </button>`;
        })
        .join("")
    );
    const active = document.querySelector('.season-chip[aria-pressed="true"]');
    if (active && active.scrollIntoView) active.scrollIntoView({ block: "nearest", inline: "center" });
  }

  document.getElementById("season-strip").addEventListener("click", (event) => {
    const chip = event.target.closest(".season-chip");
    if (!chip) return;
    select(Number(chip.dataset.season));
  });

  function select(season) {
    selected = season;
    const url = new URL(location.href);
    url.searchParams.set("s", String(season));
    history.replaceState(null, "", url);
    document.querySelectorAll(".season-chip").forEach((chip) => {
      chip.setAttribute("aria-pressed", String(Number(chip.dataset.season) === season));
    });
    loading();
    ShaheenAPI.getSeason(season).then(renderDetail).catch(failed);
  }

  function loading() {
    ["season-champion", "season-rising", "season-legend", "season-top", "season-tournaments"].forEach((id) =>
      setHtml(id, '<p class="unavailable">Loading…</p>')
    );
  }

  function failed() {
    ["season-champion", "season-rising", "season-legend", "season-top", "season-tournaments"].forEach((id) => {
      const el = document.getElementById(id);
      if (el && el.textContent.trim() === "Loading…") el.innerHTML = UNAVAILABLE;
    });
  }

  // ---- the selected season ----
  function renderHero(detail) {
    const s = detail.season;
    const now = Date.now();
    const start = new Date(s.starts_at).getTime();
    const end = new Date(s.ends_at).getTime();
    let timeline = "";
    if (detail.status === "current") {
      const pct = Math.min(100, Math.max(0, ((now - start) / (end - start)) * 100));
      const left = Math.max(0, Math.ceil((end - now) / DAY));
      timeline = `<div class="season-progress" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${Math.round(pct)}" aria-label="Season progress">
          <span style="width:${pct.toFixed(1)}%"></span>
        </div>
        <span class="muted">${left} day${left === 1 ? "" : "s"} left</span>`;
    } else if (detail.status === "upcoming") {
      const until = Math.max(0, Math.ceil((start - now) / DAY));
      timeline = `<span class="muted">Starts in about ${until} day${until === 1 ? "" : "s"}</span>`;
    }
    setHtml(
      "season-hero",
      `${badgeImg(s, "season-hero-card", 220)}
      <div class="season-hero-copy">
        <span class="season-kicker">Pakistan Season ${s.number} ${STATUS[detail.status] || ""}</span>
        <h2>Season of <span class="season-name-word">${escapeHtml(s.name)}</span></h2>
        <span class="season-urdu" lang="ur">${escapeHtml(s.name_urdu)}</span>
        <span class="season-meta">Brawlhalla Season ${s.brawlhalla_season} &middot; ${date(s.starts_at)} – ${date(s.ends_at)}</span>
        ${timeline}
      </div>`
    );
    document.title = `Season of ${s.name} — Pakistan Season ${s.number} | BRAWLISTAN`;
  }

  function playerCard(id, name, lines) {
    return `<a class="featured" href="${profileHref(id)}">
      ${avatarHtml(name, 52)}
      <span><strong>${escapeHtml(name)}</strong>${lines}</span>
    </a>`;
  }

  function renderDetail(detail) {
    if (!detail) return failed();
    renderHero(detail);
    const upcoming = detail.status === "upcoming";
    document.getElementById("champ-title").textContent = detail.status === "current" ? "Leader so far" : "Champion";
    const link = document.getElementById("top-link");
    if (link) link.href = `rankings.html?season=${encodeURIComponent(detail.season.brawlhalla_season)}#pakistan`;

    const champ = detail.top[0];
    setHtml(
      "season-champion",
      upcoming
        ? UPCOMING
        : champ
          ? playerCard(
              champ.brawlhalla_id,
              champ.player_name,
              `<span class="muted num">${formatNumber(champ.rating)} rating</span><span style="display:block;margin-top:6px">${tierBadge(champ.tier)}</span>`
            )
          : UNAVAILABLE
    );

    const r = detail.rising;
    setHtml(
      "season-rising",
      upcoming
        ? UPCOMING
        : r
          ? playerCard(r.brawlhalla_id, r.player_name, `<span class="trend-up num">▲ ${formatNumber(r.rating_gain)}</span> <span class="muted num">to ${formatNumber(r.rating)}</span>`)
          : UNAVAILABLE
    );

    const l = detail.legend;
    setHtml(
      "season-legend",
      upcoming
        ? UPCOMING
        : l
          ? `<div class="featured season-legend">
              ${legendAvatarHtml(l.legend_name_key, 52)}
              <span>
                <strong>${escapeHtml(legendDisplayName(l.legend_name_key))}</strong>
                <span class="muted num">${formatNumber(l.games)} games &middot; ${l.win_rate}% wins</span>
                <span class="muted" style="display:block">played by ${l.players} player${l.players === 1 ? "" : "s"} this season</span>
              </span>
            </div>`
          : UNAVAILABLE
    );

    setHtml(
      "season-top",
      upcoming
        ? UPCOMING
        : detail.top.length
          ? `<div class="bl-table-wrap"><table class="bl-table">
              <thead><tr><th scope="col">#</th><th scope="col">Player</th><th scope="col" class="hide-sm">Tier</th><th scope="col" class="right">Rating</th></tr></thead>
              <tbody>${detail.top
                .map(
                  (row, i) => `<tr>
                    <td>${rankHtml(i + 1)}</td>
                    <td><a class="bl-player" href="${profileHref(row.brawlhalla_id)}">${avatarHtml(row.player_name, 28)}<span class="bl-player-name">${escapeHtml(row.player_name)}</span></a></td>
                    <td class="hide-sm">${tierBadge(row.tier)}</td>
                    <td class="right num">${formatNumber(row.rating)}</td>
                  </tr>`
                )
                .join("")}</tbody>
            </table></div>`
          : UNAVAILABLE
    );

    setHtml(
      "season-tournaments",
      upcoming
        ? UPCOMING
        : detail.tournaments.length
          ? `<ul class="list-rows">${detail.tournaments
              .map(
                (t) => `<li><a href="tournament.html?id=${encodeURIComponent(t.id)}">${escapeHtml(t.name)}</a>
                  <span class="muted">${escapeHtml(t.kind)} &middot; ${escapeHtml(t.status.replace("_", " "))}</span></li>`
              )
              .join("")}</ul>`
          : '<p class="unavailable">No tournaments this season</p>'
    );
  }

  // ---- load ----
  ShaheenAPI.withSnapshot("seasons", () => ShaheenAPI.getSeasons(), (list) => {
    cards = Array.isArray(list) ? list : [];
    if (!selected) {
      const current = cards.find((c) => c.status === "current");
      selected = current ? current.season.brawlhalla_season : null;
    }
    renderStrip();
  }).catch(() => setHtml("season-strip", UNAVAILABLE));

  const firstLoad = params.get("s")
    ? ShaheenAPI.getSeason(selected).then(renderDetail)
    : ShaheenAPI.withSnapshot("season-current", () => ShaheenAPI.getCurrentSeason(), renderDetail);
  firstLoad.catch(() => {
    failed();
    const hero = document.getElementById("season-hero");
    if (hero && hero.textContent.trim() === "Loading…") hero.innerHTML = UNAVAILABLE;
  });
})();
