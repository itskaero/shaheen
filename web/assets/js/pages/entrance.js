// The entrance page (docs/DECISIONS.md ADR-130): live stats under the hero,
// the top-players carousel and the legend mosaic. Snapshot first, then the
// live API, like every other page.
(function () {
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const year = document.getElementById("en-year");
  if (year) year.textContent = String(new Date().getFullYear());

  // ---- hero stats ------------------------------------------------------
  const stats = new Map(); // label -> value, in display order

  function paintStats() {
    const box = document.getElementById("en-stats");
    if (!box) return;
    box.innerHTML = [...stats]
      .map(([label, value]) => `<div><dt>${escapeHtml(label)}</dt><dd class="num">${escapeHtml(String(value))}</dd></div>`)
      .join("");
  }

  ShaheenAPI.withSnapshot("clan", () => ShaheenAPI.getClan(), (clan) => {
    if (!clan) return;
    if (clan.pakistan_season) stats.set("Season", clan.pakistan_season.name);
    if (typeof clan.discord_member_count === "number") stats.set("In the Discord", clan.discord_member_count.toLocaleString());
    paintStats();
  }).catch(() => {});

  // ---- top players carousel ---------------------------------------------
  let players = [];
  let centre = 0;

  function card(r, place, active) {
    const winRate = r.games ? Math.round((r.wins / r.games) * 100) : null;
    const legend = r.main_legend ? legendDisplayName(r.main_legend) : null;
    return `<a class="en-card${active ? " is-active" : ""}" href="player.html?id=${encodeURIComponent(r.brawlhalla_id)}"${active ? "" : ' tabindex="-1" aria-hidden="true"'}>
      <span class="en-card-place">#${place}</span>
      <span class="en-card-avatar">${r.main_legend ? legendAvatarHtml(r.main_legend, 72) : avatarHtml(r.player_name, 72)}</span>
      <strong>${escapeHtml(r.player_name)}</strong>
      <span class="en-card-handle">${r.team ? escapeHtml(r.team) : "Free agent"}</span>
      <p>${escapeHtml(r.tier || "Unranked")}${legend ? ` &middot; mains ${escapeHtml(legend)}` : ""}</p>
      <span class="en-card-pills">
        <span><b class="num">${formatNumber(r.rating)}</b> rating</span>
        ${r.games ? `<span><b class="num">${formatNumber(r.games)}</b> games</span>` : ""}
        ${winRate != null ? `<span><b class="num">${winRate}%</b> wins</span>` : ""}
      </span>
    </a>`;
  }

  function paintCards() {
    const box = document.getElementById("en-cards");
    if (!box) return;
    if (!players.length) {
      box.innerHTML = '<p class="unavailable">Data unavailable</p>';
      return;
    }
    const n = players.length;
    const at = (offset) => (centre + offset + n) % n;
    const slots = n >= 3 ? [-1, 0, 1] : [0];
    box.innerHTML = slots.map((o) => card(players[at(o)], at(o) + 1, o === 0)).join("");
  }

  document.querySelectorAll(".en-arrow").forEach((button) => {
    button.addEventListener("click", () => {
      if (!players.length) return;
      centre = (centre + Number(button.dataset.dir) + players.length) % players.length;
      paintCards();
    });
  });

  ShaheenAPI.withSnapshot("rankings", () => ShaheenAPI.getRankings(), (payload) => {
    const rows = ((payload && payload.rows) || []).filter((r) => r.rating != null);
    players = rows.slice(0, 10);
    centre = 0;
    paintCards();
    if (rows.length) stats.set("Ranked players", rows.length.toLocaleString());
    paintStats();
  }).catch(() => {
    if (!players.length) paintCards();
  });

  ShaheenAPI.withSnapshot("cities", () => ShaheenAPI.getCityBoard(), (board) => {
    const n = board && board.cities ? board.cities.length : 0;
    if (n) {
      stats.set("Cities at war", n.toLocaleString());
      paintStats();
    }
  }).catch(() => {});

  // ---- legend mosaic -----------------------------------------------------
  // Portraits ship with the site (assets/img/legend-portraits), so the
  // mosaic needs no API. Each row repeats once for a seamless drift.
  const LEGENDS = [
    ["koji", "mordex", "caspian", "hattori", "val", "jiro", "artemis", "zariel", "ada", "orion", "scarlet", "ember"],
    ["bodvar", "lucien", "nix", "thatch", "kaya", "magyar", "petra", "teros", "mirage", "sentinel", "diana", "azoth"],
    ["sidra", "xull", "cassidy", "ragnir", "vector", "yumiko", "brynn", "volkov", "onyx", "queen_nai", "wu_shang", "seven"],
  ];

  function renderMosaic() {
    const box = document.getElementById("en-mosaic");
    if (!box) return;
    box.innerHTML = LEGENDS.map((row, i) => {
      const tiles = row
        .filter((key) => legendPortraitUrl(key))
        .map((key) => `<span class="en-tile"><img src="${legendPortraitUrl(key)}" alt="" width="104" height="132" loading="lazy" /><span>${escapeHtml(legendDisplayName(key))}</span></span>`)
        .join("");
      const copy = reduceMotion ? "" : `<span class="en-mosaic-copy" aria-hidden="true">${tiles}</span>`;
      return `<div class="en-mosaic-row${i % 2 ? " is-reverse" : ""}"><div class="en-mosaic-track">${tiles}${copy}</div></div>`;
    }).join("");
  }
  renderMosaic();
})();
