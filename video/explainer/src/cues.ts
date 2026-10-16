// Sound-design cues: [video seconds, sfx name (public/sfx), volume].
// Each sits on its scene's own animation frame (scene start + local frame / 30).
import { SCENES } from "./theme";

type Cue = readonly [number, string, number];
const at = (scene: keyof typeof SCENES, frame: number) => SCENES[scene] + frame / 30;
const many = (scene: keyof typeof SCENES, frames: number[], name: string, vol: number): Cue[] =>
  frames.map((fr) => [at(scene, fr), name, vol]);
const range = (from: number, to: number, step: number) => Array.from({ length: Math.floor((to - from) / step) + 1 }, (_, i) => from + i * step);

export const CUES: Cue[] = [
  // 1. Hook
  [at("hook", 2), "sweep", 0.45],
  [at("hook", 36), "impact", 0.9],
  [at("hook", 84), "whoosh", 0.6],
  [at("hook", 87), "hit", 0.55],
  [at("hook", 122), "hit", 0.4],
  [at("hook", 136), "whoosh", 0.5],
  [at("hook", 139), "boom", 0.75],
  // 2. Meet the site
  [at("meet", 0), "whoosh-long", 0.5],
  [at("meet", 62), "whoosh", 0.5],
  ...many("meet", [70, 87, 104, 121, 139, 155], "tick", 0.55),
  // 3. Link your profile
  [at("link", 0), "hit", 0.5],
  [at("link", 34), "whoosh", 0.4],
  [at("link", 45), "whoosh", 0.35],
  [at("link", 86), "click", 0.6],
  [at("link", 98), "whoosh", 0.45],
  ...many("link", range(112, 124, 3), "key", 0.45),
  [at("link", 150), "click", 0.6],
  [at("link", 160), "sweep", 0.4],
  [at("link", 219), "whoosh", 0.45],
  [at("link", 256), "click", 0.6],
  ...many("link", range(262, 276, 2), "key", 0.4),
  [at("link", 286), "click", 0.65],
  [at("link", 292), "success", 0.6],
  [at("link", 331), "hit", 0.5],
  ...many("link", [346, 364, 381, 398, 412], "tick", 0.45),
  // 4. City Wars
  [at("city", 0), "whoosh-long", 0.55],
  ...many("city", range(0, 32, 4), "tick", 0.3),
  [at("city", 35), "impact", 0.9],
  [at("city", 78), "whoosh", 0.5],
  ...many("city", range(92, 101, 3), "key", 0.4),
  [at("city", 132), "click", 0.55],
  [at("city", 142), "sweep", 0.4],
  [at("city", 165), "whoosh", 0.5],
  ...many("city", [186, 191, 196, 201, 206], "tick", 0.45),
  [at("city", 232), "hit", 0.55],
  [at("city", 251), "whoosh", 0.5],
  [at("city", 258), "sweep", 0.35],
  // 5. Clan Wars
  [at("clan", 0), "impact", 0.9],
  ...many("clan", [35, 44, 52, 61, 69], "hit", 0.35),
  [at("clan", 113), "whoosh", 0.5],
  ...many("clan", [121, 139, 156, 173], "hit", 0.55),
  [at("clan", 219), "whoosh", 0.5],
  [at("clan", 242), "sweep", 0.35],
  [at("clan", 290), "whoosh", 0.5],
  [at("clan", 294), "hit", 0.6],
  // 6. Call to action
  ...many("cta", [0, 33, 68, 103], "hit", 0.55),
  [at("cta", 133), "whoosh", 0.55],
  [at("cta", 137), "boom", 0.85],
  ...many("cta", range(172, 196, 3), "key", 0.35),
  [at("cta", 312), "impact", 0.7],
];
