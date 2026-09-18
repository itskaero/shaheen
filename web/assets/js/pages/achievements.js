(async function () {
  const el = document.getElementById("achievements-content");

  try {
    const entries = await ShaheenAPI.getAchievements();

    if (!entries || entries.length === 0) {
      el.innerHTML = '<p class="state-msg">No achievements defined yet.</p>';
      return;
    }

    const cards = entries
      .map((entry) => {
        const unearned = entry.holder_count === 0;
        const pct = Math.round(entry.completion_pct);
        // Banded server-side (services/achievements.py) so Discord and the
        // site can't disagree on what counts as rare.
        const rarity = entry.rarity || "";
        const rarityClass = rarity ? ` rarity-${rarity.toLowerCase()}` : "";
        return `
        <div class="card achievement-card${unearned ? " unearned" : ""}">
          <span class="badge-icon achievement-icon">🏅</span>
          ${rarity ? `<span class="achievement-rarity${rarityClass}">${escapeHtml(rarity)}</span>` : ""}
          <h3>${escapeHtml(entry.name)}</h3>
          <p>${escapeHtml(entry.description)}</p>
          <div class="achievement-progress">
            <div class="legend-bar-track"><div class="legend-bar-fill" style="width: ${Math.max(pct, entry.holder_count > 0 ? 4 : 0)}%"></div></div>
            <span class="legend-meta">${entry.holder_count}/${entry.total_members} member(s) &middot; ${pct}%</span>
          </div>
        </div>`;
      })
      .join("");

    el.innerHTML = `<div class="achievement-grid">${cards}</div>`;
  } catch (err) {
    el.innerHTML = `<p class="state-msg error">Couldn't load achievements: ${err.message}</p>`;
  }
})();
