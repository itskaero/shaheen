(async function () {
  const el = document.getElementById("leaderboard-content");

  try {
    const entries = await ShaheenAPI.getLeaderboard(25);

    if (!entries || entries.length === 0) {
      el.innerHTML = '<p class="state-msg">No ranked players yet — link a Brawlhalla account with /link in Discord.</p>';
      return;
    }

    const rows = entries
      .map(
        (entry, i) => `
        <tr>
          <td class="rank">#${i + 1}</td>
          <td><a href="player.html?id=${entry.brawlhalla_id}">${escapeHtml(entry.player_name)}</a></td>
          <td>${entry.region ? escapeHtml(entry.region) : "—"}</td>
          <td>${formatTier(entry.tier)}</td>
          <td>${formatNumber(entry.rating)}</td>
          <td>${formatNumber(entry.peak_rating)}</td>
        </tr>`
      )
      .join("");

    el.innerHTML = `
      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>Player</th>
              <th>Region</th>
              <th>Tier</th>
              <th>Rating</th>
              <th>Peak</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    `;
  } catch (err) {
    el.innerHTML = `<p class="state-msg error">Couldn't load the leaderboard: ${err.message}</p>`;
  }
})();
