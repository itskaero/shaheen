(async function () {
  const el = document.getElementById("clan-content");

  try {
    const clan = await ShaheenAPI.getClan();
    el.innerHTML = `
      <div class="card">
        <p class="motto" style="text-align: center">${clan.motto}</p>
        <p class="tagline" style="text-align: center">${clan.tagline}</p>
      </div>
      <div class="stat-grid">
        <div class="stat">
          <span class="value">${formatNumber(clan.member_count)}</span>
          <span class="label">Linked Members</span>
        </div>
      </div>
    `;
  } catch (err) {
    el.innerHTML = `<p class="state-msg error">Couldn't load clan info: ${err.message}</p>`;
  }
})();
