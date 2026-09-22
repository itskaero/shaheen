// Music library page (docs/DECISIONS.md ADR-095): a small player over two
// full-length clan anthem tracks, with a live Web Audio frequency
// visualizer — it only animates while a track is actually playing, and
// draws one static bar pattern instead under prefers-reduced-motion.
//
// Playback here is always user-initiated (a click on Play), so none of
// assets/js/audio.js's autoplay-block workaround is needed. One courtesy
// borrowed from it: starting a library track pauses the sitewide
// `#site-audio` element if it's playing, so two anthems never overlap.

(function () {
  const nowPlayingEl = document.getElementById("music-now-playing");
  const tracksEl = document.getElementById("music-tracks");
  if (!nowPlayingEl || !tracksEl) {
    return;
  }

  const TRACKS = [
    {
      title: "Anthem",
      subtitle: "Full-length version — HIGHER TOGETHER.",
      src: "assets/audio/anthem-full.mp3",
      cover: "assets/img/music/anthem-full.jpg",
    },
    {
      title: "بلندیوں کی جانب",
      subtitle: "Bulandiyon Ki Janab — towards the heights.",
      src: "assets/audio/bulandiyon-ki-janab.mp3",
      cover: "assets/img/music/bulandiyon-ki-janab.jpg",
    },
  ];

  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  nowPlayingEl.innerHTML = `
    <div class="music-disc" id="music-disc"><img id="music-cover" src="" alt="" /></div>
    <div class="music-visualizer">
      <canvas id="music-canvas" aria-hidden="true"></canvas>
      <h3 class="music-track-title" id="music-title"></h3>
      <p class="music-track-subtitle" id="music-subtitle"></p>
      <div class="music-transport">
        <button type="button" class="music-playpause" id="music-playpause" aria-label="Play">▶</button>
        <div class="music-progress">
          <div class="music-progress-track" id="music-progress-track" role="slider" aria-label="Seek" tabindex="0"><div class="music-progress-fill" id="music-progress-fill"></div></div>
          <span class="music-time" id="music-time">0:00 / 0:00</span>
        </div>
        <input type="range" class="music-volume" id="music-volume" min="0" max="100" value="80" aria-label="Volume" />
      </div>
    </div>`;

  const discEl = document.getElementById("music-disc");
  const coverEl = document.getElementById("music-cover");
  const canvas = document.getElementById("music-canvas");
  const canvasCtx = canvas.getContext("2d");
  const titleEl = document.getElementById("music-title");
  const subtitleEl = document.getElementById("music-subtitle");
  const playPauseEl = document.getElementById("music-playpause");
  const progressTrackEl = document.getElementById("music-progress-track");
  const progressFillEl = document.getElementById("music-progress-fill");
  const timeEl = document.getElementById("music-time");
  const volumeEl = document.getElementById("music-volume");

  const audio = new Audio();
  audio.id = "library-audio";
  audio.preload = "none";
  audio.volume = 0.8;
  audio.style.display = "none";
  document.body.appendChild(audio);

  // Courtesy (docs/DECISIONS.md ADR-073/ADR-095): never let the sitewide
  // background anthem play at the same time as a library track. A single
  // pause-on-click isn't enough — assets/js/audio.js arms its own
  // document-level click listener when its autoplay was blocked, and that
  // listener can fire right after this one (same click, bubbling to
  // document) and start it anyway. Watching #site-audio's own "play"
  // event catches that case too, not just the moment a library track
  // starts.
  function watchSiteAudio() {
    // assets/js/audio.js creates #site-audio from its own DOMContentLoaded
    // handler, which can still be pending when this script runs (both are
    // plain <script> tags near the end of <body>, so this one can execute
    // before the page has actually finished parsing) — look it up lazily
    // rather than once at module load, or this listener would silently
    // never attach.
    const siteAudio = document.getElementById("site-audio");
    if (siteAudio) {
      siteAudio.addEventListener("play", () => {
        if (!audio.paused) {
          siteAudio.pause();
        }
      });
    }
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", watchSiteAudio);
  } else {
    watchSiteAudio();
  }

  let currentIndex = 0;
  let audioCtx = null;
  let analyser = null;
  let freqData = null;
  let rafId = null;

  function formatTime(seconds) {
    if (!isFinite(seconds) || seconds < 0) {
      return "0:00";
    }
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${String(s).padStart(2, "0")}`;
  }

  function resizeCanvas() {
    const rect = canvas.getBoundingClientRect();
    canvas.width = Math.max(1, Math.round(rect.width));
    canvas.height = Math.max(1, Math.round(rect.height));
  }

  function drawBars(values) {
    const { width, height } = canvas;
    const bars = 32;
    const gap = 3;
    const barWidth = width / bars - gap;
    canvasCtx.clearRect(0, 0, width, height);
    const gradient = canvasCtx.createLinearGradient(0, height, 0, 0);
    gradient.addColorStop(0, "#1fb87e");
    gradient.addColorStop(1, "#ffd23f");
    canvasCtx.fillStyle = gradient;
    for (let i = 0; i < bars; i++) {
      const h = Math.max(3, values[i] * height);
      canvasCtx.fillRect(i * (barWidth + gap), height - h, barWidth, h);
    }
  }

  function drawStaticBars() {
    drawBars(new Array(32).fill(0.12));
  }

  function draw() {
    rafId = requestAnimationFrame(draw);
    if (!analyser || !freqData) {
      return;
    }
    analyser.getByteFrequencyData(freqData);
    const bars = 32;
    const step = Math.max(1, Math.floor(freqData.length / bars));
    const values = [];
    for (let i = 0; i < bars; i++) {
      values.push((freqData[i * step] || 0) / 255);
    }
    drawBars(values);
  }

  function stopDraw() {
    if (rafId) {
      cancelAnimationFrame(rafId);
      rafId = null;
    }
  }

  function ensureAudioGraph() {
    if (audioCtx) {
      return;
    }
    const AudioContextCtor = window.AudioContext || window.webkitAudioContext;
    if (!AudioContextCtor) {
      return;
    }
    audioCtx = new AudioContextCtor();
    const sourceNode = audioCtx.createMediaElementSource(audio);
    analyser = audioCtx.createAnalyser();
    analyser.fftSize = 128;
    freqData = new Uint8Array(analyser.frequencyBinCount);
    sourceNode.connect(analyser);
    analyser.connect(audioCtx.destination);
  }

  function renderTrackCards() {
    tracksEl.innerHTML = TRACKS.map(
      (track, i) => `
      <div class="card music-track-card${i === currentIndex ? " is-active" : ""}" data-index="${i}" tabindex="0" role="button" aria-label="Play ${escapeHtml(track.title)}">
        <div class="music-track-cover"><img src="${track.cover}" alt="" /></div>
        <div class="music-track-card-info">
          <div class="music-track-card-title">${escapeHtml(track.title)}</div>
          <div class="music-track-card-meta">${escapeHtml(track.subtitle)}</div>
        </div>
      </div>`
    ).join("");
    tracksEl.querySelectorAll(".music-track-card").forEach((card) => {
      const play = () => loadTrack(Number(card.dataset.index), true);
      card.addEventListener("click", play);
      card.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          play();
        }
      });
    });
  }

  function pauseVisuals() {
    discEl.classList.remove("is-playing");
    playPauseEl.textContent = "▶";
    playPauseEl.setAttribute("aria-label", "Play");
    stopDraw();
    // The static bar pattern itself isn't animation — only the rAF loop
    // in draw() is, and that's what prefers-reduced-motion should stop.
    drawStaticBars();
  }

  function play() {
    const siteAudio = document.getElementById("site-audio");
    if (siteAudio && !siteAudio.paused) {
      siteAudio.pause();
    }
    ensureAudioGraph();
    if (audioCtx && audioCtx.state === "suspended") {
      audioCtx.resume();
    }
    audio
      .play()
      .then(() => {
        discEl.classList.add("is-playing");
        playPauseEl.textContent = "⏸";
        playPauseEl.setAttribute("aria-label", "Pause");
        if (!reduced) {
          stopDraw();
          draw();
        }
      })
      .catch(() => {
        // Playback failed (e.g. interrupted by a rapid track switch) —
        // pauseVisuals below already reflects the paused state.
      });
  }

  function loadTrack(index, autoplay) {
    currentIndex = index;
    const track = TRACKS[index];
    coverEl.src = track.cover;
    coverEl.alt = track.title;
    titleEl.textContent = track.title;
    subtitleEl.textContent = track.subtitle;
    audio.src = track.src;
    progressFillEl.style.width = "0%";
    timeEl.textContent = "0:00 / 0:00";
    renderTrackCards();
    if (autoplay) {
      play();
    } else {
      pauseVisuals();
    }
  }

  playPauseEl.addEventListener("click", () => {
    if (audio.paused) {
      play();
    } else {
      audio.pause();
    }
  });

  audio.addEventListener("pause", pauseVisuals);
  audio.addEventListener("ended", pauseVisuals);

  audio.addEventListener("timeupdate", () => {
    if (audio.duration) {
      progressFillEl.style.width = `${(audio.currentTime / audio.duration) * 100}%`;
    }
    timeEl.textContent = `${formatTime(audio.currentTime)} / ${formatTime(audio.duration)}`;
  });

  progressTrackEl.addEventListener("click", (event) => {
    if (!audio.duration) {
      return;
    }
    const rect = progressTrackEl.getBoundingClientRect();
    const ratio = Math.min(1, Math.max(0, (event.clientX - rect.left) / rect.width));
    audio.currentTime = ratio * audio.duration;
  });

  volumeEl.addEventListener("input", () => {
    audio.volume = Number(volumeEl.value) / 100;
  });

  window.addEventListener("resize", () => {
    resizeCanvas();
    if (audio.paused) {
      drawStaticBars();
    }
  });

  resizeCanvas();
  loadTrack(0, false);
})();
