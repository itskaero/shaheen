import { Easing, interpolate } from "remotion";
import { BEATS } from "./beats";
import { FPS } from "./theme";

export const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
export const easeOut = Easing.bezier(0.16, 1, 0.3, 1);
export const easeIn = Easing.bezier(0.7, 0, 0.84, 0);
export const easeInOut = Easing.bezier(0.65, 0, 0.35, 1);

/** 0→1 between two frames with an ease, clamped. */
export function prog(frame: number, start: number, dur: number, ease = easeOut): number {
  return interpolate(frame, [start, start + dur], [0, 1], { ...clamp, easing: ease });
}

/** Beat pulse at a global frame: 1 on a beat (scaled by strength), decaying. */
export function beatPulse(globalFrame: number): number {
  const t = globalFrame / FPS;
  let best = 0;
  for (const [bt, s] of BEATS) {
    if (bt > t) break;
    const age = t - bt;
    if (age < 0.35) best = Math.max(best, (0.45 + 0.55 * (s / 9)) * Math.exp(-age * 9));
  }
  return best;
}

/** Deterministic pseudo-random in [0,1). */
export function rand(seed: number): number {
  const x = Math.sin(seed * 12.9898 + 78.233) * 43758.5453;
  return x - Math.floor(x);
}

/** Decaying shake offset after an impact frame. */
export function shake(frame: number, at: number, power = 18, seed = 1): { x: number; y: number } {
  const age = frame - at;
  if (age < 0 || age > 14) return { x: 0, y: 0 };
  const k = power * Math.exp(-age * 0.32);
  return { x: (rand(seed + age) - 0.5) * 2 * k, y: (rand(seed + age + 99) - 0.5) * 2 * k };
}
