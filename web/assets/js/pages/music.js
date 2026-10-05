// Music library (docs/DECISIONS.md ADR-118, replacing ADR-095's player).
//
// One <audio> element plays the library; the page moves on the beat. Each
// track has a beat map made offline by scripts/beat_map.py (tempo, every
// beat, its strength, bar starts and a loudness curve), so the background
// video, the cover and the visualizer pulse exactly on the music's beats —
// also after a seek — rather than on guesses from live audio. A Web Audio
// analyser still draws the live spectrum.
//
// Calm by default: nothing animates until something plays; under
// prefers-reduced-motion the video stays on its poster, beats change only
// colour, never scale. The visualizer and beat loop run only while playing
// and the tab is visible.
(function () {
  const TRACKS = [
    { slug: "brawlistan", title: "Brawlistan", subtitle: "The network's theme", group: "originals" },
    { slug: "urooj", title: "Urooj", urdu: "عروج", subtitle: "The rise", group: "originals" },
    { slug: "zarb", title: "Zarb!", urdu: "ضرب!", subtitle: "The strike", group: "originals" },
    { slug: "zarb-2", title: "Zarb! II", urdu: "ضرب!", subtitle: "The strike, second cut", group: "originals" },
    { slug: "anthem-full", title: "Anthem", subtitle: "Higher together", group: "shaheen", cover: "anthem-full" },
    { slug: "bulandiyon-ki-janab", title: "Bulandiyon Ki Janab", urdu: "بلندیوں کی جانب", subtitle: "Towards the heights", group: "shaheen", cover: "bulandiyon-ki-janab" },
  ];
  const ARTIST = "BRAWLISTAN";
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const $ = (id) => document.getElementById(id);

  const els = {
    video: $("music-video"),
    cover: $("music-cover"),
    coverWebp: $("music-cover-webp"),
    title: $("music-title"),
    subtitle: $("music-subtitle"),
    bpm: $("music-bpm"),
    state: $("music-state"),
    count: $("music-count"),
    play: $("music-play"),
    prev: $("music-prev"),
    next: $("music-next"),
    progress: $("music-progress"),
    current: $("music-current"),
    duration: $("music-duration"),
    volume: $("music-volume"),
    viz: $("music-viz"),
    originals: $("music-originals"),
    shaheen: $("music-shaheen"),
  };
  if (!els.play) return;

  const root = document.documentElement;
  const audio = new Audio();
  audio.preload = "metadata";
  audio.volume = 0.8;

  let index = 0;
  let beatMap = null; // the current track's beats.json
  let beatCursor = 0;
  let beat = 0; // 0..1 pulse, decays between beats
  let raf = 0;
  let seeking = false;
  let audioCtx = null;
  let analyser = null;
  let freq = null;
  const beatMaps = new Map();

  // ---- the background video: 720p on small screens or data saver ----
  function startVideo() {
    if (!els.video || reduced) return; // reduced motion: the poster stays
    const saveData = navigator.connection && navigator.connection.saveData;
    const small = Math.min(screen.width, screen.height) < 900 || window.innerWidth < 900;
    if (!els.video.src) {
      els.video.src = `assets/video/music-loop-${small || saveData ? "720" : "1080"}.mp4`;
    }
    const play = els.video.play();
    if (play) play.catch(() => {}); // autoplay refused: the poster is fine
  }

  // ---- library list ----
  function format(seconds) {
    if (!isFinite(seconds)) return "0:00";
    const s = Math.floor(seconds);
    return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
  }

  function coverStem(track) {
    return `assets/img/music/${track.cover || track.slug}`;
  }

  function renderList() {
    for (const group of ["originals", "shaheen"]) {
      const list = els[group];
      list.innerHTML = TRACKS.map((t, i) =>
        t.group !== group
          ? ""
          : `<li>
              <button type="button" class="music-row" data-i="${i}" aria-label="Play ${escapeHtml(t.title)}">
                <span class="music-row-num" aria-hidden="true"><span class="num">${String(i + 1).padStart(2, "0")}</span><span class="music-eq"><i></i><i></i><i></i></span></span>
                <img class="music-row-cover" src="${coverStem(t)}.jpg" alt="" width="48" height="48" loading="lazy" />
                <span class="music-row-text">
                  <strong>${escapeHtml(t.title)}${t.urdu ? ` <span class="music-urdu" lang="ur">${escapeHtml(t.urdu)}</span>` : ""}</strong>
                  <span class="muted">${escapeHtml(t.subtitle)}</span>
                </span>
                <span class="music-row-bpm muted num" data-bpm="${t.slug}"></span>
                <span class="music-row-time muted num" data-time="${t.slug}"></span>
              </button>
            </li>`
      ).join("");
    }
    document.querySelectorAll(".music-row").forEach((row) =>
      row.addEventListener("click", () => {
        const i = Number(row.dataset.i);
        if (i === index && !audio.paused) audio.pause();
        else select(i, true);
      })
    );
  }

  function markRows() {
    document.querySelectorAll(".music-row").forEach((row) => {
      const on = Number(row.dataset.i) === index;
      row.classList.toggle("is-current", on);
      row.classList.toggle("is-playing", on && !audio.paused);
      row.setAttribute("aria-current", on ? "true" : "false");
    });
  }

  // ---- beat maps ----
  function loadBeatMap(slug) {
    if (!beatMaps.has(slug)) {
      beatMaps.set(
        slug,
        fetch(`assets/audio/${slug}.beats.json`)
          .then((r) => (r.ok ? r.json() : null))
          .catch(() => null)
      );
    }
    return beatMaps.get(slug);
  }

  function annotateRow(slug, map) {
    if (!map) return;
    const bpm = document.querySelector(`[data-bpm="${slug}"]`);
    const time = document.querySelector(`[data-time="${slug}"]`);
    if (bpm) bpm.textContent = `${Math.round(map.bpm)} BPM`;
    if (time) time.textContent = format(map.duration);
  }

  // First beat at or after `time` (binary search): re-syncs instantly after a seek.
  function beatIndexAt(time) {
    const beats = beatMap ? beatMap.beats : [];
    let lo = 0;
    let hi = beats.length;
    while (lo < hi) {
      const mid = (lo + hi) >> 1;
      if (beats[mid] < time) lo = mid + 1;
      else hi = mid;
    }
    return lo;
  }

  // ---- selecting and playing ----
  function select(i, autoplay) {
    index = (i + TRACKS.length) % TRACKS.length;
    const t = TRACKS[index];
    audio.src = `assets/audio/${t.slug}.mp3`;
    els.title.innerHTML = `${escapeHtml(t.title)}${t.urdu ? ` <span class="music-urdu" lang="ur">${escapeHtml(t.urdu)}</span>` : ""}`;
    els.subtitle.textContent = `${t.subtitle} · ${t.group === "shaheen" ? "SHAHEEN" : ARTIST}`;
    els.cover.src = `${coverStem(t)}.jpg`;
    if (els.coverWebp) els.coverWebp.srcset = `${coverStem(t)}.webp`;
    els.count.textContent = `Track ${index + 1} of ${TRACKS.length}`;
    els.bpm.textContent = "— BPM";
    beatMap = null;
    loadBeatMap(t.slug).then((map) => {
      if (TRACKS[index] !== t) return;
      beatMap = map;
      beatCursor = beatIndexAt(audio.currentTime);
      els.bpm.textContent = map ? `${Math.round(map.bpm)} BPM` : "— BPM";
    });
    if ("mediaSession" in navigator) {
      navigator.mediaSession.metadata = new MediaMetadata({
        title: t.title,
        artist: t.group === "shaheen" ? "SHAHEEN" : ARTIST,
        album: "BRAWLISTAN Music",
        artwork: [{ src: new URL(`${coverStem(t)}.jpg`, document.baseURI).href, sizes: "512x512", type: "image/jpeg" }],
      });
    }
    markRows();
    if (autoplay) play();
  }

  function ensureAnalyser() {
    if (audioCtx || !window.AudioContext) return;
    try {
      audioCtx = new AudioContext();
      const source = audioCtx.createMediaElementSource(audio);
      analyser = audioCtx.createAnalyser();
      analyser.fftSize = 256;
      analyser.smoothingTimeConstant = 0.78;
      freq = new Uint8Array(analyser.frequencyBinCount);
      source.connect(analyser);
      analyser.connect(audioCtx.destination);
    } catch {
      analyser = null; // playback still works without the live spectrum
    }
  }

  function play() {
    ensureAnalyser();
    if (audioCtx && audioCtx.state === "suspended") audioCtx.resume();
    const p = audio.play();
    if (p) p.catch(() => {});
  }

  // ---- the beat loop: runs only while playing and visible ----
  function latency() {
    // What we hear lags what the element reports by the output latency.
    return audioCtx ? (audioCtx.outputLatency || audioCtx.baseLatency || 0) : 0;
  }

  function onBeat(i) {
    const strength = beatMap.strength ? beatMap.strength[i] / 9 : 0.7;
    const downbeat = (i - (beatMap.downbeat_phase || 0)) % 4 === 0;
    beat = Math.min(1, 0.45 + strength * 0.4 + (downbeat ? 0.25 : 0));
    root.style.setProperty("--beat-hue", downbeat ? "1" : "0");
  }

  function frame() {
    raf = requestAnimationFrame(frame);
    const now = audio.currentTime - latency();
    if (beatMap) {
      const beats = beatMap.beats;
      while (beatCursor < beats.length && beats[beatCursor] <= now) {
        onBeat(beatCursor);
        beatCursor += 1;
      }
      const e = beatMap.energy;
      const energy = e ? (e.values[Math.min(e.values.length - 1, Math.floor(now * e.rate))] || 0) / 99 : 0.5;
      root.style.setProperty("--energy", energy.toFixed(3));
    }
    // Exponential decay: a quick hit that settles before the next beat.
    beat *= reduced ? 0.86 : 0.9;
    root.style.setProperty("--beat", beat.toFixed(3));
    drawViz();
    if (!seeking) {
      els.progress.value = audio.duration ? Math.round((audio.currentTime / audio.duration) * 1000) : 0;
      els.current.textContent = format(audio.currentTime);
    }
  }

  function startLoop() {
    if (!raf && !document.hidden) raf = requestAnimationFrame(frame);
  }

  function stopLoop() {
    cancelAnimationFrame(raf);
    raf = 0;
    beat = 0;
    root.style.setProperty("--beat", "0");
  }

  // ---- visualizer: live spectrum, mirrored, brightened on the beat ----
  const ctx = els.viz.getContext("2d");
  function sizeViz() {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const r = els.viz.getBoundingClientRect();
    els.viz.width = Math.max(1, Math.round(r.width * dpr));
    els.viz.height = Math.max(1, Math.round(r.height * dpr));
  }

  function drawViz(still) {
    const w = els.viz.width;
    const h = els.viz.height;
    ctx.clearRect(0, 0, w, h);
    const bars = 48;
    const gap = w / bars;
    if (analyser && freq && !still) analyser.getByteFrequencyData(freq);
    for (let b = 0; b < bars; b++) {
      // Mirror around the centre: bass in the middle.
      const k = Math.abs(b - (bars - 1) / 2) / (bars / 2);
      let v;
      if (still || !freq) v = 0.18 + 0.12 * Math.sin(b * 0.7) ** 2;
      else v = freq[Math.min(freq.length - 1, Math.floor(k * freq.length * 0.72))] / 255;
      v = Math.min(1, v * (0.85 + beat * 0.3));
      const bh = Math.max(2, v * h * 0.92);
      const x = b * gap + gap * 0.2;
      const grad = ctx.createLinearGradient(0, h, 0, h - bh);
      grad.addColorStop(0, `rgba(61, 242, 110, ${0.55 + beat * 0.35})`);
      grad.addColorStop(1, `rgba(240, 22, 140, ${0.35 + beat * 0.45})`);
      ctx.fillStyle = grad;
      ctx.beginPath();
      if (ctx.roundRect) ctx.roundRect(x, (h - bh) / 2, gap * 0.6, bh, gap * 0.3);
      else ctx.rect(x, (h - bh) / 2, gap * 0.6, bh);
      ctx.fill();
    }
  }

  // ---- wiring ----
  audio.addEventListener("play", () => {
    document.body.classList.add("is-playing");
    els.play.setAttribute("aria-label", "Pause");
    els.state.textContent = "Playing";
    beatCursor = beatIndexAt(audio.currentTime);
    startVideo();
    startLoop();
    markRows();
  });
  audio.addEventListener("pause", () => {
    document.body.classList.remove("is-playing");
    els.play.setAttribute("aria-label", "Play");
    els.state.textContent = "Paused";
    stopLoop();
    drawViz(true);
    markRows();
  });
  audio.addEventListener("seeked", () => {
    beatCursor = beatIndexAt(audio.currentTime);
  });
  audio.addEventListener("loadedmetadata", () => {
    els.duration.textContent = format(audio.duration);
  });
  audio.addEventListener("ended", () => select(index + 1, true));

  els.play.addEventListener("click", () => (audio.paused ? play() : audio.pause()));
  els.prev.addEventListener("click", () => (audio.currentTime > 3 ? (audio.currentTime = 0) : select(index - 1, !audio.paused)));
  els.next.addEventListener("click", () => select(index + 1, !audio.paused));
  els.progress.addEventListener("input", () => {
    seeking = true;
    if (audio.duration) els.current.textContent = format((els.progress.value / 1000) * audio.duration);
  });
  els.progress.addEventListener("change", () => {
    if (audio.duration) audio.currentTime = (els.progress.value / 1000) * audio.duration;
    seeking = false;
  });
  els.volume.addEventListener("input", () => {
    audio.volume = els.volume.value / 100;
  });

  if ("mediaSession" in navigator) {
    navigator.mediaSession.setActionHandler("play", play);
    navigator.mediaSession.setActionHandler("pause", () => audio.pause());
    navigator.mediaSession.setActionHandler("previoustrack", () => select(index - 1, true));
    navigator.mediaSession.setActionHandler("nexttrack", () => select(index + 1, true));
  }

  document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
      cancelAnimationFrame(raf);
      raf = 0;
      if (els.video) els.video.pause();
    } else {
      if (!audio.paused) startLoop();
      startVideo();
    }
  });
  window.addEventListener("resize", () => {
    sizeViz();
    if (audio.paused) drawViz(true);
  });

  renderList();
  TRACKS.forEach((t) => loadBeatMap(t.slug).then((map) => annotateRow(t.slug, map)));
  select(0, false);
  sizeViz();
  drawViz(true);
  startVideo(); // the loop plays quietly behind the page; muted, so autoplay is allowed
})();
