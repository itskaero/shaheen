(async function () {
  const el = document.getElementById("clan-content");

  try {
    const clan = await ShaheenAPI.getClan();
    el.innerHTML = `
      <div class="card clan-reveal">
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

    // The clan-reveal wipe (style.css's .clan-reveal.in-view) is normally
    // triggered by scroll.js's IntersectionObserver, but this card is
    // injected into the DOM well after DOMContentLoaded (once the fetch
    // resolves) so that observer never sees it — and it's the very first
    // thing on the page anyway, so a scroll trigger isn't the right fit
    // here. Two rAFs so the browser paints the closed clip-path first,
    // then the transition to .in-view actually animates instead of
    // snapping straight to its end state in the same frame.
    const revealCard = el.querySelector(".clan-reveal");
    if (revealCard) {
      requestAnimationFrame(() => requestAnimationFrame(() => revealCard.classList.add("in-view")));
    }
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
      .map((entry, i) => {
        const currentThreshold = xpForLevel(entry.level);
        const nextThreshold = xpForLevel(entry.level + 1);
        const span = Math.max(1, nextThreshold - currentThreshold);
        const progressPct = Math.min(100, Math.max(4, Math.round(((entry.xp - currentThreshold) / span) * 100)));
        return `
        <li class="chat-activity-row">
          ${rankHtml(i + 1)}
          <span class="chat-activity-name">${escapeHtml(entry.player_name)}</span>
          ${chatRankBadge(entry.rank_title)}
          <div class="chat-activity-progress">
            <div class="legend-bar-track"><div class="legend-bar-fill" style="width: ${progressPct}%"></div></div>
            <span class="legend-meta">Level ${formatNumber(entry.level)} &middot; ${formatNumber(entry.xp)} XP</span>
          </div>
        </li>`;
      })
      .join("");

    activityEl.innerHTML = `<ul class="chat-activity-list">${rows}</ul>`;
  } catch (err) {
    activityEl.innerHTML = `<p class="state-msg error">Couldn't load community activity: ${err.message}</p>`;
  }
})();
