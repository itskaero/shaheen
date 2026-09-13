// Scroll-driven polish for the landing page: reveal-on-scroll (.reveal),
// animated count-up numbers (shared as ShaheenMotion.countUp so page
// scripts can trigger one as soon as its data arrives, independent of
// scroll position), and a subtle parallax offset on .cinematic-strip.
// Vanilla JS, IntersectionObserver-based, fully inert under
// prefers-reduced-motion.

const ShaheenMotion = (() => {
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function countUp(el) {
    const target = Number(el.dataset.countTo);
    if (!Number.isFinite(target)) {
      return;
    }
    if (reduced) {
      el.textContent = target.toLocaleString();
      return;
    }
    const duration = 1100;
    const start = performance.now();
    function frame(now) {
      const progress = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - progress, 3);
      el.textContent = Math.round(target * eased).toLocaleString();
      if (progress < 1) {
        requestAnimationFrame(frame);
      }
    }
    requestAnimationFrame(frame);
  }

  return { reduced, countUp };
})();

document.addEventListener("DOMContentLoaded", () => {
  const plainRevealTargets = document.querySelectorAll(".reveal");
  // .clan-reveal (clan.html's diagonal clip-path wipe, docs/DECISIONS.md
  // ADR-066/074) starts from a degenerate zero-area clip-path
  // (`polygon(0 0, 0 0, 0 100%, 0 100%)`) until `.in-view` grows it — and at
  // least this Chromium build computes intersectionRatio against that
  // *clipped* (post-clip-path) area, so it's permanently ~0 no matter how
  // visible the element actually is. A 0.2 threshold (fine for plain
  // opacity-based .reveal) would therefore never cross for .clan-reveal, so
  // it needs its own observer at threshold 0, where isIntersecting only
  // needs the (unclipped) layout box to overlap the root at all.
  const clanRevealTargets = document.querySelectorAll(".clan-reveal");

  if (ShaheenMotion.reduced || !("IntersectionObserver" in window)) {
    [...plainRevealTargets, ...clanRevealTargets].forEach((el) => {
      el.classList.add("in-view");
      el.querySelectorAll("[data-count-to]").forEach(ShaheenMotion.countUp);
    });
  } else {
    const reveal = (observer) => (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("in-view");
          entry.target.querySelectorAll("[data-count-to]").forEach(ShaheenMotion.countUp);
          observer.unobserve(entry.target);
        }
      });
    };

    const plainObserver = new IntersectionObserver(
      (entries) => reveal(plainObserver)(entries),
      { threshold: 0.2, rootMargin: "0px 0px -60px 0px" }
    );
    plainRevealTargets.forEach((el) => plainObserver.observe(el));

    const clanObserver = new IntersectionObserver(
      (entries) => reveal(clanObserver)(entries),
      { threshold: 0, rootMargin: "0px 0px -60px 0px" }
    );
    clanRevealTargets.forEach((el) => clanObserver.observe(el));
  }

  const strip = document.querySelector(".cinematic-strip");
  if (strip && !ShaheenMotion.reduced) {
    let ticking = false;
    function updateParallax() {
      ticking = false;
      const rect = strip.getBoundingClientRect();
      const center = rect.top + rect.height / 2 - window.innerHeight / 2;
      const offset = Math.max(-30, Math.min(30, center * -0.08));
      strip.style.backgroundPositionY = `calc(15% + ${offset}px)`;
    }
    window.addEventListener(
      "scroll",
      () => {
        if (!ticking) {
          ticking = true;
          requestAnimationFrame(updateParallax);
        }
      },
      { passive: true }
    );
    updateParallax();
  }
});
