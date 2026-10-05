// Landing hero animation (docs/DECISIONS.md ADR-110): fireflies drifting
// over the banner, and pulses of current running through a constellation of
// Pakistani cities ("Pakistan's Brawlhalla Network"), plus a current line
// along the seam between the banner art and the hero text.
//
// Plain canvas, no library. Decorative only: the canvas is aria-hidden and
// ignores the pointer. It pauses when the hero is off-screen or the tab is
// hidden, and with prefers-reduced-motion it draws one still frame of the
// network and stops. Without JS or canvas the banner shows as before.
(function () {
  "use strict";

  const hero = document.querySelector(".hero-banner");
  const art = hero && hero.querySelector(".hero-art img");
  if (!hero || !art) return;

  const canvas = document.createElement("canvas");
  canvas.className = "hero-fx";
  canvas.setAttribute("aria-hidden", "true");
  const ctx = canvas.getContext && canvas.getContext("2d");
  if (!ctx) return;
  hero.appendChild(canvas);

  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const debug = /[?&]fx-debug\b/.test(location.search);

  const GREEN = [61, 242, 110];
  const EMERALD = [30, 224, 138];
  const GOLD = [242, 193, 78];
  const CREAM = [251, 249, 216];
  const rgba = (c, a) => `rgba(${c[0]},${c[1]},${c[2]},${a})`;

  // --- the network: real coordinates, projected into a box on the banner ---
  const CITIES = [
    ["Gilgit", 35.92, 74.31],
    ["Peshawar", 34.01, 71.58],
    ["Islamabad", 33.69, 73.05],
    ["Lahore", 31.55, 74.34],
    ["Faisalabad", 31.42, 73.08],
    ["Multan", 30.16, 71.52],
    ["Quetta", 30.18, 66.98],
    ["Sukkur", 27.7, 68.86],
    ["Hyderabad", 25.4, 68.37],
    ["Karachi", 24.86, 67.01],
    ["Gwadar", 25.13, 62.32],
  ];
  const LINKS = [
    [0, 1], [0, 2], [1, 2], [2, 3], [2, 4], [3, 4], [4, 5], [3, 5],
    [1, 6], [5, 6], [5, 7], [6, 7], [7, 8], [8, 9], [9, 10], [6, 10],
  ];
  const neighbours = CITIES.map((_, i) =>
    LINKS.filter((l) => l[0] === i || l[1] === i).map((l) => (l[0] === i ? l[1] : l[0]))
  );

  const LON0 = 61.6, LON1 = 75.6, LAT0 = 24.4, LAT1 = 36.6;
  const nodes = CITIES.map(([name, lat, lon]) => ({
    name,
    u: (lon - LON0) / (LON1 - LON0), // 0..1 west -> east
    v: (LAT1 - lat) / (LAT1 - LAT0), // 0..1 north -> south
    x: 0,
    y: 0,
    flare: 0,
    phase: Math.random() * Math.PI * 2,
  }));

  // --- layout -------------------------------------------------------------
  let width = 0, height = 0, dpr = 1;
  let bannerBottom = 0; // y of the seam between banner art and hero text
  let unit = 1; // scale for speeds/sizes, ~1 at a 1200px-wide hero
  let veil = null; // dark backdrop that lets the network read over busy art

  function layout() {
    const rect = hero.getBoundingClientRect();
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    width = rect.width;
    height = rect.height;
    canvas.width = Math.round(width * dpr);
    canvas.height = Math.round(height * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    const artRect = art.getBoundingClientRect();
    const artTop = artRect.top - rect.top;
    bannerBottom = artTop + artRect.height;
    unit = Math.max(0.55, Math.min(1.3, width / 1200));

    // The night sky above the skyline, right of the logo. On a narrow
    // screen the banner is cropped at the sides, so the box moves inward.
    const narrow = width < 720;
    const boxH = artRect.height * (narrow ? 0.8 : 0.84);
    const boxW = Math.min(width * (narrow ? 0.36 : 0.26), boxH * 1.05);
    const boxX = width * (narrow ? 0.97 : 0.975) - boxW;
    const boxY = artTop + artRect.height * 0.07;
    veil = { x: boxX + boxW * 0.5, y: boxY + boxH * 0.5, r: Math.max(boxW, boxH) * 0.72 };
    for (const n of nodes) {
      n.x = boxX + n.u * boxW;
      n.y = boxY + n.v * boxH;
    }
    resetFlies();
    if (reduceMotion) drawStill();
  }

  // --- glow sprites, rendered once per colour ------------------------------
  function sprite(c) {
    const s = document.createElement("canvas");
    s.width = s.height = 64;
    const g = s.getContext("2d");
    const grad = g.createRadialGradient(32, 32, 0, 32, 32, 32);
    grad.addColorStop(0, rgba([255, 255, 255], 1));
    grad.addColorStop(0.12, rgba(c, 0.95));
    grad.addColorStop(0.4, rgba(c, 0.28));
    grad.addColorStop(1, rgba(c, 0));
    g.fillStyle = grad;
    g.fillRect(0, 0, 64, 64);
    return s;
  }
  const SPRITES = { green: sprite(GREEN), gold: sprite(GOLD), cream: sprite(CREAM) };

  function glow(img, x, y, size, alpha) {
    if (alpha <= 0.01) return;
    ctx.globalAlpha = alpha;
    ctx.drawImage(img, x - size / 2, y - size / 2, size, size);
    ctx.globalAlpha = 1;
  }

  // --- fireflies --------------------------------------------------------------
  const flies = [];
  function resetFlies() {
    const count = width < 720 ? 22 : 46;
    flies.length = 0;
    for (let i = 0; i < count; i++) {
      const roll = Math.random();
      flies.push({
        x: Math.random() * width,
        // Most live over the art; a few drift down over the text.
        y: Math.random() < 0.55 ? Math.random() * bannerBottom : bannerBottom + Math.random() * (height - bannerBottom),
        size: 12 + Math.random() * 14,
        img: roll < 0.55 ? SPRITES.green : roll < 0.85 ? SPRITES.cream : SPRITES.gold,
        a: Math.random() * 1000,
        b: Math.random() * 1000,
        speed: 10 + Math.random() * 18,
        flicker: 0.6 + Math.random() * 1.4,
        phase: Math.random() * Math.PI * 2,
      });
    }
  }

  function updateFlies(dt, t) {
    for (const f of flies) {
      // Layered sines give a smooth, wandering heading without a noise lib.
      const heading =
        Math.sin(t * 0.00031 + f.a) * 1.7 + Math.sin(t * 0.00073 + f.b) * 0.9 - Math.PI / 2;
      f.x += Math.cos(heading) * f.speed * unit * dt;
      f.y += (Math.sin(heading) * 0.7 - 0.25) * f.speed * unit * dt; // slow upward bias
      if (pointer) {
        const dx = pointer.x - f.x, dy = pointer.y - f.y;
        const d2 = dx * dx + dy * dy;
        if (d2 < 120 * 120 && d2 > 1) {
          f.x += dx * 0.9 * dt;
          f.y += dy * 0.9 * dt;
        }
      }
      if (f.x < -20) f.x = width + 20;
      else if (f.x > width + 20) f.x = -20;
      if (f.y < -20) f.y = height + 20;
      else if (f.y > height + 20) f.y = -20;
    }
  }

  function drawFlies(t) {
    for (const f of flies) {
      const pulse = 0.5 + 0.5 * Math.sin(t * 0.001 * f.flicker + f.phase);
      glow(f.img, f.x, f.y, f.size * Math.max(unit, 0.8) * (0.8 + pulse * 0.4), 0.12 + pulse * pulse * 0.88);
    }
  }

  // --- current through the network -----------------------------------------
  const MAX_PULSES = 6;
  const pulses = [];
  let nextPulseAt = 0;

  function spawnPulse(start) {
    if (pulses.length >= MAX_PULSES) return;
    const hops = 2 + Math.floor(Math.random() * 3);
    const path = [start];
    for (let i = 0; i < hops; i++) {
      const here = path[path.length - 1];
      const options = neighbours[here].filter((n) => n !== path[path.length - 2]);
      if (!options.length) break;
      path.push(options[Math.floor(Math.random() * options.length)]);
    }
    if (path.length < 2) return;
    nodes[start].flare = 1;
    pulses.push({
      path,
      leg: 0,
      progress: 0, // 0..1 along the current leg
      color: Math.random() < 0.2 ? GOLD : GREEN,
          });
  }

  function updatePulses(dt, t) {
    if (t >= nextPulseAt) {
      spawnPulse(Math.floor(Math.random() * nodes.length));
      nextPulseAt = t + 600 + Math.random() * 800;
    }
    for (let i = pulses.length - 1; i >= 0; i--) {
      const p = pulses[i];
      const a = nodes[p.path[p.leg]], b = nodes[p.path[p.leg + 1]];
      const len = Math.hypot(b.x - a.x, b.y - a.y) || 1;
      p.progress += (170 * unit * dt) / len;
      if (p.progress >= 1) {
        b.flare = 1;
        p.leg += 1;
        p.progress = 0;
        if (p.leg >= p.path.length - 1) pulses.splice(i, 1);
      }
    }
  }

  function drawVeil() {
    if (!veil) return;
    const grad = ctx.createRadialGradient(veil.x, veil.y, 0, veil.x, veil.y, veil.r);
    grad.addColorStop(0, "rgba(3,8,6,0.74)");
    grad.addColorStop(0.6, "rgba(3,8,6,0.5)");
    grad.addColorStop(1, "rgba(3,8,6,0)");
    ctx.fillStyle = grad;
    ctx.fillRect(veil.x - veil.r, veil.y - veil.r, veil.r * 2, veil.r * 2);
  }

  function drawNetwork(t, still) {
    ctx.lineWidth = 1.4;
    ctx.strokeStyle = rgba(EMERALD, 0.55);
    ctx.beginPath();
    for (const [i, j] of LINKS) {
      ctx.moveTo(nodes[i].x, nodes[i].y);
      ctx.lineTo(nodes[j].x, nodes[j].y);
    }
    ctx.stroke();

    if (!still) {
      for (const p of pulses) {
        const a = nodes[p.path[p.leg]], b = nodes[p.path[p.leg + 1]];
        const hx = a.x + (b.x - a.x) * p.progress;
        const hy = a.y + (b.y - a.y) * p.progress;
        const len = Math.hypot(b.x - a.x, b.y - a.y) || 1;
        const tail = Math.min(p.progress, (70 * unit) / len);
        const tx = a.x + (b.x - a.x) * (p.progress - tail);
        const ty = a.y + (b.y - a.y) * (p.progress - tail);
        const grad = ctx.createLinearGradient(tx, ty, hx, hy);
        grad.addColorStop(0, rgba(p.color, 0));
        grad.addColorStop(1, rgba(p.color, 0.95));
        ctx.strokeStyle = grad;
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.moveTo(tx, ty);
        ctx.lineTo(hx, hy);
        ctx.stroke();
        glow(p.color === GOLD ? SPRITES.gold : SPRITES.green, hx, hy, 34 * Math.max(unit, 0.8), 1);
      }
    }

    for (const n of nodes) {
      const breathe = still ? 0.5 : 0.5 + 0.5 * Math.sin(t * 0.0012 + n.phase);
      const size = (14 + breathe * 6 + n.flare * 30) * Math.max(unit, 0.75);
      glow(SPRITES.cream, n.x, n.y, size, 0.75 + n.flare * 0.25);
      if (!still) n.flare = Math.max(0, n.flare - 0.025);
    }
  }

  // --- current along the seam under the banner ------------------------------
  function drawSeam(t, still) {
    const y = bannerBottom - 0.5;
    ctx.lineWidth = 1;
    ctx.strokeStyle = rgba(EMERALD, 0.35);
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(width, y);
    ctx.stroke();
    if (still) return;
    const period = 5200;
    const k = (t % period) / period; // 0..1 sweep, then a pause
    const span = width + 400;
    const head = -200 + (k / 0.7) * span;
    if (k > 0.7) return;
    const grad = ctx.createLinearGradient(head - 220 * unit, y, head, y);
    grad.addColorStop(0, rgba(GREEN, 0));
    grad.addColorStop(1, rgba(GREEN, 1));
    ctx.strokeStyle = grad;
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(head - 220 * unit, y);
    ctx.lineTo(head, y);
    ctx.stroke();
    glow(SPRITES.green, head, y, 40 * Math.max(unit, 0.8), 1);
  }

  // --- pointer: fireflies lean in, the nearest city fires -------------------
  let pointer = null;
  let lastPointerPulse = 0;
  function onPointer(event) {
    const rect = hero.getBoundingClientRect();
    pointer = { x: event.clientX - rect.left, y: event.clientY - rect.top };
    const now = performance.now();
    if (reduceMotion || now - lastPointerPulse < 400) return;
    let best = -1, bestD = (60 * unit) ** 2;
    nodes.forEach((n, i) => {
      const d = (n.x - pointer.x) ** 2 + (n.y - pointer.y) ** 2;
      if (d < bestD) {
        bestD = d;
        best = i;
      }
    });
    if (best >= 0) {
      lastPointerPulse = now;
      spawnPulse(best);
    }
  }
  hero.addEventListener("pointermove", onPointer, { passive: true });
  hero.addEventListener("pointerdown", onPointer, { passive: true });
  hero.addEventListener("pointerleave", () => (pointer = null));

  // --- loop -------------------------------------------------------------------
  let running = false, visible = true, raf = 0, last = 0;

  function frame(now) {
    if (!running) return;
    const dt = Math.min(0.05, (now - last) / 1000 || 0);
    last = now;
    ctx.clearRect(0, 0, width, height);
    drawVeil();
    ctx.globalCompositeOperation = "lighter";
    updatePulses(dt, now);
    drawNetwork(now, false);
    drawSeam(now, false);
    updateFlies(dt, now);
    drawFlies(now);
    ctx.globalCompositeOperation = "source-over";
    if (debug) window.__heroFxFrames = (window.__heroFxFrames || 0) + 1;
    raf = requestAnimationFrame(frame);
  }

  function drawStill() {
    ctx.clearRect(0, 0, width, height);
    drawVeil();
    ctx.globalCompositeOperation = "lighter";
    drawNetwork(0, true);
    drawSeam(0, true);
    ctx.globalCompositeOperation = "source-over";
  }

  function setRunning(next) {
    if (reduceMotion || next === running) return;
    running = next;
    if (running) {
      last = performance.now();
      raf = requestAnimationFrame(frame);
    } else {
      cancelAnimationFrame(raf);
    }
  }

  const update = () => setRunning(visible && !document.hidden);

  if (art.complete) layout();
  else art.addEventListener("load", layout, { once: true });
  if ("ResizeObserver" in window) new ResizeObserver(layout).observe(hero);
  else window.addEventListener("resize", layout);

  if ("IntersectionObserver" in window) {
    new IntersectionObserver((entries) => {
      visible = entries[entries.length - 1].isIntersecting;
      update();
    }).observe(hero);
  }
  document.addEventListener("visibilitychange", update);
  if (reduceMotion) {
    drawStill();
    if (debug) window.__heroFxFrames = 0;
  } else {
    update();
  }
})();
