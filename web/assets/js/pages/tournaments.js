(async function () {
  const el = document.getElementById("tournaments-content");

  try {
    const tournaments = await ShaheenAPI.getTournaments();

    if (!tournaments || tournaments.length === 0) {
      el.innerHTML = '<p class="state-msg">No tournaments yet — staff can start one with /tournament create in Discord.</p>';
      return;
    }

    el.innerHTML = `
      <ul class="tournament-list">
        ${tournaments
          .map(
            (t) => `
              <li>
                <a class="card tournament-card" href="tournament.html?id=${t.id}" style="text-decoration: none;">
                  <div>
                    <h3>${escapeHtml(t.name)}</h3>
                    <p class="meta">${escapeHtml(t.kind)}${t.started_at ? ` · started ${formatDate(t.started_at)}` : ""}</p>
                  </div>
                  ${statusBadge(t.status)}
                </a>
              </li>`
          )
          .join("")}
      </ul>
    `;
  } catch (err) {
    el.innerHTML = `<p class="state-msg error">Couldn't load tournaments: ${err.message}</p>`;
  }
})();

function statusBadge(status) {
  const labels = {
    registration: "Registration",
    in_progress: "In Progress",
    completed: "Completed",
    cancelled: "Cancelled",
  };
  return `<span class="status-badge status-${escapeHtml(status)}">${labels[status] || escapeHtml(status)}</span>`;
}
