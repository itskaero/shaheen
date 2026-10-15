// Site-wide background music, beat-synced (docs/DECISIONS.md ADR-133).
//
// Plays assets/audio/bg.mp3 on a loop on every page except the Music page
// (it has its own player). The beat map (bg.beats.json, scripts/beat_map.py)
// drives the visuals, so they land exactly on the beat even after a loop:
// - CSS variables on <html>: --bl-beat (a pulse, 1 on a beat, decaying to 0)
//   and --bl-bass (the track's loudness, smoothed, 0..1);
// - window.BLBeat, the same numbers for canvas code (embers.js);
// - a "bl:beat" event per beat: { strength 0..1, downbeat, bpm }.
//
// Browsers block autoplay with sound, so it starts on the visitor's first
// click, key or tap if it couldn't start by itself. The mute choice and the
// position are remembered across pages (localStorage, best effort).
(function () {
  "use strict";

  if (document.body.dataset.page === "music") return;

  const SRC = "assets/audio/bg.mp3";
  const BEATS = "assets/audio/bg.beats.json";
  const VOLUME = 0.38;
  const MUTE_KEY = "brawlistan-bg-muted";
  const POSITION_KEY = "brawlistan-bg-position";
  const BEAT_DECAY_S = 0.3;

  const root = document.documentElement;
  const BEAT = (window.BLBeat = { beat: 0, bass: 0, playing: false, bpm: 0 });

  function read(key) {
    try {
      return localStorage.getItem(key);
    } catch {
      return null;
    }
  }
  function write(key, value) {
    try {
      localStorage.setItem(key, value);
    } catch {
      /* storage blocked: the choice just won't persist */
    }
  }

  // ---- the audio element and the toggle ----
  const audio = new Audio();
  audio.src = SRC;
  audio.loop = true;
  audio.preload = "auto";
  audio.volume = VOLUME;

  const saved = parseFloat(read(POSITION_KEY) || "0");
  if (saved > 0) {
    audio.addEventListener(
      "loadedmetadata",
      () => {
        if (saved < audio.duration) audio.currentTime = saved;
      },
      { once: true }
    );
  }

  const button = document.createElement("button");
  button.type = "button";
  button.className = "bl-music";
  button.innerHTML =
    '<span class="bl-music-bars" aria-hidden="true"><i></i><i></i><i></i><i></i></span><span class="bl-music-label">Music</span>';
  document.body.appendChild(button);

  let muted = read(MUTE_KEY) === "1";

  function render() {
    const off = muted || audio.paused;
    button.classList.toggle("is-off", off);
    button.setAttribute("aria-pressed", String(!off));
    button.setAttribute("aria-label", off ? "Play background music" : "Mute background music");
    button.title = off ? "Play music" : "Mute music";
  }

  function play() {
    const attempt = audio.play();
    if (attempt && attempt.catch) {
      attempt.then(render).catch(() => {
        button.classList.add("is-pending");
        armFirstInteraction();
        render();
      });
    }
  }

  let armed = false;
  function armFirstInteraction() {
    if (armed) return;
    armed = true;
    const start = (event) => {
      ["pointerdown", "keydown", "touchstart"].forEach((t) => document.removeEventListener(t, start, true));
      button.classList.remove("is-pending");
      // The toggle handles its own click.
      if (event && button.contains(event.target)) return;
      if (!muted) audio.play().then(render).catch(() => {});
    };
    ["pointerdown", "keydown", "touchstart"].forEach((t) => document.addEventListener(t, start, true));
  }

  button.addEventListener("click", () => {
    // Waiting for a first interaction counts as "off": the click plays.
    if (muted || audio.paused) {
      muted = false;
      write(MUTE_KEY, "0");
      button.classList.remove("is-pending");
      play();
    } else {
      muted = true;
      write(MUTE_KEY, "1");
      audio.pause();
    }
    render();
  });

  let lastSaved = 0;
  audio.addEventListener("timeupdate", () => {
    const now = Date.now();
    if (now - lastSaved > 2000) {
      lastSaved = now;
      write(POSITION_KEY, audio.currentTime.toFixed(2));
    }
  });
  window.addEventListener("pagehide", () => write(POSITION_KEY, audio.currentTime.toFixed(2)));

  // ---- the beat engine ----
  let map = null;
  let next = 0; // index of the next beat to fire
  let lastTime = 0;
  let raf = 0;
  let lastFrame = 0;

  fetch(BEATS)
    .then((r) => (r.ok ? r.json() : null))
    .then((m) => {
      if (!m || !Array.isArray(m.beats)) return;
      map = m;
      BEAT.bpm = m.bpm || 0;
      next = firstBeatAfter(audio.currentTime);
    })
    .catch(() => {
      /* no beat map: the music still plays, the visuals stay calm */
    });

  function firstBeatAfter(t) {
    const beats = map.beats;
    let lo = 0;
    let hi = beats.length;
    while (lo < hi) {
      const mid = (lo + hi) >> 1;
      if (beats[mid] <= t) lo = mid + 1;
      else hi = mid;
    }
    return lo;
  }

  function loudness(t) {
    const e = map.energy;
    if (!e || !e.values || !e.values.length) return 0;
    const i = Math.min(e.values.length - 1, Math.max(0, Math.floor(t * e.rate)));
    return e.values[i] / 99;
  }

  function fire(i) {
    const strength = (map.strength[i] || 0) / 9;
    const downbeat = (((i - (map.downbeat_phase || 0)) % 4) + 4) % 4 === 0;
    const kick = Math.min(1, 0.25 + strength * 0.75 + (downbeat ? 0.15 : 0));
    if (strength > 0.1) BEAT.beat = Math.max(BEAT.beat, kick);
    window.dispatchEvent(new CustomEvent("bl:beat", { detail: { strength, downbeat, bpm: BEAT.bpm } }));
  }

  function frame(now) {
    const dt = Math.min(0.1, (now - lastFrame) / 1000 || 0);
    lastFrame = now;
    let target = 0;
    if (map && !audio.paused) {
      const t = audio.currentTime;
      // A loop back to the start or a seek: find our place again.
      if (t < lastTime - 0.05 || t > lastTime + 1) next = firstBeatAfter(t - 0.001);
      while (next < map.beats.length && map.beats[next] <= t) fire(next++);
      lastTime = t;
      target = loudness(t);
    }
    BEAT.bass += (target - BEAT.bass) * Math.min(1, dt * 10);
    BEAT.beat = Math.max(0, BEAT.beat - dt / BEAT_DECAY_S);
    root.style.setProperty("--bl-bass", BEAT.bass.toFixed(3));
    root.style.setProperty("--bl-beat", BEAT.beat.toFixed(3));
    const settled = audio.paused && BEAT.bass < 0.005 && BEAT.beat === 0;
    raf = settled || document.hidden ? 0 : requestAnimationFrame(frame);
  }

  function wake() {
    BEAT.playing = !audio.paused;
    if (!raf && !document.hidden) {
      lastFrame = performance.now();
      raf = requestAnimationFrame(frame);
    }
  }
  audio.addEventListener("play", wake);
  audio.addEventListener("pause", wake);
  audio.addEventListener("pause", render);
  audio.addEventListener("play", render);
  document.addEventListener("visibilitychange", wake);

  render();
  if (!muted) play();
})();
