(async function () {
  const el = document.getElementById("clan-content");

  try {
    const clan = await ShaheenAPI.getClan();
    el.innerHTML = `
      <div class="card">
        <p class="motto" style="text-align: center">${clan.motto}</p>
        <p class="tagline" style="text-align: center; margin: 0">${clan.tagline}</p>
      </div>
      <div class="stat-grid">
        <div class="stat">
          <span class="value">${formatNumber(clan.member_count)}</span>
          <span class="label">Linked Members</span>
        </div>
      </div>
      <div class="divider"><span>Community Activity</span></div>
      <div id="community-activity">
        <p class="state-msg">Loading community activity…</p>
      </div>
      <div class="divider"><span>Explore</span></div>
      <div class="stat-grid">
        <a class="stat" href="leaderboard.html" style="text-decoration: none">
          <span class="value">🏆</span><span class="label">Leaderboard</span>
        </a>
        <a class="stat" href="player.html" style="text-decoration: none">
          <span class="value">📈</span><span class="label">Player Profiles</span>
        </a>
        <a class="stat" href="tournaments.html" style="text-decoration: none">
          <span class="value">🥇</span><span class="label">Tournaments</span>
        </a>
      </div>
    `;
  } catch (err) {
    el.innerHTML = `<p class="state-msg error">Couldn't load clan info: ${err.message}</p>`;
    return;
  }

  // A separate fetch/try so a community-activity failure can't take down
  // the clan info + explore links above, which already rendered fine.
  const activityEl = document.getElementById("community-activity");
  try {
    const entries = await ShaheenAPI.getCommunityActivity(10);

    if (!entries || entries.length === 0) {
      activityEl.innerHTML =
        '<p class="state-msg">No chat activity yet — link your account with /link and start chatting in Discord!</p>';
      return;
    }

    const rows = entries
      .map(
        (entry, i) => `
        <tr>
          <td>${rankHtml(i + 1)}</td>
          <td>${escapeHtml(entry.player_name)}</td>
          <td>${escapeHtml(entry.rank_title)}</td>
          <td>${formatNumber(entry.level)}</td>
          <td>${formatNumber(entry.xp)}</td>
        </tr>`
      )
      .join("");

    activityEl.innerHTML = `
      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Rank</th>
              <th>Player</th>
              <th>Title</th>
              <th>Level</th>
              <th>XP</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    `;
  } catch (err) {
    activityEl.innerHTML = `<p class="state-msg error">Couldn't load community activity: ${err.message}</p>`;
  }
})();
