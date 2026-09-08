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
    content.innerHTML = '<p class="state-msg">Loading player…</p>';

    try {
      const [profile, history] = await Promise.all([
        ShaheenAPI.getPlayer(brawlhallaId),
        ShaheenAPI.getPlayerHistory(brawlhallaId, 20),
      ]);

      if (!profile) {
        content.innerHTML = `<p class="state-msg error">No player found with Brawlhalla ID ${escapeHtml(brawlhallaId)}.</p>`;
        return;
      }

      const achievements = profile.achievements.length
        ? `<ul class="badge-list">${profile.achievements
            .map(
              (a) =>
                `<li><span class="badge-icon">🏅</span><span><strong>${escapeHtml(a.name)}</strong> — ${escapeHtml(a.description)}</span></li>`
            )
            .join("")}</ul>`
        : '<p class="state-msg">No achievements yet.</p>';

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
        </div>

        <div class="card">
          <h3 style="margin-top: 0">Rating History</h3>
          <canvas id="history-chart"></canvas>
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
})();
