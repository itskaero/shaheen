(async function () {
  const titleEl = document.getElementById("tournament-title");
  const content = document.getElementById("bracket-content");
  const id = new URLSearchParams(window.location.search).get("id");

  if (!id) {
    content.innerHTML = '<p class="state-msg error">No tournament specified.</p>';
    return;
  }

  try {
    const bracket = await ShaheenAPI.getTournamentBracket(id);
    if (!bracket) {
      content.innerHTML = '<p class="state-msg error">Tournament not found.</p>';
      return;
    }

    titleEl.textContent = bracket.tournament.name;
    document.title = `${bracket.tournament.name} — Shaheen`;

    if (bracket.matches.length === 0) {
      content.innerHTML = '<p class="state-msg">Registration is still open — the bracket appears once the tournament starts.</p>';
      return;
    }

    const rounds = new Map();
    for (const match of bracket.matches) {
      if (!rounds.has(match.round_number)) {
        rounds.set(match.round_number, []);
      }
      rounds.get(match.round_number).push(match);
    }
    const roundNumbers = [...rounds.keys()].sort((a, b) => a - b);
    const totalRounds = roundNumbers.length;

    content.innerHTML = `
      <div class="table-scroll" style="border: none; background: none;">
        <div class="bracket">
          ${roundNumbers
            .map((roundNumber) => {
              const matches = rounds.get(roundNumber).sort((a, b) => a.slot_index - b.slot_index);
              return `
                <div class="bracket-round">
                  <div class="bracket-round-label">${roundLabel(roundNumber, totalRounds)}</div>
                  ${matches.map((m) => bracketMatchHtml(m)).join("")}
                </div>`;
            })
            .join("")}
        </div>
      </div>
    `;
  } catch (err) {
    content.innerHTML = `<p class="state-msg error">Couldn't load this bracket: ${err.message}</p>`;
  }
})();

function roundLabel(roundNumber, totalRounds) {
  const fromEnd = totalRounds - roundNumber;
  if (fromEnd === 0) return "Final";
  if (fromEnd === 1) return "Semifinals";
  if (fromEnd === 2) return "Quarterfinals";
  return `Round ${roundNumber}`;
}

function bracketMatchHtml(match) {
  return `
    <div class="bracket-match">
      ${entrantHtml(match.entrant_a, match.winner_entrant_id, match.status)}
      ${entrantHtml(match.entrant_b, match.winner_entrant_id, match.status)}
    </div>`;
}

function entrantHtml(entrant, winnerEntrantId, status) {
  if (!entrant) {
    const label = status === "bye" ? "BYE" : "TBD";
    return `<div class="bracket-entrant" style="color: var(--grey);">${label}</div>`;
  }
  const classes = ["bracket-entrant"];
  if (entrant.id === winnerEntrantId) classes.push("winner");
  if (entrant.eliminated && entrant.id !== winnerEntrantId) classes.push("eliminated");
  const seed = entrant.seed ? `<span class="bracket-seed">#${entrant.seed}</span>` : "";
  return `
    <div class="${classes.join(" ")}">
      <span>${escapeHtml(entrant.names.join(" & "))}</span>
      ${seed}
    </div>`;
}
