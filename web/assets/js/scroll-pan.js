// Generalized sticky-stage/panel-column scroll mechanism shared by all three
// clan.html scrollytelling sections (docs/DECISIONS.md ADR-076, supersedes
// spirit-scroll.js). One IntersectionObserver({threshold:0.55}) per stage;
// only one [data-scroll-card] is ever .in-view within that stage's panels
// at a time (mutual-exclusion crossfade, unchanged from spirit-scroll.js —
// the outgoing card fades to opacity:0 at the same moment the incoming one
// fades to opacity:1, a true crossfade in both scroll directions).
//
// Panels with data-pan-x additionally write --pan-x onto that stage's own
// [data-scroll-visual] element — read by that section's CSS to pan a
// background image horizontally (mirrors the homepage's pillar-scroll.js
// --focus-x technique, but scoped per-stage instead of global on <html>,
// since clan.html runs three independent stages on one page — unlike the
// homepage's one). Panels without data-pan-x (The Spirit of Shaheen) leave
// that branch a no-op, reproducing the original pan-free behavior exactly.
//
// Same fallback posture as pillar-scroll.js: every card simply visible, no
// pin/pan, under prefers-reduced-motion or missing IntersectionObserver
// (also unreachable on narrow/short viewports — style.css disables
// position:sticky there instead).

document.addEventListener("DOMContentLoaded", () => {
  const stages = document.querySelectorAll("[data-scroll-stage]");
  if (!stages.length) {
    return;
  }

  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  stages.forEach((stage) => {
    const panels = stage.querySelectorAll("[data-scroll-panel]");
    if (!panels.length) {
      return;
    }
    const visual = stage.querySelector("[data-scroll-visual]");

    if (reduced || !("IntersectionObserver" in window)) {
      panels.forEach((panel) => {
        panel.querySelector("[data-scroll-card]")?.classList.add("in-view");
      });
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) {
            return;
          }
          const panel = entry.target;
          const card = panel.querySelector("[data-scroll-card]");
          if (card) {
            panels.forEach((p) => p.querySelector("[data-scroll-card]")?.classList.remove("in-view"));
            card.classList.add("in-view");
          }
          if (visual && panel.dataset.panX !== undefined) {
            visual.style.setProperty("--pan-x", `${panel.dataset.panX}%`);
          }
        });
      },
      { threshold: 0.55 }
    );
    panels.forEach((panel) => observer.observe(panel));
  });
});
