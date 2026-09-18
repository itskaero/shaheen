(function () {
  const content = document.getElementById("player-content");
  const form = document.getElementById("search-form");
  const input = document.getElementById("player-id-input");

  const params = new URLSearchParams(window.location.search);
  const initialId = params.get("id");
  if (initialId) {
    input.value = initialId;
    loadPlayer(initialId);
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const id = input.value.trim();
    if (!id) {
      return;
    }
    const url = new URL(window.location);
    url.searchParams.set("id", id);
    window.history.pushState({}, "", url);
    loadPlayer(id);
  });

  async function loadPlayer(brawlhallaId) {
    content.innerHTML = '<p class="state-msg">Loading player… (first load can take up to a minute)</p>';

    try {
      const [profile, history, legends, matches, checklist] = await Promise.all([
        ShaheenAPI.getPlayer(brawlhallaId),
        ShaheenAPI.getPlayerHistory(brawlhallaId, 20),
        ShaheenAPI.getPlayerLegends(brawlhallaId),
        ShaheenAPI.getPlayerMatches(brawlhallaId),
        // Added after the other four endpoints, so an API instance that
        // predates it must not take the whole page down — fall back to the
        // earned-only list carried on the profile itself.
        ShaheenAPI.getPlayerAchievements(brawlhallaId).catch(() => null),
      ]);

      if (!profile) {
        content.innerHTML = `<p class="state-msg error">No player found with Brawlhalla ID ${escapeHtml(brawlhallaId)}.</p>`;
        return;
      }

      const achievements = checklist
        ? achievementChecklistHtml(checklist)
        : earnedOnlyHtml(profile.achievements);

      content.innerHTML = `
        <div class="card">
          <div class="profile-head">
            ${avatarHtml(profile.player_name, 64)}
            <div>
              <h2>${escapeHtml(profile.player_name)}</h2>
              <p class="page-subtitle" style="margin: 0.25rem 0 0;">
                ${profile.region ? escapeHtml(profile.region) : "Region unknown"} · Brawlhalla ID ${profile.brawlhalla_id}
              </p>
            </div>
          </div>
        </div>

        <div class="stat-grid">
          <div class="stat">
            <span style="display: block; margin-bottom: 0.35rem;">${tierBadge(profile.tier)}</span>
            <span class="label">Tier</span>
          </div>
          <div class="stat"><span class="value">${formatNumber(profile.rating)}</span><span class="label">Rating</span></div>
          <div class="stat"><span class="value">${formatNumber(profile.peak_rating)}</span><span class="label">Peak Rating</span></div>
          ${
            profile.global_rank
              ? `<div class="stat"><span class="value">#${formatNumber(profile.global_rank)}</span><span class="label">Global Rank</span></div>`
              : ""
          }
        </div>

        <div class="card">
          <h3 style="margin-top: 0">Rating History</h3>
          <canvas id="history-chart"></canvas>
        </div>

        <div class="card">
          <h3 style="margin-top: 0">Legend Mastery</h3>
          ${legendMasteryHtml(legends)}
        </div>

        <div class="card">
          <h3 style="margin-top: 0">Match History</h3>
          ${matchHistoryHtml(matches)}
        </div>

        <div class="card">
          <h3 style="margin-top: 0">Achievements</h3>
          ${achievements}
        </div>
      `;

      if (history && history.length > 0) {
        const chronological = [...history].reverse();
        drawSparkline(document.getElementById("history-chart"), chronological);
      }
    } catch (err) {
      content.innerHTML = `<p class="state-msg error">Couldn't load this player: ${err.message}</p>`;
    }
  }


  const CATEGORY_LABELS = {
    onboarding: "Getting Started",
    milestone: "Milestones",
    ranked: "Ranked",
    competition: "Competition",
    community: "Community",
    tenure: "Tenure",
  };

  function earnedOnlyHtml(earned) {
    if (!earned || earned.length === 0) {
      return '<p class="state-msg">No achievements yet.</p>';
    }
    return `<ul class="badge-list">${earned
      .map(
        (a) =>
          `<li><span class="badge-icon">🏅</span><span><strong>${escapeHtml(a.name)}</strong> — ${escapeHtml(a.description)}</span></li>`
      )
      .join("")}</ul>`;
  }

  // The clan-wide gallery on achievements.html looks identical for every
  // member by design. This is the per-member view: the same catalog, with
  // what this player has and hasn't earned.
  function achievementChecklistHtml(entries) {
    if (!entries || entries.length === 0) {
      return '<p class="state-msg">No achievements defined yet.</p>';
    }

    const earnedCount = entries.filter((entry) => entry.earned).length;
    const pct = Math.round((earnedCount / entries.length) * 100);

    const groups = new Map();
    entries.forEach((entry) => {
      const key = entry.category || "milestone";
      if (!groups.has(key)) {
        groups.set(key, []);
      }
      groups.get(key).push(entry);
    });

    const sections = [...groups.entries()]
      .map(([category, items]) => {
        const rows = items
          .map(
            (entry) => `
              <li class="${entry.earned ? "achievement-earned" : "achievement-locked"}">
                <span class="badge-icon">${entry.earned ? "🏅" : "🔒"}</span>
                <span>
                  <strong>${escapeHtml(entry.name)}</strong> — ${escapeHtml(entry.description)}
                  ${entry.earned && entry.awarded_at ? `<span class="legend-meta"> · ${formatDate(entry.awarded_at)}</span>` : ""}
                </span>
              </li>`
          )
          .join("");
        return `
          <div class="achievement-group">
            <h4>${escapeHtml(CATEGORY_LABELS[category] || category)}</h4>
            <ul class="badge-list">${rows}</ul>
          </div>`;
      })
      .join("");

    return `
      <div class="achievement-progress">
        <div class="legend-bar-track"><div class="legend-bar-fill" style="width: ${Math.max(pct, earnedCount > 0 ? 4 : 0)}%"></div></div>
        <span class="legend-meta">${earnedCount} of ${entries.length} earned · ${pct}%</span>
      </div>
      ${sections}
    `;
  }

  function legendMasteryHtml(legends) {
    if (!legends || legends.length === 0) {
      return '<p class="state-msg">No legend stats yet — plays will show up after the next snapshot.</p>';
    }
    const maxGames = Math.max(...legends.map((l) => l.games), 1);
    return `
      <ul class="legend-list">
        ${legends
          .map((legend) => {
            const winRate = legend.games > 0 ? Math.round((legend.wins / legend.games) * 100) : 0;
            const width = Math.max(6, Math.round((legend.games / maxGames) * 100));
            return `
              <li>
                <div class="legend-row">
                  <span class="legend-name">${escapeHtml(legendDisplayName(legend.legend_name_key))}</span>
                  <span class="legend-meta">${legend.games} games · ${winRate}% WR · ${legend.kos} KOs · ${formatNumber(legend.damagedealt)} DMG · ${legend.falls} falls</span>
                </div>
                <div class="legend-bar-track"><div class="legend-bar-fill" style="width: ${width}%"></div></div>
              </li>`;
          })
          .join("")}
      </ul>
    `;
  }

  function matchHistoryHtml(matches) {
    if (!matches || matches.length === 0) {
      return '<p class="state-msg">No confirmed matches yet.</p>';
    }
    return `
      <ul class="match-list">
        ${matches
          .map(
            (m) => `
              <li class="${m.won ? "match-win" : "match-loss"}">
                <span class="match-result">${m.won ? "WIN" : "LOSS"}</span>
                <span class="match-kind">${escapeHtml(m.kind)}</span>
                <span class="match-opponents">vs ${m.opponents.length ? escapeHtml(m.opponents.join(" & ")) : "Unknown"}</span>
                <span class="match-date">${formatDate(m.confirmed_at)}</span>
              </li>`
          )
          .join("")}
      </ul>
    `;
  }
})();
