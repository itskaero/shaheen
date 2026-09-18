(function () {
  const el = document.getElementById("roster-content");

  function render(entries, meta) {

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
    if (meta && !meta.live && meta.capturedAt) {
      el.insertAdjacentHTML(
        "beforeend",
        `<p class="snapshot-note">Showing the last saved copy from ${formatDate(meta.capturedAt)} — refreshing…</p>`
      );
    }
  }

  ShaheenAPI.withSnapshot("roster", () => ShaheenAPI.getRoster(), render).catch((err) => {
    el.innerHTML = `<p class="state-msg error">Couldn't load the roster: ${err.message}</p>`;
  });
})();
