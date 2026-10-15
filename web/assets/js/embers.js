// Rising embers and red fireflies (docs/DECISIONS.md ADR-130) over any
// element marked [data-embers]: the entrance hero and the home dashboard's
// season banner.
//
// Plain canvas, no library, decorative only: the canvas is aria-hidden and
// ignores the pointer. Glows are pre-rendered sprites drawn with "lighter"
// compositing, the device pixel ratio is capped at 2, and the loop pauses
// while the element is off-screen or the tab is hidden. With
// prefers-reduced-motion it paints one still frame and never animates.
//
// data-embers="<n>" sets the ember count on a wide screen (default 90); it
// scales down with the element's area.
(function () {
  "use strict";

  const hosts = document.querySelectorAll("[data-embers]");
  if (!hosts.length) return;

  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // Fire palette, from the art: blood red, ember orange, gold, and a rare
  // Pakistan-green firefly.
  const COLOURS = [
    [255, 46, 46],
    [255, 72, 28],
    [255, 120, 40],
    [255, 170, 60],
    [255, 214, 120],
  ];
  const GREEN = [61, 242, 110];

  const spriteCache = new Map();
  function sprite(rgb) {
    const key = rgb.join(",");
    if (spriteCache.has(key)) return spriteCache.get(key);
    const size = 64;
    const c = document.createElement("canvas");
    c.width = c.height = size;
    const g = c.getContext("2d");
    const grad = g.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
    grad.addColorStop(0, "rgba(255,248,230,1)");
    grad.addColorStop(0.12, `rgba(${key},0.95)`);
    grad.addColorStop(0.4, `rgba(${key},0.28)`);
    grad.addColorStop(1, `rgba(${key},0)`);
    g.fillStyle = grad;
    g.fillRect(0, 0, size, size);
    spriteCache.set(key, c);
    return c;
  }

  function pick(list) {
    return list[Math.floor(Math.random() * list.length)];
  }

  function attach(host) {
    const canvas = document.createElement("canvas");
    canvas.className = "embers-fx";
    canvas.setAttribute("aria-hidden", "true");
    const ctx = canvas.getContext && canvas.getContext("2d");
    if (!ctx) return;
    host.appendChild(canvas);

    const wanted = Math.max(10, parseInt(host.dataset.embers, 10) || 90);
    let width = 0;
    let height = 0;
    let dpr = 1;
    let embers = [];
    let pointerX = -1;

    function spawn(anywhere) {
      const firefly = Math.random() < 0.22; // drifts and blinks instead of rising fast
      const rgb = Math.random() < 0.05 ? GREEN : pick(COLOURS);
      const size = firefly ? 6 + Math.random() * 10 : 3 + Math.random() * 7;
      return {
        x: Math.random() * width,
        y: anywhere ? Math.random() * height : height + 10 + Math.random() * 40,
        vy: firefly ? 6 + Math.random() * 14 : 22 + Math.random() * 46,
        sway: 10 + Math.random() * 30,
        swaySpeed: 0.4 + Math.random() * 1.2,
        phase: Math.random() * Math.PI * 2,
        flicker: 2 + Math.random() * 6,
        size,
        life: 0,
        maxLife: firefly ? 7 + Math.random() * 8 : 4 + Math.random() * 6,
        firefly,
        img: sprite(rgb),
      };
    }

    function layout() {
      const rect = host.getBoundingClientRect();
      width = Math.max(1, rect.width);
      height = Math.max(1, rect.height);
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = Math.round(width * dpr);
      canvas.height = Math.round(height * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      // About `wanted` on a 1440x800 hero, fewer on a phone.
      const target = Math.round(wanted * Math.min(1, (width * height) / (1440 * 800)) + 12);
      embers = Array.from({ length: target }, () => spawn(true));
    }

    function draw(t, dt) {
      ctx.clearRect(0, 0, width, height);
      ctx.globalCompositeOperation = "lighter";
      for (let i = 0; i < embers.length; i++) {
        const e = embers[i];
        e.life += dt;
        e.y -= e.vy * dt;
        // A gust away from the pointer, when it's near.
        let push = 0;
        if (pointerX >= 0) {
          const d = e.x - pointerX;
          if (Math.abs(d) < 120) push = (Math.sign(d) || 1) * (120 - Math.abs(d)) * 0.6 * dt;
        }
        e.x += Math.sin(t * e.swaySpeed + e.phase) * e.sway * dt + push;

        const fadeIn = Math.min(1, e.life / 0.8);
        const fadeOut = Math.max(0, 1 - e.life / e.maxLife);
        const blink = e.firefly
          ? 0.35 + 0.65 * Math.max(0, Math.sin(t * e.flicker * 0.5 + e.phase))
          : 0.7 + 0.3 * Math.sin(t * e.flicker + e.phase);
        // Embers burn out as they rise: dimmer near the top.
        const heightFade = Math.min(1, Math.max(0.15, e.y / height + 0.25));
        const alpha = fadeIn * fadeOut * blink * heightFade;
        if (alpha > 0.01) {
          ctx.globalAlpha = alpha;
          const s = e.size * (e.firefly ? 2.6 : 2.2);
          ctx.drawImage(e.img, e.x - s / 2, e.y - s / 2, s, s);
        }
        if (e.life > e.maxLife || e.y < -30 || e.x < -40 || e.x > width + 40) {
          embers[i] = spawn(false);
        }
      }
      ctx.globalAlpha = 1;
      ctx.globalCompositeOperation = "source-over";
    }

    layout();
    if ("ResizeObserver" in window) new ResizeObserver(layout).observe(host);
    else window.addEventListener("resize", layout);

    if (reduceMotion) {
      draw(0, 0);
      return;
    }

    host.addEventListener("pointermove", (event) => {
      pointerX = event.clientX - host.getBoundingClientRect().left;
    });
    host.addEventListener("pointerleave", () => {
      pointerX = -1;
    });

    let visible = true;
    let raf = 0;
    let last = 0;
    function frame(now) {
      const dt = Math.min(0.05, (now - last) / 1000 || 0);
      last = now;
      draw(now / 1000, dt);
      raf = requestAnimationFrame(frame);
    }
    function sync() {
      const run = visible && !document.hidden;
      if (run && !raf) {
        last = performance.now();
        raf = requestAnimationFrame(frame);
      } else if (!run && raf) {
        cancelAnimationFrame(raf);
        raf = 0;
      }
    }
    if ("IntersectionObserver" in window) {
      new IntersectionObserver((entries) => {
        visible = entries[0].isIntersecting;
        sync();
      }).observe(host);
    }
    document.addEventListener("visibilitychange", sync);
    sync();
  }

  hosts.forEach(attach);
})();
