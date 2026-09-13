// Site-wide background audio — the clan anthem (docs/DECISIONS.md ADR-073).
//
// Self-contained on purpose: no dependency on config.js/api.js, so it works
// identically on every page regardless of what else that page loads.
//
// Browsers block unconditional autoplay-with-sound (Chrome/Firefox/Safari
// all require some prior engagement on the origin) — there is no way around
// that, only the standard fallback every site with background audio uses:
// try to play immediately, and if it's blocked, start on the visitor's very
// first interaction with the page instead.

const AUDIO_SRC = "assets/audio/anthem.mp3";
const AUDIO_VOLUME = 0.55;
const MUTE_KEY = "shaheen-audio-muted";
const POSITION_KEY = "shaheen-audio-position";
const POSITION_SAVE_INTERVAL_MS = 3000;

function readStorage(key) {
  try {
    return window.localStorage.getItem(key);
  } catch {
    // Storage disabled (private mode, locked-down context, etc.) — treat as unset.
    return null;
  }
}

function writeStorage(key, value) {
  try {
    window.localStorage.setItem(key, value);
  } catch {
    // Best-effort only — a visitor's mute choice or resume position just
    // won't persist across pages if storage is unavailable.
  }
}

function buildToggleIcon(muted) {
  // Inline SVG, not an emoji glyph — crisp at 1x and colorable with
  // currentColor to match the site palette exactly.
  if (muted) {
    return `
      <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M4 9v6h4l5 5V4L8 9H4Z" fill="currentColor" stroke="none" />
        <line x1="16" y1="9" x2="21" y2="15" />
        <line x1="21" y1="9" x2="16" y2="15" />
      </svg>`;
  }
  return `
    <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M4 9v6h4l5 5V4L8 9H4Z" fill="currentColor" stroke="none" />
      <path d="M16.5 8.5a5 5 0 0 1 0 7" />
      <path d="M19 6a9 9 0 0 1 0 12" />
    </svg>`;
}

function initSiteAudio() {
  const audio = document.createElement("audio");
  audio.id = "site-audio";
  audio.src = AUDIO_SRC;
  audio.loop = true;
  audio.preload = "auto";
  audio.volume = AUDIO_VOLUME;
  audio.style.display = "none";
  document.body.appendChild(audio);

  const savedPosition = parseFloat(readStorage(POSITION_KEY) || "0");
  if (savedPosition > 0) {
    audio.addEventListener(
      "loadedmetadata",
      () => {
        if (savedPosition < audio.duration) {
          audio.currentTime = savedPosition;
        }
      },
      { once: true }
    );
  }

  const button = document.createElement("button");
  button.className = "audio-toggle";
  button.type = "button";
  button.setAttribute("aria-label", "Toggle background music");
  document.body.appendChild(button);

  let userMuted = readStorage(MUTE_KEY) === "1";

  function render() {
    const showAsMuted = userMuted || audio.paused;
    button.innerHTML = buildToggleIcon(showAsMuted);
    button.classList.toggle("is-muted", showAsMuted);
  }

  function tryPlay() {
    const playPromise = audio.play();
    if (playPromise && typeof playPromise.catch === "function") {
      playPromise
        .then(() => {
          button.classList.remove("is-pending");
          render();
        })
        .catch(() => {
          // Autoplay blocked — wait for the visitor's first interaction.
          button.classList.add("is-pending");
          render();
          armInteractionFallback();
        });
    } else {
      render();
    }
  }

  let fallbackArmed = false;
  function armInteractionFallback() {
    if (fallbackArmed) {
      return;
    }
    fallbackArmed = true;
    const start = () => {
      document.removeEventListener("click", start);
      document.removeEventListener("keydown", start);
      document.removeEventListener("touchstart", start);
      if (!userMuted) {
        audio.play().then(render).catch(() => {});
      }
      button.classList.remove("is-pending");
    };
    document.addEventListener("click", start, { once: true });
    document.addEventListener("keydown", start, { once: true });
    document.addEventListener("touchstart", start, { once: true });
  }

  button.addEventListener("click", () => {
    userMuted = !userMuted;
    writeStorage(MUTE_KEY, userMuted ? "1" : "0");
    if (userMuted) {
      audio.pause();
    } else {
      tryPlay();
    }
    render();
  });

  let lastSaved = 0;
  audio.addEventListener("timeupdate", () => {
    const now = Date.now();
    if (now - lastSaved > POSITION_SAVE_INTERVAL_MS) {
      lastSaved = now;
      writeStorage(POSITION_KEY, String(audio.currentTime));
    }
  });
  window.addEventListener("pagehide", () => {
    writeStorage(POSITION_KEY, String(audio.currentTime));
  });

  render();
  if (!userMuted) {
    tryPlay();
  }
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initSiteAudio);
} else {
  initSiteAudio();
}
