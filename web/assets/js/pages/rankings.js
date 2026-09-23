// Rankings: the clan ladder and the Pakistan ladder on one page
// (docs/DECISIONS.md ADR-099). The clan tab is built from /roster — already
// every linked member, rating-sorted, unplaced members included — so the old
// separate Leaderboard and Roster pages become one list.
(function () {
  const TABS = {
    clan: { tab: "tab-clan", panel: "panel-clan" },
    pakistan: { tab: "tab-pakistan", panel: "panel-pakistan" },
  };

  function selectTab(name, { focus = false, updateHash = true } = {}) {
    Object.entries(TABS).forEach(([key, ids]) => {
      const tab = document.getElementById(ids.tab);
      const panel = document.getElementById(ids.panel);
      const active = key === name;
      tab.setAttribute("aria-selected", active ? "true" : "false");
      tab.tabIndex = active ? 0 : -1;
      panel.hidden = !active;
      if (active && focus) tab.focus();
    });
    if (updateHash) {
      history.replaceState(null, "", name === "clan" ? location.pathname : `#${name}`);
    }
  }

  function tabFromHash() {
    return location.hash === "#pakistan" ? "pakistan" : "clan";
  }

  Object.entries(TABS).forEach(([key, ids]) => {
    const tab = document.getElementById(ids.tab);
    tab.addEventListener("click", () => selectTab(key));
    tab.addEventListener("keydown", (event) => {
      if (event.key === "ArrowRight" || event.key === "ArrowLeft") {
        event.preventDefault();
        selectTab(key === "clan" ? "pakistan" : "clan", { focus: true });
      }
    });
  });
  window.addEventListener("hashchange", () => selectTab(tabFromHash(), { updateHash: false }));
  selectTab(tabFromHash(), { updateHash: false });

  function playerCell(entry, size = 36) {
    return `
      <a class="player-cell" href="player.html?id=${entry.brawlhalla_id}">
        ${avatarHtml(entry.player_name, size)}
        <span>${escapeHtml(entry.player_name)}</span>
        ${entry.is_clan_member ? '<span class="clan-tag">Shaheen</span>' : ""}
      </a>`;
  }

  function podiumHtml(ranked) {
    if (ranked.length < 3) return "";
    // visual order 2 · 1 · 3, so the winner stands in the middle
    const order = [1, 0, 2];
    return `
      <ol class="podium" aria-label="Top three">
        ${order
          .map((index) => {
            const entry = ranked[index];
            return `
              <li class="podium-step podium-${index + 1}">
                <a href="player.html?id=${entry.brawlhalla_id}">
                  ${rankHtml(index + 1)}
                  ${avatarHtml(entry.player_name, index === 0 ? 72 : 56)}
                  <span class="podium-name">${escapeHtml(entry.player_name)}</span>
                  ${entry.is_clan_member ? '<span class="clan-tag">Shaheen</span>' : ""}
                  ${tierBadge(entry.tier)}
                  <span class="podium-rating">${formatNumber(entry.rating)}</span>
                </a>
              </li>`;
          })
          .join("")}
      </ol>`;
  }

  function tableHtml(entries, { memberSince }) {
    const rows = entries
      .map(
        (entry, i) => `
        <tr>
          <td>${rankHtml(i + 1)}</td>
          <td>${playerCell(entry)}</td>
          <td>${entry.region ? escapeHtml(entry.region) : "—"}</td>
          <td>${entry.tier ? tierBadge(entry.tier) : "—"}</td>
          <td>${formatNumber(entry.rating)}</td>
          <td>${formatNumber(entry.peak_rating)}</td>
          ${memberSince ? `<td>${entry.member_since ? formatDate(entry.member_since) : "—"}</td>` : ""}
        </tr>`
      )
      .join("");
    return `
      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th>#</th><th>Player</th><th>Region</th><th>Tier</th><th>Rating</th><th>Peak</th>
              ${memberSince ? "<th>Member Since</th>" : ""}
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>`;
  }

  function snapshotNote(meta) {
    return meta && !meta.live && meta.capturedAt
      ? `<p class="snapshot-note">Showing the last saved copy from ${formatDate(meta.capturedAt)} — refreshing…</p>`
      : "";
  }

  function renderClan(entries, meta) {
    const el = document.getElementById("clan-content");
    if (!entries || entries.length === 0) {
      el.innerHTML = '<p class="state-msg">No linked members yet — link a Brawlhalla account with /link in Discord.</p>';
      return;
    }
    const ranked = entries.filter((entry) => entry.rating != null);
    const unplaced = entries.filter((entry) => entry.rating == null);
    el.innerHTML = `
      ${podiumHtml(ranked)}
      ${ranked.length ? tableHtml(ranked, { memberSince: true }) : '<p class="state-msg">Nobody has placed in ranked this season yet.</p>'}
      ${
        unplaced.length
          ? `<h2 class="board-subhead">Not placed this season <span>${unplaced.length}</span></h2>
             <ul class="unplaced-list">
               ${unplaced.map((entry) => `<li>${playerCell(entry, 28)}</li>`).join("")}
             </ul>`
          : ""
      }
      ${snapshotNote(meta)}`;
  }

  function renderPakistan(entries, meta) {
    const el = document.getElementById("pakistan-content");
    if (!entries || entries.length === 0) {
      el.innerHTML = '<p class="state-msg">Nobody on the Pakistan ladder yet — be the first with /pakistan join in our Discord.</p>';
      return;
    }
    el.innerHTML = `${podiumHtml(entries)}${tableHtml(entries, { memberSince: false })}${snapshotNote(meta)}`;
  }

  ShaheenAPI.withSnapshot("roster", () => ShaheenAPI.getRoster(), renderClan).catch((err) => {
    document.getElementById("clan-content").innerHTML =
      `<p class="state-msg error">Couldn't load the clan ladder: ${escapeHtml(err.message)}</p>`;
  });
  ShaheenAPI.withSnapshot("pakistan", () => ShaheenAPI.getPakistanLeaderboard(150), renderPakistan).catch(
    (err) => {
      document.getElementById("pakistan-content").innerHTML =
        `<p class="state-msg error">Couldn't load the Pakistan ladder: ${escapeHtml(err.message)}</p>`;
    }
  );
})();
