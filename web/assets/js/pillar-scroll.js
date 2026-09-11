// Homepage-only "scrollytelling" hero (docs/DECISIONS.md ADR-066): a
// position:sticky banner image (styled in style.css's .pillar-hero rules)
// stays pinned behind a stack of five full-height text panels. As each
// panel crosses the middle of the viewport, this sets a CSS custom
// property (--focus-x, a left-offset percentage into the banner) that
// style.css's .pillar-vignette radial-gradient reads to "spotlight" that
// panel's character — a single source image plus a runtime vignette,
// rather than five separately generated cutout assets, so there's nothing
// that can be cropped wrong ahead of time.
//
// Inert under prefers-reduced-motion and on browsers without
// IntersectionObserver — every panel just renders in place, no pinning,
// no focus change (same fallback posture as scroll.js).

document.addEventListener("DOMContentLoaded", () => {
  const panels = document.querySelectorAll(".pillar-panel[data-focus-x]");
  if (!panels.length) {
    return;
  }

  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (reduced || !("IntersectionObserver" in window)) {
    panels.forEach((panel) => panel.classList.add("in-view"));
    return;
  }

  const root = document.documentElement;
  const eyebrowEl = document.querySelector("[data-caption-eyebrow]");
  const titleEl = document.querySelector("[data-caption-title]");

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) {
          return;
        }
        const panel = entry.target;
        panel.classList.add("in-view");
        root.style.setProperty("--focus-x", `${panel.dataset.focusX}%`);
        if (eyebrowEl && panel.dataset.eyebrow) {
          eyebrowEl.textContent = panel.dataset.eyebrow;
        }
        if (titleEl && panel.dataset.title) {
          titleEl.textContent = panel.dataset.title;
        }
      });
    },
    { threshold: 0.55 }
  );
  panels.forEach((panel) => observer.observe(panel));
});
