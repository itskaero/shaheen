// Horizontal scroll-snap carousels ("What We Stand For" / "Shaheen Is More
// Than a Name" on clan.html, docs/DECISIONS.md ADR-075). Native CSS
// scroll-snap does all the actual scrolling/snapping with zero JS — this
// file only adds optional prev/next buttons for keyboard/mouse users
// without a trackpad or touchscreen. Buttons ship `hidden` in markup and
// are only unhidden once wired up here, so a JS failure never leaves a
// dead button behind (same posture as the header's .discord-widget).

document.addEventListener("DOMContentLoaded", () => {
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  document.querySelectorAll("[data-carousel]").forEach((carousel) => {
    const track = carousel.querySelector("[data-carousel-track]");
    const prevBtn = carousel.querySelector("[data-carousel-prev]");
    const nextBtn = carousel.querySelector("[data-carousel-next]");
    if (!track || !prevBtn || !nextBtn) {
      return;
    }

    function step() {
      const card = track.querySelector(":scope > *");
      return card ? card.getBoundingClientRect().width + 20 : track.clientWidth * 0.8;
    }

    function updateArrows() {
      const max = track.scrollWidth - track.clientWidth - 2;
      prevBtn.disabled = track.scrollLeft <= 2;
      nextBtn.disabled = track.scrollLeft >= max;
    }

    prevBtn.addEventListener("click", () => {
      track.scrollBy({ left: -step(), behavior: reduced ? "auto" : "smooth" });
    });
    nextBtn.addEventListener("click", () => {
      track.scrollBy({ left: step(), behavior: reduced ? "auto" : "smooth" });
    });

    let ticking = false;
    track.addEventListener(
      "scroll",
      () => {
        if (!ticking) {
          ticking = true;
          requestAnimationFrame(() => {
            ticking = false;
            updateArrows();
          });
        }
      },
      { passive: true }
    );

    prevBtn.hidden = false;
    nextBtn.hidden = false;
    updateArrows();
  });
});
