// BRAWLISTAN player profile (docs/DECISIONS.md ADR-106).
//
// The player comes from, in order: a generated SEO page's
// <body data-player-id>, ?id=, or the trailing id of ?p=<slug>. Ranking
// context the per-player API doesn't carry (Pakistan rank, team, claim,
// 7-day trend, 2v2) comes from the same cached rankings/players snapshots the
// Rankings and Players pages use, so the profile never disagrees with them.
(function () {
  const el = document.getElementById("profile");
  const UNAVAILABLE = '<p class="unavailable">Data unavailable</p>';
  const COUNTRIES = { PK: "Pakistan" };

  function idFromPage() {
    if (document.body.dataset.playerId) return document.body.dataset.playerId;
    const params = new URLSearchParams(location.search);
    if (params.get("id")) return params.get("id");
    const slug = params.get("p") || "";
    const tail = slug.split("-").pop();
    return /^\d+$/.test(tail) ? tail : null;
  }

  const brawlhallaId = idFromPage();
  if (!brawlhallaId || !/^\d{1,12}$/.test(brawlhallaId)) {
    el.innerHTML = `<div class="panel empty-panel">
      <h2>Pick a player</h2>
      <p>Find someone on the <a href="players.html" class="muted" style="text-decoration:underline">Players</a> page or the <a href="rankings.html" class="muted" style="text-decoration:underline">Rankings</a>.</p>
    </div>`;
    return;
  }

  // Cached site data, then live. Each resolves to null rather than failing
  // the whole page.
  function cached(name, live) {
    return new Promise((resolve) => {
      let got = null;
      ShaheenAPI.withSnapshot(name, live, (data) => {
        got = data;
      })
        .then(() => resolve(got))
        .catch(() => resolve(got));
    });
  }

  function tile(label, value, small = "") {
    return `<div class="stat-tile"><span>${label}</span><strong>${value}</strong>${small ? `<small>${small}</small>` : ""}</div>`;
  }

  function seasonName(s) {
    return s.pakistan_season_number ? `Season ${s.pakistan_season_number} · ${escapeHtml(s.pakistan_season_name)}` : `Brawlhalla S${s.season}`;
  }

  function mainLegendsHtml(legends) {
    if (!legends || !legends.length) return UNAVAILABLE;
    return `<div class="main-legends">${legends
      .slice(0, 3)
      .map((l) => {
        const portrait = legendPortraitUrl(l.legend_name_key);
        const art = portrait ? `<img src="${portrait}" alt="" width="56" height="56" loading="lazy" />` : avatarHtml(legendDisplayName(l.legend_name_key), 56);
        const wr = l.games ? Math.round((l.wins / l.games) * 100) : 0;
        return `<div class="main-legend">${art}<div>
          <strong>${escapeHtml(legendDisplayName(l.legend_name_key))}</strong>
          <div class="muted" style="font-size:12.5px">${formatNumber(l.games)} games · ${wr}% WR · ${formatNumber(l.kos)} KOs</div>
        </div></div>`;
      })
      .join("")}</div>`;
  }

  function legendTableHtml(legends) {
    if (!legends || !legends.length) return UNAVAILABLE;
    return `<div class="bl-table-wrap"><table class="bl-table">
      <thead><tr><th scope="col">Legend</th><th scope="col" class="right">Games</th><th scope="col" class="right">Win %</th>
      <th scope="col" class="right hide-sm">KOs</th><th scope="col" class="right hide-sm">Damage</th><th scope="col" class="right hide-sm">Falls</th></tr></thead>
      <tbody>${legends
        .map(
          (l) => `<tr>
            <td><span class="legend-cell">${legendAvatarHtml(l.legend_name_key, 24)}${escapeHtml(legendDisplayName(l.legend_name_key))}</span></td>
            <td class="right num">${formatNumber(l.games)}</td>
            <td class="right num">${l.games ? Math.round((l.wins / l.games) * 100) : 0}%</td>
            <td class="right num hide-sm">${formatNumber(l.kos)}</td>
            <td class="right num hide-sm">${formatNumber(l.damagedealt)}</td>
            <td class="right num hide-sm">${formatNumber(l.falls)}</td>
          </tr>`
        )
        .join("")}</tbody></table></div>
      <p class="muted" style="font-size:12px;margin:10px 0 0">Lifetime games across all modes, from the official Brawlhalla API.</p>`;
  }

  function seasonsHtml(seasons) {
    if (!seasons || !seasons.length) return UNAVAILABLE;
    return `<div class="bl-table-wrap"><table class="bl-table">
      <thead><tr><th scope="col">Season</th><th scope="col" class="right">Final</th><th scope="col" class="right">Peak</th></tr></thead>
      <tbody>${seasons
        .map((s) => `<tr><td>${seasonName(s)}</td><td class="right num">${formatNumber(s.final_rating)}</td><td class="right num">${formatNumber(s.peak_rating)}</td></tr>`)
        .join("")}</tbody></table></div>`;
  }

  function matchesHtml(matches) {
    if (!matches || !matches.length) return UNAVAILABLE;
    return `<ul class="list-rows">${matches
      .map(
        (m) => `<li>
          <span><span class="pill ${m.won ? "pill-live" : "pill-muted"}">${m.won ? "Win" : "Loss"}</span>
          <span style="margin-left:8px">${escapeHtml(m.kind)} vs ${m.opponents.length ? escapeHtml(m.opponents.join(" & ")) : "unknown"}</span></span>
          <span class="muted" style="font-size:12.5px">${formatDate(m.confirmed_at)}</span>
        </li>`
      )
      .join("")}</ul>`;
  }

  function achievementsHtml(checklist, earnedOnly) {
    const entries = checklist || (earnedOnly || []).map((a) => ({ ...a, earned: true }));
    if (!entries.length) return UNAVAILABLE;
    const earned = entries.filter((e) => e.earned);
    const sorted = [...earned, ...entries.filter((e) => !e.earned)];
    return `<p class="muted" style="margin:0 0 12px;font-size:13px">${earned.length} of ${entries.length} earned</p>
      <div class="achievement-chips">${sorted
        .map(
          (a) => `<div class="achievement-chip ${a.earned ? "earned" : "locked"}">
            <span aria-hidden="true">${a.earned ? "🏅" : "🔒"}</span>
            <span><strong>${escapeHtml(a.name)}</strong><small>${escapeHtml(a.description)}${a.earned && a.awarded_at ? ` · ${formatDate(a.awarded_at)}` : ""}</small></span>
          </div>`
        )
        .join("")}</div>`;
  }

  function trendText(trend) {
    if (trend == null) return "";
    if (trend > 0) return `<span class="trend-up">▲ ${trend}</span> this week`;
    if (trend < 0) return `<span class="trend-down">▼ ${Math.abs(trend)}</span> this week`;
    return "No change this week";
  }

  // ---------- claim (ADR-107) ----------
  function claimedHtml(entry) {
    return `<p class="muted" style="margin:0">${
      entry.is_verified
        ? "Claimed and <strong>verified</strong>: staff confirmed this Brawlhalla account belongs to the member who claimed it."
        : "Claimed by a member of the BRAWLISTAN Discord. Staff haven't verified the account owner yet."
    } Their Discord account stays private.</p>`;
  }

  function claimFormHtml() {
    return `<p class="muted" style="margin:0 0 12px">Is this you? Run <code>/link</code> in the BRAWLISTAN Discord (with no ID) to get a one-time code, then enter it here.</p>
      <form id="claim-form" class="filters" style="margin:0" novalidate>
        <div class="field">
          <label for="claim-code">Link code</label>
          <input id="claim-code" class="input" name="code" inputmode="text" autocomplete="one-time-code"
            placeholder="XXXX-XXXX" maxlength="9" pattern="[A-Za-z0-9]{4}-?[A-Za-z0-9]{4}" required />
        </div>
        <button type="submit" class="btn btn-brand btn-sm" style="height:36px">Claim this profile</button>
        <a class="btn btn-ghost btn-sm" style="height:36px" data-discord-invite href="${typeof DISCORD_INVITE_URL !== "undefined" ? DISCORD_INVITE_URL : "join.html"}" target="_blank" rel="noopener">Open Discord</a>
      </form>
      <p id="claim-result" role="status" aria-live="polite" class="muted" style="margin:10px 0 0;min-height:1.4em"></p>`;
  }

  function wireClaimForm(profile) {
    const form = document.getElementById("claim-form");
    if (!form) return;
    const input = document.getElementById("claim-code");
    const result = document.getElementById("claim-result");
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const code = input.value.trim();
      if (!/^[A-Za-z0-9]{4}-?[A-Za-z0-9]{4}$/.test(code)) {
        result.textContent = "Codes look like ABCD-EFGH. Run /link in the Discord to get one.";
        input.focus();
        return;
      }
      const button = form.querySelector('button[type="submit"]');
      button.disabled = true;
      result.textContent = "Checking…";
      const response = await ShaheenAPI.claimProfile(profile.brawlhalla_id, code);
      button.disabled = false;
      if (response.ok) {
        form.remove();
        result.innerHTML = `<strong class="trend-up">Linked.</strong> ${escapeHtml(response.data.player_name)} is now yours. Staff can verify it next; the site updates within a few hours.`;
        return;
      }
      const detail = response.data && typeof response.data.detail === "string" ? response.data.detail : "That didn't work. Try again.";
      result.textContent = detail;
    });
  }

  // ---------- compare ----------
  function compareHtml(me, others) {
    const options = others
      .filter((p) => String(p.brawlhalla_id) !== String(me.brawlhalla_id))
      .map((p) => `<option value="${p.brawlhalla_id}">${escapeHtml(p.player_name)}</option>`)
      .join("");
    return `<section class="panel panel-pad" id="compare" hidden style="margin-top:16px" aria-labelledby="compare-title">
      <div class="section-head"><h2 id="compare-title">Compare</h2></div>
      <div class="field" style="max-width:320px;margin-bottom:14px">
        <label for="compare-with">Compare with</label>
        <select id="compare-with" class="select"><option value="">Choose a player</option>${options}</select>
      </div>
      <div id="compare-body"></div>
    </section>`;
  }

  function renderCompare(a, b) {
    const rows = [
      ["Rating", a.rating, b.rating, true],
      ["Peak", a.peak_rating, b.peak_rating, true],
      ["Global rank", a.global_rank, b.global_rank, false],
      ["2v2 rating", a.rating_2v2, b.rating_2v2, true],
      ["7-day change", a.trend, b.trend, true],
    ];
    const cell = (v, other, higherBetter, side) => {
      const better = v != null && other != null && v !== other && (higherBetter ? v > other : v < other);
      return `<span class="${side}${better ? " better" : ""} num">${formatNumber(v)}</span>`;
    };
    document.getElementById("compare-body").innerHTML = `<div class="compare-grid">
      <strong class="left">${escapeHtml(a.player_name)}</strong><span></span><strong>${escapeHtml(b.player_name)}</strong>
      ${rows.map(([label, x, y, hb]) => `${cell(x, y, hb, "left")}<span class="label">${label}</span>${cell(y, x, hb, "")}`).join("")}
      <span class="left">${a.tier ? tierBadge(a.tier) : "—"}</span><span class="label">Tier</span><span>${b.tier ? tierBadge(b.tier) : "—"}</span>
      <span class="left">${a.main_legend ? escapeHtml(legendDisplayName(a.main_legend)) : "—"}</span><span class="label">Main legend</span><span>${b.main_legend ? escapeHtml(legendDisplayName(b.main_legend)) : "—"}</span>
    </div>`;
  }

  async function load() {
    const [profile, history, legends, matches, checklist, seasons, rankings, directory] = await Promise.all([
      // api.js returns null for a 404 and throws on any other failure.
      ShaheenAPI.getPlayer(brawlhallaId).catch(() => undefined),
      ShaheenAPI.getPlayerHistory(brawlhallaId, 100).catch(() => null),
      ShaheenAPI.getPlayerLegends(brawlhallaId, 6).catch(() => null),
      ShaheenAPI.getPlayerMatches(brawlhallaId, 10).catch(() => null),
      ShaheenAPI.getPlayerAchievements(brawlhallaId).catch(() => null),
      ShaheenAPI.getPlayerSeasons(brawlhallaId).catch(() => null),
      cached("rankings", () => ShaheenAPI.getRankings()),
      cached("players", () => ShaheenAPI.getPlayers()),
    ]);

    if (profile === null) {
      el.innerHTML = `<div class="panel empty-panel"><h2>No such player</h2><p>BRAWLISTAN doesn't track a player with Brawlhalla ID ${escapeHtml(brawlhallaId)}.</p></div>`;
      return;
    }
    if (profile === undefined) {
      el.innerHTML = UNAVAILABLE;
      return;
    }

    const entry = (directory || []).find((p) => String(p.brawlhalla_id) === String(brawlhallaId)) || {};
    const rated = ((rankings && rankings.rows) || []).filter((r) => r.rating != null);
    const rankIndex = rated.findIndex((r) => String(r.brawlhalla_id) === String(brawlhallaId));
    const rankRow = ((rankings && rankings.rows) || []).find((r) => String(r.brawlhalla_id) === String(brawlhallaId)) || {};
    const slug = entry.slug || `player-${brawlhallaId}`;

    document.title = `${profile.player_name} — Pakistan Brawlhalla Ranking | BRAWLISTAN`;

    const country = entry.country ? `${entry.country === "PK" ? "🇵🇰 " : ""}${escapeHtml(COUNTRIES[entry.country] || entry.country)}` : "Country not set";
    const claimText = entry.is_verified
      ? '<span class="pill pill-verified" title="Staff confirmed this account\'s owner">✓ Verified</span>'
      : entry.is_claimed
        ? '<span class="pill pill-team" title="Linked to a member of the BRAWLISTAN Discord">Claimed</span>'
        : '<span class="pill pill-muted">Unclaimed</span>';
    const s = profile.pakistan_season;

    el.innerHTML = `
      <section class="panel profile-head" aria-label="Player">
        ${avatarHtml(profile.player_name, 72)}
        <div>
          <h1>${escapeHtml(profile.player_name)}</h1>
          <div class="profile-meta">
            <span>${country}</span><span aria-hidden="true">·</span>
            <span>Brawlhalla ID ${escapeHtml(String(profile.brawlhalla_id))}</span>
            ${profile.region ? `<span aria-hidden="true">·</span><span>${escapeHtml(profile.region)}</span>` : ""}
          </div>
          <div class="profile-meta">
            ${teamPillHtml(entry.team, entry.team_slug)}
            ${claimText}
            ${(profile.playstyle_tags || []).map((t) => `<span class="pill">${escapeHtml(t)}</span>`).join("")}
          </div>
        </div>
        <div class="profile-actions">
          <button type="button" class="btn btn-ghost btn-sm" id="compare-btn" aria-expanded="false" aria-controls="compare">Compare</button>
          <button type="button" class="btn btn-ghost btn-sm" id="share-btn">Share</button>
          <a class="btn btn-primary btn-sm" data-discord-invite href="${typeof DISCORD_INVITE_URL !== "undefined" ? DISCORD_INVITE_URL : "join.html"}" target="_blank" rel="noopener">Discord</a>
        </div>
      </section>

      <div class="stat-tiles">
        ${tile("Pakistan rank", rankIndex >= 0 ? `#${rankIndex + 1}` : "—", rankIndex >= 0 ? `of ${rated.length}` : "Not on the board")}
        ${tile("Global rank", profile.global_rank ? `#${formatNumber(profile.global_rank)}` : "—", profile.region_rank ? `#${formatNumber(profile.region_rank)} in ${escapeHtml(profile.region || "region")}` : "")}
        ${tile("Rating", formatNumber(profile.rating), trendText(rankRow.trend))}
        ${tile("Peak", formatNumber(profile.peak_rating), s ? `Season ${s.number} · ${escapeHtml(s.name)}` : "")}
        ${tile("Tier", profile.tier ? escapeHtml(profile.tier) : "Unranked", rankRow.rating_2v2 ? `2v2: ${formatNumber(rankRow.rating_2v2)}` : "")}
      </div>

      ${compareHtml({ brawlhalla_id: brawlhallaId }, directory || [])}

      <div class="home-grid" style="margin-top:16px">
        <section class="panel panel-pad span-8" aria-labelledby="h-history">
          <div class="section-head"><h2 id="h-history">Rating history</h2><span class="muted" style="font-size:12.5px">Dashed: peak</span></div>
          ${history && history.some((h) => h.rating != null) ? '<div class="chart-box"><canvas id="history-chart" aria-label="Rating over time" role="img"></canvas></div>' : UNAVAILABLE}
        </section>
        <section class="panel panel-pad span-4" aria-labelledby="h-main">
          <div class="section-head"><h2 id="h-main">Main legends</h2></div>
          ${mainLegendsHtml(legends)}
        </section>
        <section class="panel panel-pad span-6" aria-labelledby="h-seasons">
          <div class="section-head"><h2 id="h-seasons">Season history</h2></div>
          ${seasonsHtml(seasons)}
        </section>
        <section class="panel panel-pad span-6" aria-labelledby="h-matches">
          <div class="section-head"><h2 id="h-matches">Tournaments and matches</h2></div>
          ${matchesHtml(matches)}
        </section>
        <section class="panel panel-pad span-12" aria-labelledby="h-legends">
          <div class="section-head"><h2 id="h-legends">Legend statistics</h2></div>
          ${legendTableHtml(legends)}
        </section>
        <section class="panel panel-pad span-12" aria-labelledby="h-ach">
          <div class="section-head"><h2 id="h-ach">Achievements</h2></div>
          ${achievementsHtml(checklist, profile.achievements)}
        </section>
        <section class="panel panel-pad span-12" aria-labelledby="h-discord">
          <div class="section-head"><h2 id="h-discord">Discord</h2></div>
          ${entry.is_claimed ? claimedHtml(entry) : claimFormHtml()}
        </section>
      </div>`;

    wireClaimForm(profile);

    if (history && history.length) {
      drawSparkline(document.getElementById("history-chart"), [...history].reverse());
    }

    // Compare: side by side from the same cached rankings/directory data.
    const compareBtn = document.getElementById("compare-btn");
    compareBtn.addEventListener("click", () => {
      const panel = document.getElementById("compare");
      panel.hidden = !panel.hidden;
      compareBtn.setAttribute("aria-expanded", panel.hidden ? "false" : "true");
      if (!panel.hidden) document.getElementById("compare-with").focus();
    });
    const lookup = (id) => {
      const row = ((rankings && rankings.rows) || []).find((r) => String(r.brawlhalla_id) === String(id));
      const dir = (directory || []).find((p) => String(p.brawlhalla_id) === String(id)) || {};
      return { ...dir, ...(row || {}), player_name: (row || dir).player_name };
    };
    document.getElementById("compare-with").addEventListener("change", (event) => {
      if (!event.target.value) {
        document.getElementById("compare-body").innerHTML = "";
        return;
      }
      const me = lookup(brawlhallaId);
      renderCompare({ ...me, player_name: profile.player_name, rating: profile.rating, peak_rating: profile.peak_rating, tier: profile.tier, global_rank: profile.global_rank }, lookup(event.target.value));
    });

    // Share: the generated per-player page carries this player's own title
    // and preview card (ADR-106).
    document.getElementById("share-btn").addEventListener("click", async (event) => {
      const url = new URL(`player/${slug}/`, document.baseURI).href;
      const title = document.title;
      try {
        if (navigator.share) {
          await navigator.share({ title, url });
          return;
        }
        await navigator.clipboard.writeText(url);
        event.target.textContent = "Link copied";
      } catch {
        /* share sheet dismissed or clipboard blocked: nothing to do */
      }
    });
  }

  load().catch(() => {
    el.innerHTML = UNAVAILABLE;
  });
})();
