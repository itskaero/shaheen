// Full-story scrollytelling on clan.html (docs/DECISIONS.md ADR-077,
// reworked in ADR-078). A continuous scroll-position formula, not the
// discrete IntersectionObserver stops used elsewhere on this site
// (scroll.js, pillar-scroll.js): scroll progress through #story-scroll-area's
// tall spacer maps to a fractional "which scene, how far into it" position
// that drives everything — which scene is active, the eagle's
// perched->launch->flight pose (spanning the Hero + Spirit scenes
// together), the two-Iqbal-quote crossfade within the Spirit scene, the
// pillar spotlight sweep + caption crossfade within the Pillars scene, and
// the legends roster slide within the Legends scene.
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

  const scrollArea = document.querySelector(".story-scroll-area");
  const panels = [...document.querySelectorAll(".story-panel")];
  const bgs = [...document.querySelectorAll(".story-scene-bg")];
  const dotsWrap = document.getElementById("story-progress");
  const counter = document.getElementById("story-counter");
  const quoteEls = [...document.querySelectorAll(".story-quote")];
  const eagle = document.getElementById("story-eagle");
  const eaglePoses = eagle ? [...eagle.querySelectorAll(".story-eagle-pose")] : [];
  const spotlight = document.getElementById("story-pillar-spotlight");
  const pillarCaptions = [...document.querySelectorAll(".story-pillar-caption")];
  const legendsStrip = document.getElementById("story-legends");
  const legends = legendsStrip ? [...legendsStrip.querySelectorAll(".story-legend")] : [];

  if (!scrollArea || !panels.length || !bgs.length || !dotsWrap || !counter || quoteEls.length !== 2) {
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
    // Progress must be measured against the sticky stage's own pin range,
    // not the whole document's scrollable height: #clan-content/the
    // footer below add extra document height that the sticky pin never
    // actually spans, so dividing by document.body.scrollHeight would
    // make the final scene (Legacy) only reach its "active" state after
    // the stage has already started unpinning -- it would never get to
    // settle fully on screen. Anchored off .story-scroll-area (a plain,
    // non-sticky block) rather than the stage itself: a stuck
    // position:sticky element's own offsetTop tracks its current stuck
    // render position in this browser, not its static one, so it can't be
    // used as a stable boundary while scrolled.
    const storyStart = scrollArea.offsetTop - innerHeight;
    const storyRange = scrollArea.offsetHeight;
    const p = clamp((scrollY - storyStart) / storyRange, 0, 1);
    const scaled = p * (panels.length - 1);
    const i = Math.floor(scaled);
    const local = scaled - i;

    panels.forEach((el, k) => el.classList.toggle("active", k === i));
    bgs.forEach((el, k) => el.classList.toggle("active", k === i));
    dots.forEach((d, k) => d.classList.toggle("active", k === Math.round(scaled)));
    counter.textContent = `${String(i + 1).padStart(2, "0")} / ${String(panels.length).padStart(2, "0")}`;

    // Eagle: perched -> launch -> flight, spanning the Hero (scene 0) and
    // Spirit (scene 1) scenes together rather than being scoped to either
    // one — it's an independent foreground layer, not part of either
    // panel's text.
    if (eaglePoses.length === 3) {
      const eagleP = clamp(scaled, 0, 2) / 2;
      const phase = Math.min(2, Math.floor(eagleP * 3));
      eaglePoses.forEach((el, k) => el.classList.toggle("active", k === phase));
      eagle.style.transform = `translateY(${-eagleP * 12}vh) scale(${1 + eagleP * 0.15})`;
    }

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

    // Pillars: a spotlight sweeps across the five totems already baked into
    // the background art, and the matching caption (also always in the
    // DOM, same crossfade pattern as the quotes) fades in with it — no
    // sliding card row.
    if (i === 2 && spotlight && pillarCaptions.length === 5) {
      const q = clamp(local, 0, 1);
      const pi = Math.min(4, Math.floor(q * 5));
      spotlight.style.setProperty("--focus", `${12 + pi * 19}%`);
      pillarCaptions.forEach((el, k) => el.classList.toggle("active", k === pi));
    }

    // Legends: which of the five roster cutouts is active, plus the
    // horizontal slide that centers it. Step width is measured live (not
    // hardcoded) so it stays correct across the mobile breakpoint's
    // narrower cards.
    if (i === 3 && legends.length && legendsStrip) {
      const q = clamp(local, 0, 1);
      const li = Math.min(legends.length - 1, Math.floor(q * legends.length));
      legends.forEach((el, k) => el.classList.toggle("active", k === li));
      const itemW = legends[0].getBoundingClientRect().width;
      const gap = parseFloat(getComputedStyle(legendsStrip).gap) || 0;
      const step = itemW + gap;
      legendsStrip.style.transform = `translate(calc(50vw - ${li * step + itemW / 2}px), -50%)`;
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
