(function () {
  const el = document.getElementById("leaderboard-content");

  function render(entries, meta) {

    if (!entries || entries.length === 0) {
      el.innerHTML = '<p class="state-msg">No ranked players yet — link a Brawlhalla account with /link in Discord.</p>';
      return;
    }

    const rows = entries
      .map(
        (entry, i) => `
        <tr>
          <td>${rankHtml(i + 1)}</td>
          <td>
            <a class="player-cell" href="player.html?id=${entry.brawlhalla_id}">
              ${avatarHtml(entry.player_name, 36)}
              <span>${escapeHtml(entry.player_name)}</span>
            </a>
          </td>
          <td>${entry.region ? escapeHtml(entry.region) : "—"}</td>
          <td>${tierBadge(entry.tier)}</td>
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
              <th>Rank</th>
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
    if (meta && !meta.live && meta.capturedAt) {
      el.insertAdjacentHTML(
        "beforeend",
        `<p class="snapshot-note">Showing the last saved copy from ${formatDate(meta.capturedAt)} — refreshing…</p>`
      );
    }
  }

  ShaheenAPI.withSnapshot("leaderboard", () => ShaheenAPI.getLeaderboard(25), render).catch((err) => {
    el.innerHTML = `<p class="state-msg error">Couldn't load the leaderboard: ${err.message}</p>`;
  });
})();
