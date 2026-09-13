// "The Spirit of Shaheen" fade-scrollytelling section on clan.html
// (docs/DECISIONS.md ADR-075). Sibling to assets/js/pillar-scroll.js's
// pin+pan homepage hero, but a deliberately different mechanic: the
// backdrop stays one static crop (no --focus-x pan, no object-position
// shifting). Scroll instead drives a crossfade between text cards stacked
// in the sticky stage's panel column — only one card is ever opacity:1 at
// a time, so scrolling reads as a fade, not a pin-and-pan.
//
// Same fallback posture as pillar-scroll.js: inert (every card simply
// visible, no pin) under prefers-reduced-motion or missing
// IntersectionObserver.

document.addEventListener("DOMContentLoaded", () => {
  const panels = document.querySelectorAll(".spirit-panel[data-panel]");
  if (!panels.length) {
    return;
  }

  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (reduced || !("IntersectionObserver" in window)) {
    panels.forEach((panel) => {
      panel.querySelector(".spirit-panel-card")?.classList.add("in-view");
    });
    return;
  }

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) {
          return;
        }
        const card = entry.target.querySelector(".spirit-panel-card");
        if (!card) {
          return;
        }
        // Mutual exclusivity is what makes this read as a crossfade in
        // both scroll directions — unlike pillar-scroll.js, which never
        // un-marks a panel once revealed.
        panels.forEach((panel) => {
          panel.querySelector(".spirit-panel-card")?.classList.remove("in-view");
        });
        card.classList.add("in-view");
      });
    },
    { threshold: 0.55 }
  );
  panels.forEach((panel) => observer.observe(panel));
});
