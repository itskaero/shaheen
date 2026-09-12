(async function () {
  const el = document.getElementById("roster-content");

  try {
    const entries = await ShaheenAPI.getRoster();

    if (!entries || entries.length === 0) {
      el.innerHTML = '<p class="state-msg">No linked members yet — link a Brawlhalla account with /link in Discord.</p>';
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
          <td>${entry.tier ? tierBadge(entry.tier) : "—"}</td>
          <td>${formatNumber(entry.rating)}</td>
          <td>${formatNumber(entry.peak_rating)}</td>
          <td>${entry.member_since ? formatDate(entry.member_since) : "—"}</td>
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
              <th>Member Since</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    `;
  } catch (err) {
    el.innerHTML = `<p class="state-msg error">Couldn't load the roster: ${err.message}</p>`;
  }
})();
