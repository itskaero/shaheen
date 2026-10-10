// BRAWLISTAN app shell (docs/DECISIONS.md ADR-104): the landscape scene,
// sidebar, top bar, mobile bottom nav and footer, rendered once here instead
// of copied into every page. Pages provide the slots:
//
//   <body class="bl" data-page="rankings">
//     <div class="bl-scene" aria-hidden="true"></div>
//     <div class="bl-app">
//       <nav class="bl-sidebar" data-shell="sidebar" aria-label="Main"></nav>
//       <div class="bl-main">
//         <header class="bl-topbar" data-shell="topbar"></header>
//         <main id="main">…</main>
//         <footer class="bl-footer" data-shell="footer"></footer>
//       </div>
//     </div>
//     <nav class="bl-bottomnav" data-shell="bottomnav" aria-label="Main"></nav>
//
// Load after config.js and before api.js: api.js fills [data-discord-invite]
// and [data-discord-widget] on DOMContentLoaded, so the shell's markup must
// already exist by then.
(function () {
  const ICONS = {
    home: '<path d="M3 10.5 12 3l9 7.5"/><path d="M5 9.5V20h5v-6h4v6h5V9.5"/>',
    trophy:
      '<path d="M8 21h8M12 17v4M7 4h10v5a5 5 0 0 1-10 0V4Z"/><path d="M17 5h3v2a3 3 0 0 1-3 3M7 5H4v2a3 3 0 0 0 3 3"/>',
    users:
      '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20a6.5 6.5 0 0 1 13 0"/><path d="M16 4.6a3.5 3.5 0 0 1 0 6.8M18 14a6.5 6.5 0 0 1 3.5 6"/>',
    shield: '<path d="M12 3 4 6v6c0 4.5 3.4 8.2 8 9 4.6-.8 8-4.5 8-9V6l-8-3Z"/>',
    swords:
      '<path d="M14.5 17.5 3 6V3h3l11.5 11.5M13 19l6-6M16 16l4 4M19 21l2-2"/><path d="M9.5 6.5 14 2h3v3l-4.5 4.5M5 14l-2 2M3 21l2-2"/>',
    calendar: '<rect x="3.5" y="5" width="17" height="15.5" rx="2.5"/><path d="M3.5 10h17M8 3v4M16 3v4"/>',
    flag: '<path d="M5 21V4M5 4h11l-2 4 2 4H5"/>',
    chart: '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
    discord:
      '<path d="M8.5 15.5c2.3 1 4.7 1 7 0M8 4.5c-1.6.3-3.1.9-4.4 1.8C1.8 10 1.3 13.6 1.6 17.2 3.4 18.6 5.3 19.4 7.3 20l1.2-2M16 4.5c1.6.3 3.1.9 4.4 1.8 1.8 3.7 2.3 7.3 2 10.9-1.8 1.4-3.7 2.2-5.7 2.8l-1.2-2M9 4.5l.6 1.4c1.6-.2 3.2-.2 4.8 0l.6-1.4"/><circle cx="9" cy="12.5" r="1.3"/><circle cx="15" cy="12.5" r="1.3"/>',
    award: '<circle cx="12" cy="9" r="6"/><path d="m8.5 14-1.5 7 5-3 5 3-1.5-7"/>',
    music: '<path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/>',
    feather: '<path d="M20 4c-6 0-12 4-14 12l-2 4M16 8 6 18M9 15h6"/>',
    cap: '<path d="M2 9.5 12 5l10 4.5-10 4.5L2 9.5Z"/><path d="M6 11.3V16c1.7 1.6 3.7 2.4 6 2.4s4.3-.8 6-2.4v-4.7M22 9.5V15"/>',
    search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
  };

  // `ready: false` hides an item until its page ships (BRAWLISTAN_MIGRATION.md
  // stages), so the nav never links to a page that doesn't exist yet.
  const NAV = [
    { key: "home", label: "Home", href: "index.html", icon: "home", mobile: true },
    { key: "rankings", label: "Rankings", href: "rankings.html", icon: "trophy", mobile: true },
    { key: "players", label: "Players", href: "players.html", icon: "users", mobile: true },
    { key: "teams", label: "Teams", href: "teams.html", icon: "shield" },
    { key: "coaches", label: "Coaches", href: "coaches.html", icon: "cap" },
    { key: "legends", label: "Legends", href: "legends.html", icon: "swords", ready: false },
    { key: "seasons", label: "Seasons", href: "seasons.html", icon: "calendar", mobile: true },
    { key: "tournaments", label: "Tournaments", href: "tournaments.html", icon: "flag" },
    { key: "statistics", label: "Statistics", href: "statistics.html", icon: "chart", ready: false },
    { key: "discord", label: "Discord", href: "join.html", icon: "discord", mobile: true },
  ];

  const COMMUNITY = [
    { key: "achievements", label: "Achievements", href: "achievements.html", icon: "award" },
    { key: "shaheen", label: "Founding Team", href: "clan.html", icon: "feather" },
    { key: "anthem", label: "Music", href: "music.html", icon: "music" },
  ];

  const page = document.body.dataset.page || "";

  function icon(name) {
    return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONS[name] || ""}</svg>`;
  }

  function navLink(item) {
    const current = item.key === page ? ' aria-current="page"' : "";
    return `<li><a href="${item.href}"${current}>${icon(item.icon)}<span>${item.label}</span></a></li>`;
  }

  const visible = NAV.filter((item) => item.ready !== false);

  // ---- scene: generated SVG landscape (no photo to download) ----
  function seeded(seed) {
    let s = seed;
    return () => {
      s = (s * 16807) % 2147483647;
      return (s - 1) / 2147483646;
    };
  }

  function ridge(rand, { base, amp, step, jag }) {
    const points = [];
    let y = base;
    for (let x = -40; x <= 1640; x += step) {
      y = Math.max(base - amp, Math.min(base + amp * 0.35, y + (rand() - 0.55) * jag));
      points.push(`${x},${y.toFixed(1)}`);
    }
    return `M-40,900 L${points.join(" L")} L1640,900 Z`;
  }

  function topoLines(rand) {
    const lines = [];
    for (let i = 0; i < 9; i++) {
      const y = 120 + i * 58;
      const a = 14 + rand() * 18;
      const f = 0.004 + rand() * 0.003;
      const phase = rand() * Math.PI * 2;
      let d = "";
      for (let x = -20; x <= 1620; x += 40) {
        const yy = y + Math.sin(x * f + phase) * a + Math.sin(x * f * 2.3) * a * 0.3;
        d += `${x === -20 ? "M" : " L"}${x},${yy.toFixed(1)}`;
      }
      lines.push(`<path d="${d}"/>`);
    }
    return lines.join("");
  }

  function renderScene() {
    const scene = document.querySelector(".bl-scene");
    if (!scene) return;
    const rand = seeded(1947);
    scene.innerHTML = `
      <svg viewBox="0 0 1600 900" preserveAspectRatio="xMidYMax slice" aria-hidden="true">
        <defs>
          <linearGradient id="bl-far" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stop-color="#1b2420"/><stop offset="1" stop-color="#101614"/>
          </linearGradient>
          <linearGradient id="bl-mid" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stop-color="#121a16"/><stop offset="1" stop-color="#0b100e"/>
          </linearGradient>
        </defs>
        <g class="topo">${topoLines(rand)}</g>
        <path d="${ridge(rand, { base: 560, amp: 230, step: 26, jag: 60 })}" fill="url(#bl-far)" opacity="0.9"/>
        <path d="${ridge(rand, { base: 650, amp: 150, step: 34, jag: 46 })}" fill="url(#bl-mid)"/>
        <path d="${ridge(rand, { base: 760, amp: 70, step: 60, jag: 26 })}" fill="#080b0a"/>
        <path class="flight" d="M-40,640 C 320,420 640,520 900,330 S 1380,180 1660,90"/>
      </svg>`;
    const motionOk = !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (!motionOk) return;
    for (let i = 0; i < 26; i++) {
      const p = document.createElement("span");
      p.className = "bl-particle";
      p.style.left = `${(rand() * 100).toFixed(2)}%`;
      p.style.top = `${(40 + rand() * 55).toFixed(2)}%`;
      p.style.setProperty("--d", `${(14 + rand() * 16).toFixed(1)}s`);
      p.style.setProperty("--delay", `${(-rand() * 20).toFixed(1)}s`);
      p.style.setProperty("--dx", `${Math.round((rand() - 0.5) * 120)}px`);
      scene.appendChild(p);
    }
  }

  // ---- sidebar ----
  function renderSidebar() {
    const el = document.querySelector('[data-shell="sidebar"]');
    if (!el) return;
    const players = NAV.find((item) => item.key === "players");
    const search =
      players && players.ready !== false
        ? `<form class="bl-search" role="search" action="players.html">
             <label class="sr-only" for="bl-search-input">Search players</label>
             ${icon("search")}
             <input id="bl-search-input" name="q" type="search" placeholder="Search players" autocomplete="off" />
           </form>`
        : "";
    el.innerHTML = `
      <a class="bl-brand" href="index.html" aria-label="BRAWLISTAN home">
        <picture>
          <source srcset="assets/img/brawlistan/wordmark.webp" type="image/webp" />
          <img src="assets/img/brawlistan/wordmark.png" alt="BRAWLISTAN" width="132" height="44" />
        </picture>
      </a>
      ${search}
      <ul class="bl-nav">${visible.map(navLink).join("")}</ul>
      <div>
        <div class="bl-nav-group-label">Season</div>
        <a class="bl-season-mini" href="seasons.html" data-shell="season" hidden></a>
      </div>
      <div>
        <div class="bl-nav-group-label">Community</div>
        <ul class="bl-nav">${COMMUNITY.map(navLink).join("")}</ul>
      </div>
      <div class="bl-sidebar-foot">Founded by <a href="clan.html">SHAHEEN</a></div>`;
  }

  // ---- top bar ----
  function renderTopbar() {
    const el = document.querySelector('[data-shell="topbar"]');
    if (!el) return;
    el.innerHTML = `
      <a class="bl-topbar-brand" href="index.html" aria-label="BRAWLISTAN home">
        <picture>
          <source srcset="assets/img/brawlistan/wordmark.webp" type="image/webp" />
          <img src="assets/img/brawlistan/wordmark.png" alt="BRAWLISTAN" width="102" height="34" />
        </picture>
      </a>
      <span class="bl-online" data-discord-widget hidden></span>
      <a class="btn btn-primary btn-sm" data-discord-invite href="join.html" target="_blank" rel="noopener">${icon("discord")}Join Discord</a>`;
  }

  // ---- mobile bottom nav ----
  function renderBottomNav() {
    const el = document.querySelector('[data-shell="bottomnav"]');
    if (!el) return;
    const items = visible.filter((item) => item.mobile);
    el.style.setProperty("--items", String(items.length));
    el.innerHTML = items
      .map((item) => {
        const current = item.key === page ? ' aria-current="page"' : "";
        return `<a href="${item.href}"${current}>${icon(item.icon)}<span>${item.label}</span></a>`;
      })
      .join("");
  }

  // ---- footer ----
  function renderFooter() {
    const el = document.querySelector('[data-shell="footer"]');
    if (!el) return;
    el.innerHTML = `
      <span>&copy; <span id="year"></span> BRAWLISTAN &mdash; Pakistan's Brawlhalla Network &middot; <span lang="ur">بلندیوں کی جانب</span></span>
      <span>Founded by <a href="clan.html">SHAHEEN</a> &middot; Data from the official Brawlhalla API &middot; Not affiliated with Blue Mammoth Games</span>`;
  }

  // ---- current season, once api.js has loaded ----
  function renderSeason(clan) {
    const el = document.querySelector('[data-shell="season"]');
    const season = clan && clan.pakistan_season;
    if (!el || !season) return;
    const badge = `assets/img/seasons/${encodeURIComponent(season.badge)}`;
    el.innerHTML = `
      <picture><source srcset="${badge}.webp" type="image/webp" /><img src="${badge}.jpg" alt="" width="34" height="30" /></picture>
      <span><strong>Season ${season.number}</strong><span>${escapeHtml(season.name)}</span></span>`;
    el.hidden = false;
  }

  // In-page "#…" links (the skip link, section anchors) must stay on this
  // page. Generated player pages set <base href="../../"> (ADR-106), which
  // would otherwise resolve "#main" against the site root and navigate away.
  document.addEventListener("click", (event) => {
    const link = event.target.closest && event.target.closest('a[href^="#"]');
    if (!link || link.getAttribute("href").length < 2) return;
    const target = document.getElementById(link.getAttribute("href").slice(1));
    if (!target) return;
    event.preventDefault();
    if (!target.hasAttribute("tabindex")) target.setAttribute("tabindex", "-1");
    target.focus({ preventScroll: true });
    target.scrollIntoView({ behavior: "smooth", block: "start" });
  });

  renderScene();
  renderSidebar();
  renderTopbar();
  renderBottomNav();
  renderFooter();

  document.addEventListener("DOMContentLoaded", () => {
    if (typeof ShaheenAPI === "undefined") return;
    ShaheenAPI.withSnapshot("clan", () => ShaheenAPI.getClan(), renderSeason).catch(() => {});
  });
})();
