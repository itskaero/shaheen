// Founding Team page (docs/DECISIONS.md ADR-085, redesigned ADR-119): the
// SHAHEEN story in the site's own components. The data parts — the team's
// holographic card, clan numbers, the founding roster, recent matches and
// chat activity — each load on their own, snapshot first, and say "Data
// unavailable" rather than guessing if their source fails.
(function () {
  const UNAVAILABLE = '<p class="unavailable">Data unavailable</p>';
  const setHtml = (id, html) => {
    const el = document.getElementById(id);
    if (el) el.innerHTML = html;
  };

  // ---- the SHAHEEN holographic card, from the teams list ----
  ShaheenAPI.withSnapshot("teams", () => ShaheenAPI.getTeams(), (teams) => {
    const shaheen = (Array.isArray(teams) ? teams : []).find((t) => t.slug === "shaheen");
    if (shaheen) setHtml("founding-card", holoTeamCardHtml(shaheen, { dpr: 2, ambient: 0.32 }));
  }).catch(() => {}); // the static logo stays

  // ---- Founders & Admins (ADR-135): name, role and avatar only ----
  const STAFF_ROLES = [
    ["founder", "Founders", "Founder"],
    ["admin", "Admins", "Admin"],
  ];
  // The API sends the avatar as a data URI; anything else is ignored.
  const SAFE_AVATAR = /^data:image\/(png|webp|jpeg|gif);base64,[A-Za-z0-9+/=]+$/;

  function staffCardHtml(person, label) {
    const avatar = person.avatar && SAFE_AVATAR.test(person.avatar)
      ? `<img class="staff-avatar" src="${person.avatar}" alt="" width="56" height="56" loading="lazy" />`
      : avatarHtml(person.name, 56);
    const name = `<strong class="staff-name">${escapeHtml(person.name)}</strong>`;
    const body = `${avatar}<span class="staff-text">${name}<span class="pill ${person.role === "founder" ? "pill-founder" : "pill-team"}">${label}</span></span>`;
    return person.slug
      ? `<a class="staff-card" href="player/${encodeURIComponent(person.slug)}/" title="${escapeHtml(person.name)}'s player profile">${body}</a>`
      : `<div class="staff-card">${body}</div>`;
  }

  ShaheenAPI.withSnapshot("staff", () => ShaheenAPI.getStaff(), (staff) => {
    const people = Array.isArray(staff) ? staff : [];
    if (!people.length) return setHtml("staff-content", '<p class="unavailable">No one to show yet.</p>');
    setHtml(
      "staff-content",
      STAFF_ROLES.map(([role, heading, label]) => {
        const group = people.filter((p) => p.role === role);
        if (!group.length) return "";
        return `<div class="staff-group"><h3 class="staff-heading">${heading}</h3>
          <div class="staff-grid">${group.map((p) => staffCardHtml(p, label)).join("")}</div></div>`;
      }).join("")
    );
  }).catch(() => setHtml("staff-content", UNAVAILABLE));

  // ---- numbers ----
  ShaheenAPI.withSnapshot("clan", () => ShaheenAPI.getClan(), (clan) => {
    const stats = [];
    if (clan && typeof clan.member_count === "number") stats.push([formatNumber(clan.member_count), "Linked members"]);
    if (clan && typeof clan.discord_member_count === "number") stats.push([formatNumber(clan.discord_member_count), "In the Discord"]);
    if (clan && clan.pakistan_season) stats.push([`S${clan.pakistan_season.number}`, clan.pakistan_season.name]);
    setHtml("founding-stats", stats.map(([v, l]) => `<div><strong>${escapeHtml(v)}</strong><span>${escapeHtml(l)}</span></div>`).join(""));
  }).catch(() => {});

  // ---- founding roster: every SHAHEEN member with a linked account ----
  ShaheenAPI.withSnapshot("roster", () => ShaheenAPI.getRoster(), (entries) => {
    if (!entries || !entries.length) return setHtml("roster-content", UNAVAILABLE);
    const rows = entries
      .map(
        (e, i) => `<tr>
          <td>${e.rating != null ? rankHtml(i + 1) : '<span class="muted">—</span>'}</td>
          <td><a class="bl-player" href="player.html?id=${encodeURIComponent(e.brawlhalla_id)}">${avatarHtml(e.player_name, 28)}<span class="bl-player-name">${escapeHtml(e.player_name)}</span></a></td>
          <td class="hide-sm">${tierBadge(e.tier)}</td>
          <td class="right num">${formatNumber(e.rating)}</td>
          <td class="right hide-sm">${e.member_since ? formatDate(e.member_since) : "—"}</td>
        </tr>`
      )
      .join("");
    setHtml(
      "roster-content",
      `<div class="bl-table-wrap"><table class="bl-table">
        <thead><tr><th scope="col">#</th><th scope="col">Player</th><th scope="col" class="hide-sm">Tier</th><th scope="col" class="right">Rating</th><th scope="col" class="right hide-sm">Member since</th></tr></thead>
        <tbody>${rows}</tbody></table></div>`
    );
  }).catch(() => setHtml("roster-content", UNAVAILABLE));

  // ---- recent confirmed matches (ADR-088) ----
  ShaheenAPI.getClanMatches(8)
    .then((matches) => {
      if (!matches || !matches.length) {
        return setHtml("clan-matches", '<p class="unavailable">No confirmed matches yet — settle one with /challenge in Discord.</p>');
      }
      setHtml(
        "clan-matches",
        `<ul class="list-rows">${matches
          .map(
            (m) => `<li>
              <span><span class="pill pill-muted">${escapeHtml(m.kind.toUpperCase())}</span>
                <strong>${m.winners.length ? escapeHtml(m.winners.join(" & ")) : "Unknown"}</strong>
                <span class="muted">beat ${m.losers.length ? escapeHtml(m.losers.join(" & ")) : "Unknown"}</span></span>
              <span class="muted">${formatDate(m.confirmed_at)}</span>
            </li>`
          )
          .join("")}</ul>`
      );
    })
    .catch(() => setHtml("clan-matches", UNAVAILABLE));

  // ---- chat activity (ADR-065): linked members only ----
  ShaheenAPI.getCommunityActivity(8)
    .then((entries) => {
      if (!entries || !entries.length) {
        return setHtml("community-activity", '<p class="unavailable">No chat activity yet.</p>');
      }
      setHtml(
        "community-activity",
        `<ul class="list-rows">${entries
          .map((e, i) => {
            const from = xpForLevel(e.level);
            const span = Math.max(1, xpForLevel(e.level + 1) - from);
            const pct = Math.min(100, Math.max(4, Math.round(((e.xp - from) / span) * 100)));
            return `<li class="activity-row">
              ${rankHtml(i + 1)}
              <span class="activity-name"><strong>${escapeHtml(e.player_name)}</strong><span class="meter"><span style="width:${pct}%"></span></span></span>
              <span class="muted num">Lv ${formatNumber(e.level)}</span>
            </li>`;
          })
          .join("")}</ul>`
      );
    })
    .catch(() => setHtml("community-activity", UNAVAILABLE));
})();
