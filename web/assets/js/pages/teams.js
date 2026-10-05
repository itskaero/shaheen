// Teams (docs/DECISIONS.md ADR-114, ADR-117): a grid of holographic team
// cards, the founding team first, then by team rating. holo.js mounts the
// WebGPU surface behind each card; only cards on screen render, and a list
// re-render (search) releases the old cards automatically. A team with
// nobody placed shows no rating rather than 0.
(function () {
  const UNAVAILABLE = '<p class="unavailable">Data unavailable</p>';
  const grid = document.getElementById("team-grid");
  const search = document.getElementById("t-search");
  let teams = [];

  function render() {
    const q = (search.value || "").trim().toLowerCase();
    const shown = teams.filter((t) => !q || t.name.toLowerCase().includes(q) || t.tag.toLowerCase().includes(q));
    grid.innerHTML = shown.length
      ? shown.map((t) => holoTeamCardHtml(t)).join("")
      : teams.length
        ? '<p class="unavailable">No team matches.</p>'
        : UNAVAILABLE;
  }

  search.addEventListener("input", render);
  ShaheenAPI.withSnapshot("teams", () => ShaheenAPI.getTeams(), (list) => {
    teams = Array.isArray(list) ? list : [];
    render();
  }).catch(() => {
    if (!teams.length) grid.innerHTML = UNAVAILABLE;
  });
})();
