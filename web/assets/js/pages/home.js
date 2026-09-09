// Homepage "By the Numbers" — live counts from the existing /clan and
// /leaderboard endpoints (no new API surface). The section's fade-in is
// scroll-triggered like every other .reveal block; the count-up itself
// fires as soon as the data arrives rather than waiting for scroll, so a
// slow connection doesn't leave a visible section stuck at zero.

(async function () {
  const section = document.getElementById("live-stats");
  if (!section) {
    return;
  }

  try {
    const [clan, leaderboard] = await Promise.all([ShaheenAPI.getClan(), ShaheenAPI.getLeaderboard(1)]);

    const membersValue = section.querySelector('[data-stat="members"] .value');
    if (membersValue) {
      membersValue.dataset.countTo = clan.member_count;
      ShaheenMotion.countUp(membersValue);
    }

    const ratingStat = section.querySelector('[data-stat="rating"]');
    const top = leaderboard[0];
    if (ratingStat && top) {
      ratingStat.querySelector(".value").dataset.countTo = top.rating;
      ShaheenMotion.countUp(ratingStat.querySelector(".value"));
      const label = ratingStat.querySelector(".label");
      if (label) {
        label.textContent = `Top Rating — ${top.player_name}`;
      }
    } else if (ratingStat) {
      ratingStat.hidden = true;
    }
  } catch (err) {
    section.hidden = true;
  }
})();
