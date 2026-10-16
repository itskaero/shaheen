// Kinetic type for the recruitment trailers: text that enters, lives and
// leaves like part of the shot rather than a caption on top of it.
//
// Entrances:  "rise"  words arrive one by one out of a blur
//             "slam"  the line crashes in large with an RGB split
//             "slice" a blade of light cuts across and reveals the line
// While held: a slow push toward the camera with a settling 3D tilt, one
//             light sweep across the letters, accent words glowing on beats.
// Exit:       the line flies toward the camera into blur.
//
// `text` marks accent words with asterisks: "Find your *people.*"
import React from "react";
import { useCurrentFrame } from "remotion";
import { easeIn, prog } from "../anim";
import { FONT } from "../theme";
import { RECRUIT_BEATS } from "./beats";

export type Variant = "rise" | "slam" | "slice";
type Beats = ReadonlyArray<readonly [number, number]>;
type Word = { text: string; accent: boolean };

const FPS = 30;
const CREAM = "#fbf9d8";
const GREEN = "#3df26e";
const sec = (t: number) => Math.round(t * FPS);

function parse(text: string): Word[] {
  let open = false;
  return text.split(" ").map((raw) => {
    let t = raw;
    let accent = open;
    if (t.startsWith("*")) {
      accent = open = true;
      t = t.slice(1);
    }
    if (t.endsWith("*")) {
      t = t.slice(0, -1);
      open = false;
    }
    return { text: t, accent };
  });
}

function pulseAt(frame: number, beats: Beats): number {
  const t = frame / FPS;
  let best = 0;
  for (const [bt, st] of beats) {
    if (bt > t) break;
    const age = t - bt;
    if (age < 0.4) best = Math.max(best, (0.4 + 0.6 * (st / 9)) * Math.exp(-age * 8));
  }
  return best;
}

export const Kinetic: React.FC<{
  text: string;
  at: number; // seconds
  out?: number; // seconds
  size: number;
  variant?: Variant;
  accent?: string;
  beats?: Beats;
}> = ({ text, at, out, size, variant = "rise", accent = GREEN, beats = RECRUIT_BEATS }) => {
  const frame = useCurrentFrame();
  const a = sec(at);
  if (frame < a - 1 || (out !== undefined && frame > sec(out) + 9)) return null;
  const words = parse(text);
  const life = frame - a;
  const pulse = pulseAt(frame, beats);

  // Held: slow push and a tilt that settles. Exit: fly through the camera.
  const q = out === undefined ? 0 : prog(frame, sec(out), 8, easeIn);
  const push = 1 + Math.min(Math.max(life, 0), 120) / 120 * 0.06;
  const tilt = (1 - prog(frame, a, 16)) * (variant === "slam" ? 0 : 16);

  const glow = (isAccent: boolean) =>
    isAccent
      ? `0 0 ${16 + pulse * 40}px ${accent}${Math.round((0.45 + pulse * 0.45) * 255).toString(16).padStart(2, "0")}, 0 6px 30px rgba(0,0,0,0.85)`
      : "0 6px 34px rgba(0,0,0,0.9), 0 0 2px rgba(0,0,0,0.9)";

  const base: React.CSSProperties = {
    fontFamily: FONT.sans,
    fontWeight: 900,
    fontSize: size,
    lineHeight: 0.98,
    letterSpacing: -size * 0.025,
    textTransform: "uppercase",
    textAlign: "center",
    whiteSpace: "nowrap",
  };

  const wordStyle = (w: Word, i: number): React.CSSProperties => {
    if (variant === "rise") {
      const p = prog(frame, a + i * 3, 10);
      return {
        display: "inline-block",
        transform: `translateY(${(1 - p) * 0.55}em) scale(${0.88 + 0.12 * p})`,
        filter: p < 1 ? `blur(${(1 - p) * 12}px)` : undefined,
        opacity: Math.min(1, p * 1.4),
      };
    }
    if (variant === "slam") {
      const p = prog(frame, a, 5);
      return {
        display: "inline-block",
        transform: `scale(${1.9 - 0.9 * p})`,
        filter: p < 1 ? `blur(${(1 - p) * 16}px)` : undefined,
        opacity: Math.min(1, p * 2),
      };
    }
    return { display: "inline-block" };
  };

  const line = (opts: { color?: string; sheen?: boolean; noShadow?: boolean }) => (
    <div style={{ ...base, display: "flex", flexWrap: "wrap", justifyContent: "center", columnGap: "0.24em" }}>
      {words.map((w, i) => (
        <span
          key={i}
          style={{
            ...wordStyle(w, i),
            color: opts.color ?? (w.accent ? accent : CREAM),
            textShadow: opts.noShadow ? "none" : glow(w.accent),
          }}
        >
          {w.text}
        </span>
      ))}
    </div>
  );

  // Slice: a diagonal reveal led by a glowing blade.
  const sliceP = variant === "slice" ? prog(frame, a, 10) : 1;
  const edge = -15 + sliceP * 130; // percent
  const clip = variant === "slice" && sliceP < 1 ? `polygon(0 0, ${edge + 8}% 0, ${edge - 8}% 100%, 0 100%)` : undefined;

  // One light sweep across the letters once everything has arrived.
  const sweepStart = a + (variant === "rise" ? words.length * 3 + 6 : 8);
  const sweep = prog(frame, sweepStart, 16);
  const showSweep = frame >= sweepStart && sweep < 1;

  // Slam: a short RGB split.
  const split = variant === "slam" && life < 9 ? (9 - life) / 9 : 0;

  return (
    <div style={{ perspective: 1100, opacity: 1 - q, filter: q > 0 ? `blur(${q * 14}px)` : undefined }}>
      <div
        style={{
          position: "relative",
          transform: `scale(${push * (1 + q * 0.45)}) rotateX(${tilt}deg)`,
          transformOrigin: "50% 60%",
        }}
      >
        {split > 0 && (
          <>
            <div style={{ position: "absolute", inset: 0, transform: `translate(${-split * 14}px, ${split * 3}px)`, mixBlendMode: "screen", opacity: split * 0.8 }}>
              {line({ color: "#ff2e3a", noShadow: true })}
            </div>
            <div style={{ position: "absolute", inset: 0, transform: `translate(${split * 14}px, ${-split * 3}px)`, mixBlendMode: "screen", opacity: split * 0.8 }}>
              {line({ color: "#2ef2ff", noShadow: true })}
            </div>
          </>
        )}
        <div style={{ clipPath: clip }}>{line({})}</div>
        {showSweep && (
          <div
            aria-hidden
            style={{
              position: "absolute",
              inset: 0,
              clipPath: clip,
              WebkitMaskImage: `linear-gradient(105deg, transparent ${sweep * 140 - 30}%, #000 ${sweep * 140 - 15}%, transparent ${sweep * 140}%)`,
              maskImage: `linear-gradient(105deg, transparent ${sweep * 140 - 30}%, #000 ${sweep * 140 - 15}%, transparent ${sweep * 140}%)`,
              mixBlendMode: "screen",
              opacity: 0.75,
            }}
          >
            {line({ color: "#ffffff", noShadow: true })}
          </div>
        )}
        {variant === "slice" && sliceP < 1 && (
          <div
            aria-hidden
            style={{
              position: "absolute",
              top: "-12%",
              bottom: "-12%",
              left: `${edge}%`,
              width: 6,
              transform: "skewX(-9deg)",
              background: "#ffffff",
              boxShadow: `0 0 18px 6px ${accent}, 0 0 50px 14px ${accent}88`,
              opacity: Math.sin(sliceP * Math.PI),
            }}
          />
        )}
      </div>
    </div>
  );
};
