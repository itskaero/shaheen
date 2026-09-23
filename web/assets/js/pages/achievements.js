(function () {
  const el = document.getElementById("achievements-content");

  const CATEGORY_LABELS = {
    onboarding: "Getting Started",
    milestone: "Milestones",
    ranked: "Ranked",
    competition: "Competition",
    community: "Community",
    tenure: "Tenure",
  };
  const HOLDERS_SHOWN = 6;

  // Who earned it, earliest first (docs/DECISIONS.md ADR-100) — Brawlhalla
  // names only, each linking to that player's profile.
  function holdersHtml(entry) {
    const holders = entry.holders || [];
    if (holders.length === 0) {
      return '<p class="achievement-first">Nobody yet — be the first.</p>';
    }
    const first = holders[0];
    const chips = holders
      .slice(0, HOLDERS_SHOWN)
      .map(
        (h) => `
          <a class="holder-chip" href="player.html?id=${h.brawlhalla_id}" title="Earned ${formatDate(h.earned_at)}">
            ${avatarHtml(h.player_name, 22)}<span>${escapeHtml(h.player_name)}</span>
          </a>`
      )
      .join("");
    const more =
      holders.length > HOLDERS_SHOWN
        ? `<span class="holder-more">+${holders.length - HOLDERS_SHOWN} more</span>`
        : "";
    return `
      <p class="achievement-first">First: <a href="player.html?id=${first.brawlhalla_id}">${escapeHtml(first.player_name)}</a> &middot; ${formatDate(first.earned_at)}</p>
      <div class="holder-list">${chips}${more}</div>`;
  }

  function cardHtml(entry) {
    const unearned = entry.holder_count === 0;
    const pct = Math.round(entry.completion_pct);
    // Banded server-side (services/achievements.py) so Discord and the
    // site can't disagree on what counts as rare.
    const rarity = entry.rarity || "";
    const rarityClass = rarity ? ` rarity-${rarity.toLowerCase()}` : "";
    return `
      <div class="card achievement-card${unearned ? " unearned" : ""}">
        <div class="achievement-head">
          <span class="badge-icon achievement-icon">🏅</span>
          ${rarity ? `<span class="achievement-rarity${rarityClass}">${escapeHtml(rarity)}</span>` : ""}
        </div>
        <h3>${escapeHtml(entry.name)}</h3>
        <p>${escapeHtml(entry.description)}</p>
        <div class="achievement-progress">
          <div class="legend-bar-track"><div class="legend-bar-fill" style="width: ${Math.max(pct, entry.holder_count > 0 ? 4 : 0)}%"></div></div>
          <span class="legend-meta">${entry.holder_count}/${entry.total_members} member(s) &middot; ${pct}%</span>
        </div>
        ${holdersHtml(entry)}
      </div>`;
  }

  function render(entries, meta) {
    if (!entries || entries.length === 0) {
      el.innerHTML = '<p class="state-msg">No achievements defined yet.</p>';
      return;
    }

    const byCategory = new Map();
    entries.forEach((entry) => {
      if (!byCategory.has(entry.category)) byCategory.set(entry.category, []);
      byCategory.get(entry.category).push(entry);
    });

    const earnedTotal = entries.filter((e) => e.holder_count > 0).length;
    el.innerHTML = `
      <p class="achievement-summary">${earnedTotal} of ${entries.length} achievements unlocked by at least one member.</p>
      ${[...byCategory.entries()]
        .map(([category, items]) => {
          const unlocked = items.filter((e) => e.holder_count > 0).length;
          return `
            <section class="achievement-section">
              <h2 class="board-subhead">${escapeHtml(CATEGORY_LABELS[category] || category)} <span>${unlocked}/${items.length} unlocked</span></h2>
              <div class="achievement-grid">${items.map(cardHtml).join("")}</div>
            </section>`;
        })
        .join("")}`;
    if (meta && !meta.live && meta.capturedAt) {
      el.insertAdjacentHTML(
        "beforeend",
        `<p class="snapshot-note">Showing the last saved copy from ${formatDate(meta.capturedAt)} — refreshing…</p>`
      );
    }
  }

  ShaheenAPI.withSnapshot("achievements", () => ShaheenAPI.getAchievements(), render).catch((err) => {
    el.innerHTML = `<p class="state-msg error">Couldn't load achievements: ${escapeHtml(err.message)}</p>`;
  });
})();
