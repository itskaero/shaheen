// Full-story scrollytelling on clan.html (docs/DECISIONS.md ADR-077).
// Ported from a delivered prototype (shaheen_scrollytelling_v2) — a
// continuous scroll-position formula, not the discrete IntersectionObserver
// stops used elsewhere on this site (scroll.js, pillar-scroll.js): scroll
// progress through #story-scroll-area's tall spacer maps to a fractional
// "which scene, how far into it" position that drives everything — which
// scene is active, the two-Iqbal-quote crossfade within the spirit scene,
// and the pillar row's continuous horizontal sweep within the pillars
// scene. Kept close to the original; only selectors were renamed to match
// this page's story- prefixed classes.
//
// Same fallback posture as every other scrollytelling module here: inert
// under prefers-reduced-motion — no scroll listener attached, so the CSS
// static-stack fallback (style.css's global reduced-motion block) is what
// visitors see.

document.addEventListener("DOMContentLoaded", () => {
  const stage = document.getElementById("story-stage");
  if (!stage) {
    return;
  }

  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (reduced) {
    return;
  }

  const panels = [...document.querySelectorAll(".story-panel")];
  const bgs = [...document.querySelectorAll(".story-scene-bg")];
  const dotsWrap = document.getElementById("story-progress");
  const counter = document.getElementById("story-counter");
  const pillars = document.getElementById("story-pillars");
  const quoteEls = [...document.querySelectorAll(".story-quote")];
  if (!panels.length || !bgs.length || !dotsWrap || !counter || !pillars || quoteEls.length !== 2) {
    return;
  }

  panels.forEach(() => {
    const dot = document.createElement("i");
    dot.className = "story-dot";
    dotsWrap.appendChild(dot);
  });
  const dots = [...dotsWrap.children];

  function clamp(v, a, b) {
    return Math.max(a, Math.min(b, v));
  }

  function update() {
    const max = document.body.scrollHeight - innerHeight;
    const p = clamp(scrollY / max, 0, 1);
    const scaled = p * (panels.length - 1);
    const i = Math.floor(scaled);
    const local = scaled - i;

    panels.forEach((el, k) => el.classList.toggle("active", k === i));
    bgs.forEach((el, k) => el.classList.toggle("active", k === i));
    dots.forEach((d, k) => d.classList.toggle("active", k === Math.round(scaled)));
    counter.textContent = `${String(i + 1).padStart(2, "0")} / ${String(panels.length).padStart(2, "0")}`;

    // Poetry is two independent scroll beats within the same Spirit scene —
    // both quotes live statically in the DOM (data-quote="0"/"1") so they're
    // still readable under prefers-reduced-motion without any JS; here they
    // crossfade via opacity as the beat progresses.
    if (i === 1) {
      const qProgress = clamp(local, 0, 1);
      const which = qProgress < 0.5 ? 0 : 1;
      const other = which === 0 ? 1 : 0;
      const inOut = qProgress < 0.5 ? clamp(qProgress / 0.12, 0, 1) : clamp((1 - qProgress) / 0.12, 0, 1);
      quoteEls[which].style.opacity = inOut;
      quoteEls[other].style.opacity = 0;
    }

    // Horizontal pillar movement: center -> reveal right -> sweep left -> settle.
    if (i === 2) {
      const q = clamp(local, 0, 1);
      const travel = Math.min(1050, innerWidth * 0.95);
      const x = (q - 0.5) * travel;
      pillars.style.transform = `translateX(calc(-50% + ${x}px))`;
    }

    // Slight zoom/depth based on scroll.
    bgs.forEach((el, k) => {
      if (k === i) {
        el.style.transform = `scale(${1.025 - 0.025 * local})`;
      }
    });
  }

  addEventListener("scroll", update, { passive: true });
  addEventListener("resize", update);
  update();
});
