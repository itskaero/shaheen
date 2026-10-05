// Music (docs/DECISIONS.md ADR-118, ADR-119): a full-screen night scene that
// moves with the music, and a cover picker.
//
// Each track has a beat map made offline by scripts/beat_map.py (tempo,
// every beat, its strength, bar starts, loudness). While a track plays:
//  - the background video is tempo-locked: its playback rate makes one pass
//    of the loop last a whole number of bars, and its position is
//    phase-locked to the beat grid (it restarts on a bar's first beat and is
//    nudged back if it drifts or after a seek);
//  - every beat sets --beat (a decaying 0..1 pulse; stronger on bar starts),
//    which kicks the video's zoom and light, the flash in the track's colour
//    and the two vertical lines; --energy follows the track's loudness.
// When nothing plays, the scene drifts slowly on its own. Under
// prefers-reduced-motion the video stays on its poster and beats only
// change light, never size.
(function () {
  const TRACKS = [
    {
      slug: "brawlistan", title: "Brawlistan", urdu: "یہ نام ہمارا", cover: "brawlistan",
      accent: "240, 22, 140", group: "originals",
      desc: "The network's anthem. A name we carry together — from every city to the top of the ladder.",
    },
    {
      slug: "urooj", title: "Urooj", urdu: "عروج", cover: "urooj",
      accent: "61, 242, 110", group: "originals",
      desc: "The rise. For the long climb, one placement match at a time.",
    },
    {
      slug: "zarb", title: "Zarb", urdu: "ضرب", cover: "zarb",
      accent: "255, 59, 59", group: "originals",
      desc: "The strike. Built for the final stock and the clutch read.",
    },
    {
      // The owner's covers name this upload "Pakistan" (both files were tagged ضرب!).
      slug: "zarb-2", title: "Pakistan", urdu: "پاکستان", cover: "pakistan",
      accent: "242, 193, 78", group: "originals",
      desc: "For the country behind every name on the board.",
    },
    {
      slug: "anthem-full", title: "Anthem", urdu: "", image: "anthem-full",
      accent: "61, 242, 110", group: "shaheen", desc: "SHAHEEN's anthem — higher together.",
    },
    {
      slug: "bulandiyon-ki-janab", title: "Bulandiyon Ki Janab", urdu: "بلندیوں کی جانب", image: "bulandiyon-ki-janab",
      accent: "242, 193, 78", group: "shaheen", desc: "Towards the heights. The founding team's second anthem.",
    },
  ];
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const $ = (id) => document.getElementById(id);
  const els = {
    video: $("music-video"), title: $("music-title"), urdu: $("music-urdu"), desc: $("music-desc"),
    bpm: $("music-bpm"), state: $("music-state"), play: $("music-play"), tracksBtn: $("music-tracks-btn"),
    progress: $("music-progress"), current: $("music-current"), duration: $("music-duration"),
    covers: $("music-covers"), shelf: $("music-shelf"), picker: $("music-picker"),
  };
  if (!els.play) return;

  const root = document.documentElement;
  const audio = new Audio();
  audio.preload = "metadata";
  audio.volume = 0.85;

  let index = 0;
  let beatMap = null;
  let beatCursor = 0;
  let beat = 0;
  let raf = 0;
  let seeking = false;
  let audioCtx = null;
  const beatMaps = new Map();

  const format = (s) => (isFinite(s) ? `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}` : "0:00");

  // ---- background video ----
  function ensureVideo() {
    if (!els.video || reduced || els.video.src) return;
    const small = window.innerWidth < 900 || (navigator.connection && navigator.connection.saveData);
    els.video.src = `assets/video/music-loop-${small ? "720" : "1080"}.mp4`;
    els.video.playbackRate = 0.6; // idle: a slow drift until something plays
    const p = els.video.play();
    if (p) p.catch(() => {});
  }

  // Lock the loop to the music: rate so one pass is a whole number of bars,
  // phase so each pass starts on a bar's first beat.
  function syncVideo(now) {
    const v = els.video;
    if (!v || reduced || !beatMap || !v.duration || v.readyState < 2) return;
    const bar = 240 / beatMap.bpm;
    const bars = Math.max(1, Math.round(v.duration / bar));
    const rate = Math.min(2, Math.max(0.5, v.duration / (bars * bar)));
    if (Math.abs(v.playbackRate - rate) > 0.002) v.playbackRate = rate;
    const anchor = beatMap.beats[beatMap.downbeat_phase || 0] || 0;
    const want = ((((now - anchor) * rate) % v.duration) + v.duration) % v.duration;
    let drift = v.currentTime - want;
    if (drift > v.duration / 2) drift -= v.duration;
    if (drift < -v.duration / 2) drift += v.duration;
    if (Math.abs(drift) > 0.12 && !v.seeking) v.currentTime = want;
  }

  // ---- beat maps ----
  function loadBeatMap(slug) {
    if (!beatMaps.has(slug)) {
      beatMaps.set(slug, fetch(`assets/audio/${slug}.beats.json`).then((r) => (r.ok ? r.json() : null)).catch(() => null));
    }
    return beatMaps.get(slug);
  }

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

  // ---- picker ----
  function art(t) {
    return t.cover ? `assets/img/music/cover-${t.cover}` : `assets/img/music/${t.image}`;
  }

  function renderPicker() {
    els.covers.innerHTML = TRACKS.map((t, i) =>
      t.group !== "originals" ? "" : `<li>
        <button type="button" class="music-cover" data-i="${i}" style="--track: ${t.accent}" aria-label="Play ${escapeHtml(t.title)}">
          <picture><source srcset="${art(t)}.webp" type="image/webp" /><img src="${art(t)}.jpg" alt="" width="714" height="483" loading="lazy" /></picture>
          <span class="music-cover-info">
            <span class="music-cover-num num">${String(i + 1).padStart(2, "0")}</span>
            <strong>${escapeHtml(t.title)}</strong>
            <span class="music-cover-meta num" data-meta="${t.slug}"></span>
          </span>
          <span class="music-cover-progress" aria-hidden="true"><span></span></span>
          <span class="music-cover-state" aria-hidden="true"><i></i><i></i><i></i></span>
        </button>
      </li>`).join("");
    els.shelf.innerHTML = TRACKS.map((t, i) =>
      t.group !== "shaheen" ? "" : `<li>
        <button type="button" class="music-shelf-row" data-i="${i}" style="--track: ${t.accent}" aria-label="Play ${escapeHtml(t.title)}">
          <img src="${art(t)}.jpg" alt="" width="56" height="56" loading="lazy" />
          <span><strong>${escapeHtml(t.title)}</strong><span class="muted">${escapeHtml(t.desc)}</span></span>
          <span class="music-cover-meta muted num" data-meta="${t.slug}"></span>
        </button>
      </li>`).join("");
    document.querySelectorAll("[data-i]").forEach((el) =>
      el.addEventListener("click", () => {
        const i = Number(el.dataset.i);
        if (i === index && !audio.paused) audio.pause();
        else {
          select(i, true);
          window.scrollTo({ top: 0, behavior: reduced ? "auto" : "smooth" });
        }
      })
    );
  }

  function markPicker() {
    document.querySelectorAll("[data-i]").forEach((el) => {
      const on = Number(el.dataset.i) === index;
      el.classList.toggle("is-current", on);
      el.classList.toggle("is-playing", on && !audio.paused);
      el.setAttribute("aria-current", on ? "true" : "false");
    });
  }

  // ---- selecting and playing ----
  function select(i, autoplay) {
    index = (i + TRACKS.length) % TRACKS.length;
    const t = TRACKS[index];
    audio.src = `assets/audio/${t.slug}.mp3`;
    els.title.textContent = t.title;
    els.urdu.textContent = t.urdu || "";
    els.desc.textContent = t.desc;
    els.bpm.textContent = "— BPM";
    root.style.setProperty("--track", t.accent);
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
        artist: t.group === "shaheen" ? "SHAHEEN" : "BRAWLISTAN",
        album: "BRAWLISTAN Music",
        artwork: [{ src: new URL(`${art(t)}.jpg`, document.baseURI).href, type: "image/jpeg" }],
      });
    }
    markPicker();
    if (autoplay) play();
  }

  function play() {
    if (!audioCtx && window.AudioContext) {
      try {
        audioCtx = new AudioContext(); // for outputLatency: beats line up with what is heard
      } catch {
        audioCtx = null;
      }
    }
    ensureVideo();
    const p = audio.play();
    if (p) p.catch(() => {});
  }

  // ---- the beat loop: only while playing and visible ----
  const latency = () => (audioCtx ? audioCtx.outputLatency || audioCtx.baseLatency || 0 : 0);

  function onBeat(i) {
    const strength = beatMap.strength ? beatMap.strength[i] / 9 : 0.7;
    const downbeat = (i - (beatMap.downbeat_phase || 0)) % 4 === 0;
    beat = Math.min(1, 0.42 + strength * 0.38 + (downbeat ? 0.3 : 0));
    root.style.setProperty("--bar", downbeat ? "1" : "0");
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
      if (e) root.style.setProperty("--energy", ((e.values[Math.min(e.values.length - 1, Math.floor(now * e.rate))] || 0) / 99).toFixed(3));
      syncVideo(now);
    }
    beat *= 0.9;
    root.style.setProperty("--beat", beat.toFixed(3));
    if (!seeking && audio.duration) {
      const fraction = audio.currentTime / audio.duration;
      els.progress.value = Math.round(fraction * 1000);
      els.current.textContent = format(audio.currentTime);
      const bar = document.querySelector(".music-cover.is-current .music-cover-progress span");
      if (bar) bar.style.width = `${(fraction * 100).toFixed(2)}%`;
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

  // ---- wiring ----
  audio.addEventListener("play", () => {
    document.body.classList.add("is-playing");
    els.play.setAttribute("aria-label", "Pause");
    els.play.querySelector(".music-play-label").textContent = "Pause";
    els.state.textContent = "Now playing";
    beatCursor = beatIndexAt(audio.currentTime);
    startLoop();
    markPicker();
  });
  audio.addEventListener("pause", () => {
    document.body.classList.remove("is-playing");
    els.play.setAttribute("aria-label", "Play");
    els.play.querySelector(".music-play-label").textContent = "Play";
    els.state.textContent = "Paused";
    stopLoop();
    if (els.video && !reduced) els.video.playbackRate = 0.6;
    markPicker();
  });
  audio.addEventListener("seeked", () => {
    beatCursor = beatIndexAt(audio.currentTime);
  });
  audio.addEventListener("loadedmetadata", () => {
    els.duration.textContent = format(audio.duration);
  });
  audio.addEventListener("ended", () => select(index + 1, true));

  els.play.addEventListener("click", () => (audio.paused ? play() : audio.pause()));
  els.tracksBtn.addEventListener("click", () => els.picker.scrollIntoView({ behavior: reduced ? "auto" : "smooth" }));
  els.progress.addEventListener("input", () => {
    seeking = true;
    if (audio.duration) els.current.textContent = format((els.progress.value / 1000) * audio.duration);
  });
  els.progress.addEventListener("change", () => {
    if (audio.duration) audio.currentTime = (els.progress.value / 1000) * audio.duration;
    seeking = false;
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
      if (els.video && els.video.src) els.video.play().catch(() => {});
    }
  });

  renderPicker();
  TRACKS.forEach((t) =>
    loadBeatMap(t.slug).then((map) => {
      if (!map) return;
      document.querySelectorAll(`[data-meta="${t.slug}"]`).forEach((el) => {
        el.textContent = `${Math.round(map.bpm)} BPM · ${format(map.duration)}`;
      });
    })
  );
  select(0, false);
  ensureVideo();
})();
