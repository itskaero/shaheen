// BRAWLISTAN's site palette (web/assets/css/arena.css, ADR-130/132) and the
// explainer's timeline. All times are seconds of video, picked on the beats of
// the soundtrack window (src/beats.ts).
export const FPS = 30;
export const WIDTH = 1920;
export const HEIGHT = 1080;
export const DURATION_S = 64.17;

export const C = {
  bg: "#0a0606",
  panel: "#151010",
  panelHi: "#1d1514",
  line: "rgba(255,255,255,0.09)",
  red: "#ff2e3a",
  ember: "#ff6a1f",
  amber: "#ffc283",
  gold: "#e9b949",
  green: "#3df26e",
  pkGreen: "#01411c",
  cream: "#f4ead8",
  white: "#ffffff",
  muted: "rgba(244,234,216,0.62)",
  discord: "#5865f2",
} as const;

export const FONT = {
  sans: "'Inter', system-ui, sans-serif",
  serif: "'Instrument Serif', Georgia, serif",
  urdu: "'Noto Nastaliq Urdu', serif",
  mono: "'JetBrains Mono', 'DejaVu Sans Mono', monospace",
};

export const FIRE = `linear-gradient(90deg, ${C.red}, ${C.ember})`;

// Scene starts (seconds). Each lands on a downbeat or a musical change.
export const SCENES = {
  hook: 0,
  meet: 5.782,
  link: 12.725,
  city: 27.725,
  clan: 40.426,
  cta: 52.547,
  end: DURATION_S,
} as const;

export const SITE = "brawlistan.rekorex.online";

export const f = (seconds: number) => Math.round(seconds * FPS);
