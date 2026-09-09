// Rating-history trend chart — hand-rolled canvas, no charting library
// (CLAUDE.md: no unjustified dependency for what's ~150 lines of vanilla
// JS). Smoothed curve, gridlines + axis labels, a peak-rating overlay,
// a hover tooltip, and an animated draw-in on first render.

function drawSparkline(canvas, points) {
  if (!canvas || !points || points.length === 0) {
    return;
  }

  const clean = points.filter((p) => p.rating !== null && p.rating !== undefined);
  if (clean.length === 0) {
    return;
  }

  const ctx = canvas.getContext("2d");
  const pad = { top: 16, right: 16, bottom: 26, left: 46 };
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  let hoverIndex = -1;
  let tooltip = canvas.parentElement.querySelector(".chart-tooltip");
  if (!tooltip) {
    tooltip = document.createElement("div");
    tooltip.className = "chart-tooltip";
    tooltip.hidden = true;
    canvas.parentElement.style.position = "relative";
    canvas.parentElement.appendChild(tooltip);
  }

  function metrics() {
    const dpr = window.devicePixelRatio || 1;
    const width = canvas.clientWidth;
    const height = canvas.clientHeight;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    const ratings = clean.map((p) => p.rating);
    const peaks = clean.map((p) => p.peak_rating).filter((v) => v !== null && v !== undefined);
    const all = ratings.concat(peaks);
    let min = Math.min(...all);
    let max = Math.max(...all);
    const headroom = (max - min || 40) * 0.15;
    min -= headroom;
    max += headroom;

    const plotW = width - pad.left - pad.right;
    const plotH = height - pad.top - pad.bottom;
    const xStep = clean.length > 1 ? plotW / (clean.length - 1) : 0;

    const toX = (i) => pad.left + i * xStep;
    const toY = (v) => pad.top + plotH - ((v - min) / (max - min)) * plotH;

    return { width, height, plotW, plotH, min, max, toX, toY };
  }

  function smoothPath(ctx2, xs, ys) {
    ctx2.moveTo(xs[0], ys[0]);
    for (let i = 0; i < xs.length - 1; i++) {
      const mx = (xs[i] + xs[i + 1]) / 2;
      const my = (ys[i] + ys[i + 1]) / 2;
      ctx2.quadraticCurveTo(xs[i], ys[i], mx, my);
    }
    ctx2.lineTo(xs[xs.length - 1], ys[ys.length - 1]);
  }

  function shortDate(iso) {
    return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric" });
  }

  function render(progress) {
    const m = metrics();
    ctx.clearRect(0, 0, m.width, m.height);

    // gridlines + y-axis labels
    const gridLines = 4;
    ctx.font = "11px Poppins, sans-serif";
    ctx.fillStyle = "rgba(234, 246, 239, 0.45)";
    ctx.strokeStyle = "rgba(57, 255, 176, 0.1)";
    ctx.lineWidth = 1;
    for (let g = 0; g <= gridLines; g++) {
      const value = m.min + ((m.max - m.min) * g) / gridLines;
      const y = m.toY(value);
      ctx.beginPath();
      ctx.moveTo(pad.left, y);
      ctx.lineTo(m.width - pad.right, y);
      ctx.stroke();
      ctx.textAlign = "right";
      ctx.textBaseline = "middle";
      ctx.fillText(Math.round(value).toLocaleString(), pad.left - 8, y);
    }

    // x-axis labels: first, middle, last
    ctx.textAlign = "center";
    ctx.textBaseline = "top";
    [0, Math.floor((clean.length - 1) / 2), clean.length - 1].forEach((i, idx, arr) => {
      if (idx > 0 && arr[idx - 1] === i) return;
      ctx.fillText(shortDate(clean[i].captured_at), m.toX(i), m.height - pad.bottom + 8);
    });

    const shownCount = Math.max(2, Math.round(clean.length * progress));
    const shown = clean.slice(0, shownCount);
    const xs = shown.map((_, i) => m.toX(i));
    const ys = shown.map((p) => m.toY(p.rating));

    // peak-rating overlay (dashed gold)
    const peakYs = shown.map((p) => m.toY(p.peak_rating ?? p.rating));
    ctx.save();
    ctx.setLineDash([4, 5]);
    ctx.strokeStyle = "rgba(255, 210, 63, 0.65)";
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    smoothPath(ctx, xs, peakYs);
    ctx.stroke();
    ctx.restore();

    // area fill under rating curve
    ctx.beginPath();
    smoothPath(ctx, xs, ys);
    ctx.lineTo(xs[xs.length - 1], m.toY(m.min));
    ctx.lineTo(xs[0], m.toY(m.min));
    ctx.closePath();
    const fill = ctx.createLinearGradient(0, pad.top, 0, m.height - pad.bottom);
    fill.addColorStop(0, "rgba(57, 255, 176, 0.28)");
    fill.addColorStop(1, "rgba(57, 255, 176, 0)");
    ctx.fillStyle = fill;
    ctx.fill();

    // rating curve, glowing
    ctx.beginPath();
    smoothPath(ctx, xs, ys);
    ctx.strokeStyle = "#39ffb0";
    ctx.lineWidth = 2.25;
    ctx.shadowColor = "rgba(57, 255, 176, 0.85)";
    ctx.shadowBlur = 9;
    ctx.stroke();
    ctx.shadowBlur = 0;

    // points
    shown.forEach((p, i) => {
      ctx.beginPath();
      ctx.arc(xs[i], ys[i], i === hoverIndex ? 4 : 2.5, 0, Math.PI * 2);
      ctx.fillStyle = i === hoverIndex ? "#ffd23f" : "#eaf6ef";
      ctx.fill();
    });

    // hover guide line
    if (hoverIndex >= 0 && hoverIndex < shown.length) {
      const x = xs[hoverIndex];
      ctx.beginPath();
      ctx.setLineDash([3, 4]);
      ctx.strokeStyle = "rgba(234, 246, 239, 0.3)";
      ctx.lineWidth = 1;
      ctx.moveTo(x, pad.top);
      ctx.lineTo(x, m.height - pad.bottom);
      ctx.stroke();
      ctx.setLineDash([]);
    }

    return m;
  }

  function showTooltip(index, m) {
    const p = clean[index];
    const x = m.toX(index);
    const y = m.toY(p.rating);
    tooltip.innerHTML = `<strong>${p.rating.toLocaleString()}</strong><span>${shortDate(p.captured_at)}</span>`;
    tooltip.style.left = `${x}px`;
    tooltip.style.top = `${Math.max(y - 12, 10)}px`;
    tooltip.hidden = false;
  }

  function hideTooltip() {
    tooltip.hidden = true;
  }

  function handleMove(clientX, clientY) {
    const rect = canvas.getBoundingClientRect();
    const m = metrics();
    const relX = clientX - rect.left;
    if (relX < pad.left - 10 || relX > m.width - pad.right + 10 || clientY - rect.top > m.height) {
      hoverIndex = -1;
      hideTooltip();
      render(1);
      return;
    }
    let nearest = 0;
    let nearestDist = Infinity;
    clean.forEach((_, i) => {
      const d = Math.abs(m.toX(i) - relX);
      if (d < nearestDist) {
        nearestDist = d;
        nearest = i;
      }
    });
    hoverIndex = nearest;
    render(1);
    showTooltip(nearest, m);
  }

  canvas.addEventListener("mousemove", (e) => handleMove(e.clientX, e.clientY));
  canvas.addEventListener("mouseleave", () => {
    hoverIndex = -1;
    hideTooltip();
    render(1);
  });
  canvas.addEventListener(
    "touchstart",
    (e) => {
      const t = e.touches[0];
      if (t) handleMove(t.clientX, t.clientY);
    },
    { passive: true }
  );

  window.addEventListener("resize", () => render(1));

  if (reduced) {
    render(1);
    return;
  }

  const duration = 900;
  const start = performance.now();
  function frame(now) {
    const progress = Math.min(1, (now - start) / duration);
    render(1 - Math.pow(1 - progress, 3));
    if (progress < 1) {
      requestAnimationFrame(frame);
    }
  }
  requestAnimationFrame(frame);
}
