(async function () {
  const el = document.getElementById("clan-content");

  // The page skeleton is rendered up front, before any fetch, so the parts
  // that need no API — the Discord invite and the live badge — appear
  // immediately and survive an API failure (ADR-082). Previously all of
  // this lived inside the getClan() try, so a cold Render instance (up to
  // a 50s spin-up) or any API error took the whole "Join the Community"
  // strip down with it, badge included.
  const inviteLink =
    typeof DISCORD_INVITE_URL !== "undefined" && DISCORD_INVITE_URL
      ? `<a class="btn" href="${DISCORD_INVITE_URL}" target="_blank" rel="noopener">Join Discord</a>`
      : "";

  el.innerHTML = `
    <div id="clan-info">
      <p class="state-msg">Loading clan info… (first load can take up to a minute)</p>
    </div>
    <div class="divider"><span>Recent Matches</span></div>
    <div id="clan-matches">
      <p class="state-msg">Loading recent matches…</p>
    </div>
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

  // This third badge didn't exist when api.js's own DOMContentLoaded
  // handler ran wireDiscordWidgets() — re-run it now that its target is in
  // the DOM (harmless no-op if DISCORD_GUILD_ID isn't set).
  if (typeof wireDiscordWidgets === "function") {
    wireDiscordWidgets();
  }

  const infoEl = document.getElementById("clan-info");

  // Snapshot-first (docs/DECISIONS.md ADR-087): web/data/clan.json ships
  // with the site, so this renders instantly instead of waiting out a
  // Render cold start, then re-renders from the live API.
  function renderClan(clan, meta) {
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
    if (clan.season != null) {
      statTiles.push(
        `<div class="stat"><span class="value">${clan.season}</span><span class="label">Brawlhalla Season</span></div>`
      );
    }
    if (clan.discord_boost_tier) {
      statTiles.push(
        `<div class="stat"><span class="value">Level ${clan.discord_boost_tier}</span><span class="label">Server Boost</span></div>`
      );
    }

    infoEl.innerHTML = `
      <div class="card clan-reveal">
        <p class="motto motto-centered">${clan.motto}</p>
        <p class="tagline tagline-centered">${clan.tagline}</p>
      </div>
      <div class="stat-grid">${statTiles.join("")}</div>
    `;

    // The clan-reveal wipe (style.css's .clan-reveal.in-view) is normally
    // triggered by scroll.js's IntersectionObserver, but this card is
    // injected into the DOM well after DOMContentLoaded (once the fetch
    // resolves) so that observer never sees it. Two rAFs so the browser
    // paints the closed clip-path first, then the transition to .in-view
    // actually animates instead of snapping to its end state in one frame.
    const revealCard = infoEl.querySelector(".clan-reveal");
    if (revealCard) {
      requestAnimationFrame(() => requestAnimationFrame(() => revealCard.classList.add("in-view")));
    }

    if (meta && !meta.live && meta.capturedAt) {
      infoEl.insertAdjacentHTML(
        "beforeend",
        `<p class="snapshot-note">Showing the last saved copy from ${formatDate(meta.capturedAt)} — refreshing…</p>`
      );
    }
  }

  try {
    await ShaheenAPI.withSnapshot("clan", () => ShaheenAPI.getClan(), renderClan);
  } catch (err) {
    infoEl.innerHTML = `<p class="state-msg error">Couldn't load clan info: ${err.message}</p>`;
  }

  // Recent confirmed clan matches (docs/DECISIONS.md ADR-088). The whole
  // competition subsystem — challenges, scrims, matches — has run since
  // Phase 4 with no public surface; this is the first one. Its own try, so
  // it can't take down the clan info above.
  const matchesEl = document.getElementById("clan-matches");
  try {
    const matches = await ShaheenAPI.getClanMatches(8);
    if (!matches || matches.length === 0) {
      matchesEl.innerHTML =
        '<p class="state-msg">No confirmed matches yet — settle one with /challenge in Discord.</p>';
    } else {
      matchesEl.innerHTML = `
        <ul class="match-list">
          ${matches
            .map(
              (m) => `
            <li class="match-win">
              <span class="match-result">${escapeHtml(m.kind.toUpperCase())}</span>
              <span class="match-opponents">
                <strong>${m.winners.length ? escapeHtml(m.winners.join(" & ")) : "Unknown"}</strong>
                beat ${m.losers.length ? escapeHtml(m.losers.join(" & ")) : "Unknown"}
              </span>
              <span class="match-date">${formatDate(m.confirmed_at)}</span>
            </li>`
            )
            .join("")}
        </ul>`;
    }
  } catch (err) {
    matchesEl.innerHTML = `<p class="state-msg error">Couldn't load recent matches: ${err.message}</p>`;
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
