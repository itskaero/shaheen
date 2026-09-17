(async function () {
  const el = document.getElementById("clan-content");

  try {
    const clan = await ShaheenAPI.getClan();

    // Linked Members always shows; the two Discord-sourced tiles are
    // guild-wide numbers captured by the bot's snapshot tick (never
    // per-member identity — docs/DECISIONS.md) and only render once a
    // snapshot actually exists, so a fresh deploy degrades to just the
    // one tile instead of showing "0"/misleading placeholders.
    const statTiles = [
      `<div class="stat"><span class="value">${formatNumber(clan.member_count)}</span><span class="label">Linked Members</span></div>`,
    ];
    if (clan.discord_member_count != null) {
      statTiles.push(
        `<div class="stat"><span class="value">${formatNumber(clan.discord_member_count)}</span><span class="label">Discord Members</span></div>`
      );
    }
    if (clan.discord_boost_tier) {
      statTiles.push(
        `<div class="stat"><span class="value">Level ${clan.discord_boost_tier}</span><span class="label">Server Boost</span></div>`
      );
    }

    const inviteLink =
      typeof DISCORD_INVITE_URL !== "undefined" && DISCORD_INVITE_URL
        ? `<a class="btn" href="${DISCORD_INVITE_URL}" target="_blank" rel="noopener">Join Discord</a>`
        : "";

    el.innerHTML = `
      <div class="card clan-reveal">
        <p class="motto motto-centered">${clan.motto}</p>
        <p class="tagline tagline-centered">${clan.tagline}</p>
      </div>
      <div class="stat-grid">${statTiles.join("")}</div>
      <div class="divider"><span>Community Activity</span></div>
      <div id="community-activity">
        <p class="state-msg">Loading community activity…</p>
      </div>
      <div class="divider"><span>Join the Community</span></div>
      <div class="community-cta">
        ${inviteLink}
        <span class="discord-widget" data-discord-widget hidden></span>
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

    // The content-area widget badge above didn't exist yet when api.js's
    // own DOMContentLoaded handler first ran wireDiscordWidgets() (this
    // card renders later, once the fetch resolves) — re-run it now so
    // that badge gets the same best-effort fill as the header/footer ones
    // (harmless no-op if DISCORD_GUILD_ID isn't set).
    if (typeof wireDiscordWidgets === "function") {
      wireDiscordWidgets();
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
