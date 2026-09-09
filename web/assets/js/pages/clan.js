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
  }
})();
