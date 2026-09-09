// Cursor-follow highlight on .card/.stat — a vanilla CSS/JS take on the
// reactbits "spotlight card" effect. Sets --mx/--my custom properties that
// style.css's .card::after / .stat::after read to position a radial glow.
// rAF-batched so it costs nothing beyond the current pointer position.

(function () {
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    return;
  }

  let pending = null;
  let ticking = false;

  function apply() {
    ticking = false;
    if (!pending) {
      return;
    }
    const { clientX, clientY } = pending;
    document.querySelectorAll(".card, .stat").forEach((el) => {
      const rect = el.getBoundingClientRect();
      const x = clientX - rect.left;
      const y = clientY - rect.top;
      if (x >= 0 && x <= rect.width && y >= 0 && y <= rect.height) {
        el.style.setProperty("--mx", `${x}px`);
        el.style.setProperty("--my", `${y}px`);
      }
    });
  }

  document.addEventListener("pointermove", (event) => {
    pending = event;
    if (!ticking) {
      ticking = true;
      requestAnimationFrame(apply);
    }
  });
})();
