// BRAWLISTAN home (docs/DECISIONS.md ADR-104). Every section reads the
// cached site snapshot first (web/data/*.json) and then the live API, and a
// section with nothing real to show says "Data unavailable" rather than
// inventing a number.
(function () {
  const UNAVAILABLE = '<p class="unavailable">Data unavailable</p>';

  function setHtml(id, html) {
    const el = document.getElementById(id);
    if (el) el.innerHTML = html;
  }

  function profileHref(entry) {
    return `player.html?id=${encodeURIComponent(entry.brawlhalla_id)}`;
  }

  function verifiedPill(entry) {
    return entry.is_claimed ? '<span class="pill pill-verified" title="Claimed by its player">✓ Claimed</span>' : "";
  }

  // ---- Pakistan Top 10 + featured player ----
  function renderTop10(entries) {
    const top = (entries || []).filter((e) => e.rating != null).slice(0, 10);
    if (!top.length) {
      setHtml("top10", UNAVAILABLE);
      if (!staffPick) setHtml("featured", UNAVAILABLE);
      return;
    }
    setHtml(
      "top10",
      `<div class="bl-table-wrap"><table class="bl-table">
        <thead><tr>
          <th scope="col">#</th><th scope="col">Player</th>
          <th scope="col" class="hide-sm">Tier</th><th scope="col" class="right">Rating</th>
        </tr></thead>
        <tbody>${top
          .map(
            (e, i) => `<tr>
              <td>${rankHtml(i + 1)}</td>
              <td><a class="bl-player" href="${profileHref(e)}">${avatarHtml(e.player_name, 28)}<span class="bl-player-name">${escapeHtml(e.player_name)}</span></a>
                ${e.is_clan_member ? '<span class="pill pill-team">SHAHEEN</span>' : ""} ${verifiedPill(e)}</td>
              <td class="hide-sm">${tierBadge(e.tier)}</td>
              <td class="right num">${formatNumber(e.rating)}</td>
            </tr>`
          )
          .join("")}</tbody>
      </table></div>`
    );

    topFirst = top[0];
    paintFeatured();
  }

  // ---- featured player: staff's /feature pick (ADR-111), else Pakistan #1 ----
  let staffPick = null;
  let topFirst = null;

  function paintFeatured() {
    const pick = staffPick || topFirst;
    if (!pick) return;
    const why = staffPick
      ? escapeHtml(staffPick.note || "Picked by BRAWLISTAN staff")
      : `Pakistan #1 this season &middot; ${formatNumber(pick.rating)}`;
    setHtml(
      "featured",
      `<a class="featured" href="${profileHref(pick)}">
        ${avatarHtml(pick.player_name, 52)}
        <span>
          <strong>${escapeHtml(pick.player_name)}</strong>
          <span class="muted">${why}</span>
          <span style="display:block;margin-top:6px">${tierBadge(pick.tier)}${
            staffPick && pick.rating != null ? ` <span class="num muted">${formatNumber(pick.rating)}</span>` : ""
          }</span>
        </span>
      </a>`
    );
  }

  // ---- current season (ADR-102) ----
  function renderSeason(clan) {
    const season = clan && clan.pakistan_season;
    if (!season) {
      setHtml("season", UNAVAILABLE);
      return;
    }
    const badge = `assets/img/seasons/${encodeURIComponent(season.badge)}`;
    const until = new Date(season.ends_at).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
    setHtml(
      "season",
      `<div class="season-card">
        <picture><source srcset="${badge}.webp" type="image/webp" /><img src="${badge}.jpg" alt="Season of ${escapeHtml(season.name)} card" width="88" height="80" loading="lazy" /></picture>
        <div>
          <span class="eyebrow">Season ${season.number}</span>
          <h3>${escapeHtml(season.name)}</h3>
          <span class="urdu" lang="ur">${escapeHtml(season.name_urdu)}</span>
          <span class="muted" style="font-size:12.5px">Brawlhalla S${season.brawlhalla_season} &middot; until about ${until}</span>
        </div>
      </div>`
    );
  }

  // ---- hero stats + community, from /clan ----
  // ---- hero stat tiles: numbers count up once (ADR-112) ----
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const shown = new Map(); // label -> last value painted, so a refresh doesn't replay

  function countUp(el, to, from) {
    if (reduceMotion || to === from) {
      el.textContent = to.toLocaleString();
      return;
    }
    const start = performance.now();
    const duration = 1100;
    (function step(now) {
      const t = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - t, 3);
      el.textContent = Math.round(from + (to - from) * eased).toLocaleString();
      if (t < 1) requestAnimationFrame(step);
    })(start);
  }

  function renderHeroStats(stats) {
    const box = document.getElementById("hero-stats");
    if (!box) return;
    box.innerHTML = stats
      .map(([v, l]) => `<div><strong>${typeof v === "number" ? "0" : escapeHtml(v)}</strong><span>${escapeHtml(l)}</span></div>`)
      .join("");
    stats.forEach(([v, l], i) => {
      if (typeof v !== "number") return;
      countUp(box.children[i].querySelector("strong"), v, shown.has(l) ? shown.get(l) : 0);
      shown.set(l, v);
    });
  }

  function renderClanNumbers(clan) {
    const stats = [];
    if (clan && clan.pakistan_season) stats.push([`S${clan.pakistan_season.number}`, clan.pakistan_season.name]);
    if (clan && typeof clan.discord_member_count === "number") stats.push([clan.discord_member_count, "in the Discord"]);
    if (clan && typeof clan.member_count === "number") stats.push([clan.member_count, "linked players"]);
    renderHeroStats(stats);

    if (!clan || typeof clan.discord_member_count !== "number") {
      setHtml("community", UNAVAILABLE);
      return;
    }
    setHtml(
      "community",
      `<p style="margin:0 0 14px" class="muted">Rankings talk, clips, looking-for-game and tournaments all happen in the Discord. Link your Brawlhalla account there with <code>/link</code> to claim your profile.</p>
      <ul class="list-rows">
        <li><span>Discord members</span><strong class="num">${clan.discord_member_count.toLocaleString()}</strong></li>
        <li><span>Players with a linked account</span><strong class="num">${formatNumber(clan.member_count)}</strong></li>
      </ul>
      <a class="btn btn-ghost btn-sm" style="margin-top:14px" data-discord-invite href="${typeof DISCORD_INVITE_URL !== "undefined" ? DISCORD_INVITE_URL : "join.html"}" target="_blank" rel="noopener">Join the Discord</a>`
    );
  }

  function renderRising(entries) {
    if (!entries || !entries.length) {
      setHtml("rising", UNAVAILABLE);
      return;
    }
    setHtml(
      "rising",
      `<ul class="list-rows">${entries
        .slice(0, 6)
        .map(
          (e) => `<li>
            <a class="bl-player" href="${profileHref(e)}">${avatarHtml(e.player_name, 26)}<span class="bl-player-name">${escapeHtml(e.player_name)}</span></a>
            <span class="num"><span class="trend-up">▲ ${e.rating_gain.toLocaleString()}</span> <span class="muted">${e.rating.toLocaleString()}</span></span>
          </li>`
        )
        .join("")}</ul>`
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
      entries
        .slice(0, 5)
        .map(
          (e) => `<div class="legend-row">
            ${legendAvatarHtml(e.legend_name_key, 34)}
            <div>
              <strong style="font-size:14px">${escapeHtml(legendDisplayName(e.legend_name_key))}</strong>
              <div class="meter"><span style="width:${Math.max(4, Math.round((e.total_games / most) * 100))}%"></span></div>
            </div>
            <span class="muted num" style="font-size:12.5px;text-align:right">${e.player_count} player${e.player_count === 1 ? "" : "s"}<br />${e.win_rate}% WR</span>
          </div>`
        )
        .join("")
    );
  }

  const STATUS = {
    registration: ["Upcoming", "pill"],
    in_progress: ["Live", "pill pill-live"],
    completed: ["Completed", "pill"],
    cancelled: ["Cancelled", "pill"],
  };

  function renderTournament(tournaments) {
    const latest = (tournaments || []).find((t) => t.status !== "cancelled");
    if (!latest) {
      setHtml("tournament", UNAVAILABLE);
      return;
    }
    const [label, cls] = STATUS[latest.status] || [latest.status, "pill"];
    setHtml(
      "tournament",
      `<a href="tournament.html?id=${encodeURIComponent(latest.id)}" style="display:block">
        <span class="${cls}">${escapeHtml(label)}</span>
        <h3 style="margin:10px 0 4px;font-size:17px">${escapeHtml(latest.name)}</h3>
        <span class="muted" style="font-size:13px">${escapeHtml(latest.kind)}${latest.started_at ? ` &middot; ${formatDate(latest.started_at)}` : ""}</span>
      </a>`
    );
  }

  // A failed fetch leaves its sections saying "Data unavailable" instead of
  // "Loading…" forever. Sections that already rendered (from the snapshot)
  // are left alone.
  function guard(ids, promise) {
    promise.catch(() => {
      ids.forEach((id) => {
        const el = document.getElementById(id);
        if (el && el.textContent.trim() === "Loading…") el.innerHTML = UNAVAILABLE;
      });
    });
  }

  guard(
    ["top10", "featured"],
    ShaheenAPI.withSnapshot("pakistan", () => ShaheenAPI.getPakistanLeaderboard(10), renderTop10)
  );
  guard(
    ["season", "community"],
    ShaheenAPI.withSnapshot("clan", () => ShaheenAPI.getClan(), (clan) => {
      renderSeason(clan);
      renderClanNumbers(clan);
    })
  );
  ShaheenAPI.withSnapshot("featured", () => ShaheenAPI.getFeatured(), (pick) => {
    staffPick = pick && pick.player_name ? pick : null;
    paintFeatured();
  }).catch(() => {});
  guard(["rising"], ShaheenAPI.withSnapshot("rising", () => ShaheenAPI.getPakistanRising(7, 10), renderRising));
  guard(
    ["legend-meta"],
    ShaheenAPI.withSnapshot("legend-meta", () => ShaheenAPI.getLegendMeta(10), renderLegendMeta)
  );
  guard(["tournament"], ShaheenAPI.getTournaments(5).then(renderTournament));
})();
