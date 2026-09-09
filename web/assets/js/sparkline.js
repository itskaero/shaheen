// Minimal hand-rolled canvas line chart for rating history — no charting
// library/CDN dependency, just enough to show a trend at a glance.

function drawSparkline(canvas, points) {
  if (!canvas || points.length === 0) {
    return;
  }

  const ctx = canvas.getContext("2d");
  const dpr = window.devicePixelRatio || 1;
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  canvas.width = width * dpr;
  canvas.height = height * dpr;
  ctx.scale(dpr, dpr);

  const padding = 12;
  const values = points.map((p) => p.rating).filter((v) => v !== null && v !== undefined);
  if (values.length === 0) {
    return;
  }
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;

  const xStep = (width - padding * 2) / Math.max(points.length - 1, 1);
  const toXY = (index, rating) => {
    const x = padding + index * xStep;
    const y = height - padding - ((rating - min) / span) * (height - padding * 2);
    return [x, y];
  };

  ctx.clearRect(0, 0, width, height);

  // fill under the line
  ctx.beginPath();
  points.forEach((p, i) => {
    const [x, y] = toXY(i, p.rating ?? min);
    if (i === 0) {
      ctx.moveTo(x, y);
    } else {
      ctx.lineTo(x, y);
    }
  });
  ctx.lineTo(padding + (points.length - 1) * xStep, height - padding);
  ctx.lineTo(padding, height - padding);
  ctx.closePath();
  ctx.fillStyle = "rgba(212, 175, 55, 0.12)";
  ctx.fill();

  // the line itself
  ctx.beginPath();
  points.forEach((p, i) => {
    const [x, y] = toXY(i, p.rating ?? min);
    if (i === 0) {
      ctx.moveTo(x, y);
    } else {
      ctx.lineTo(x, y);
    }
  });
  ctx.strokeStyle = "#d4af37";
  ctx.lineWidth = 2;
  ctx.stroke();

  // dots
  points.forEach((p, i) => {
    const [x, y] = toXY(i, p.rating ?? min);
    ctx.beginPath();
    ctx.arc(x, y, 2.5, 0, Math.PI * 2);
    ctx.fillStyle = "#e8e1cf";
    ctx.fill();
  });
}
