import React, { createContext, useContext } from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { clamp, easeOut, prog, rand } from "../anim";
import { C, HEIGHT, WIDTH } from "../theme";

/** Beat pulse of the soundtrack at the current global frame (0..1). */
export const PulseContext = createContext(0);
export const usePulse = () => useContext(PulseContext);

/** Rising embers and red fireflies, like the site's embers.js. */
export const Embers: React.FC<{ count?: number; seed?: number; speed?: number; opacity?: number; green?: boolean }> = ({
  count = 60,
  seed = 1,
  speed = 1,
  opacity = 1,
  green = false,
}) => {
  const frame = useCurrentFrame();
  const pulse = usePulse();
  return (
    <AbsoluteFill style={{ pointerEvents: "none", opacity }}>
      {Array.from({ length: count }, (_, i) => {
        const r1 = rand(seed * 100 + i);
        const r2 = rand(seed * 200 + i);
        const r3 = rand(seed * 300 + i);
        const vy = (1.2 + r2 * 3.2) * speed * (1 + pulse * 0.8);
        const travel = HEIGHT + 200;
        const y = HEIGHT + 60 - ((frame * vy + r3 * travel) % travel);
        const x = r1 * WIDTH + Math.sin((frame + i * 37) / (18 + r2 * 20)) * 30;
        const size = 2 + r3 * 5;
        const isGreen = green && i % 9 === 0;
        const col = isGreen ? C.green : r2 > 0.6 ? C.ember : r2 > 0.25 ? C.red : C.amber;
        const twinkle = 0.45 + 0.55 * Math.abs(Math.sin((frame + i * 13) / (6 + r1 * 9)));
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: x,
              top: y,
              width: size,
              height: size,
              borderRadius: "50%",
              background: col,
              boxShadow: `0 0 ${8 + size * 3}px ${2 + size}px ${col}`,
              opacity: twinkle * (0.55 + pulse * 0.45),
            }}
          />
        );
      })}
    </AbsoluteFill>
  );
};

/** Radial speed lines bursting from a point at frame `at`. */
export const SpeedBurst: React.FC<{ at: number; dur?: number; color?: string; cx?: number; cy?: number; count?: number; seed?: number }> = ({
  at,
  dur = 12,
  color = C.amber,
  cx = WIDTH / 2,
  cy = HEIGHT / 2,
  count = 46,
  seed = 3,
}) => {
  const frame = useCurrentFrame();
  const p = (frame - at) / dur;
  if (p < 0 || p > 1) return null;
  const e = easeOut(p);
  return (
    <svg width={WIDTH} height={HEIGHT} style={{ position: "absolute", inset: 0, pointerEvents: "none" }}>
      {Array.from({ length: count }, (_, i) => {
        const a = (i / count) * Math.PI * 2 + rand(seed + i) * 0.12;
        const r0 = 160 + rand(seed + i * 3) * 260 + e * 700;
        const len = (120 + rand(seed + i * 7) * 420) * (1 - p);
        return (
          <line
            key={i}
            x1={cx + Math.cos(a) * r0}
            y1={cy + Math.sin(a) * r0}
            x2={cx + Math.cos(a) * (r0 + len)}
            y2={cy + Math.sin(a) * (r0 + len)}
            stroke={i % 5 === 0 ? C.red : color}
            strokeWidth={1.5 + rand(seed + i * 11) * 4}
            strokeLinecap="round"
            opacity={(1 - p) * 0.9}
          />
        );
      })}
    </svg>
  );
};

/** Horizontal motion streaks, for whip transitions. */
export const Streaks: React.FC<{ at: number; dur?: number; dir?: 1 | -1; color?: string; seed?: number }> = ({
  at,
  dur = 10,
  dir = 1,
  color = C.ember,
  seed = 5,
}) => {
  const frame = useCurrentFrame();
  const p = (frame - at) / dur;
  if (p < 0 || p > 1) return null;
  return (
    <AbsoluteFill style={{ pointerEvents: "none", overflow: "hidden" }}>
      {Array.from({ length: 22 }, (_, i) => {
        const y = rand(seed + i) * HEIGHT;
        const w = 300 + rand(seed + i * 2) * 900;
        const x = dir * (-w + p * (WIDTH + w * 2) * (0.7 + rand(seed + i * 4) * 0.6)) + (dir < 0 ? WIDTH : 0);
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              top: y,
              left: dir > 0 ? x : undefined,
              right: dir < 0 ? -x + WIDTH : undefined,
              width: w,
              height: 2 + rand(seed + i * 9) * 5,
              background: `linear-gradient(${dir > 0 ? 90 : 270}deg, transparent, ${i % 3 ? color : C.cream})`,
              opacity: Math.sin(p * Math.PI) * 0.85,
            }}
          />
        );
      })}
    </AbsoluteFill>
  );
};

/** A short full-frame flash. */
export const Flash: React.FC<{ at: number; dur?: number; color?: string; max?: number }> = ({ at, dur = 8, color = "#fff", max = 0.85 }) => {
  const frame = useCurrentFrame();
  const o = interpolate(frame, [at, at + 1, at + dur], [0, max, 0], clamp);
  if (o <= 0) return null;
  return <AbsoluteFill style={{ background: color, opacity: o, mixBlendMode: "screen", pointerEvents: "none" }} />;
};

/** Film grain + vignette, always on top. */
export const Finish: React.FC = () => {
  const frame = useCurrentFrame();
  const seed = Math.floor(frame / 2) % 50;
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <AbsoluteFill style={{ background: "radial-gradient(ellipse at center, transparent 55%, rgba(0,0,0,0.62) 100%)" }} />
      <svg width={WIDTH} height={HEIGHT} style={{ position: "absolute", inset: 0, opacity: 0.07, mixBlendMode: "overlay" }}>
        <filter id={`grain${seed}`}>
          <feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="2" seed={seed} stitchTiles="stitch" />
          <feColorMatrix type="saturate" values="0" />
        </filter>
        <rect width="100%" height="100%" filter={`url(#grain${seed})`} />
      </svg>
    </AbsoluteFill>
  );
};

/** Diagonal Pakistan-flag ribbon (green and white), used sparingly. */
export const FlagRibbon: React.FC<{ progress: number; top?: number; angle?: number; opacity?: number }> = ({
  progress,
  top = 820,
  angle = -8,
  opacity = 0.9,
}) => (
  <div
    style={{
      position: "absolute",
      left: -200,
      top,
      width: (WIDTH + 400) * progress,
      height: 46,
      transform: `rotate(${angle}deg)`,
      transformOrigin: "left center",
      opacity,
      display: "flex",
      flexDirection: "column",
      filter: "drop-shadow(0 0 18px rgba(1,65,28,0.6))",
    }}
  >
    <div style={{ height: 10, background: C.cream }} />
    <div style={{ flex: 1, background: `linear-gradient(90deg, #0b5a2b, ${C.pkGreen})` }} />
  </div>
);

/** Small uppercase chip, e.g. "ILLUSTRATIVE VALUES". */
export const Tag: React.FC<{ children: React.ReactNode; color?: string; style?: React.CSSProperties; enter?: number }> = ({
  children,
  color = C.amber,
  style,
  enter = 0,
}) => {
  const frame = useCurrentFrame();
  const p = prog(frame, enter, 10);
  return (
    <div
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 10,
        padding: "8px 16px",
        borderRadius: 999,
        border: `1.5px solid ${color}`,
        color,
        background: "rgba(10,6,6,0.82)",
        fontFamily: "'Inter', sans-serif",
        fontWeight: 700,
        fontSize: 20,
        letterSpacing: 2.5,
        textTransform: "uppercase",
        opacity: p,
        transform: `translateY(${(1 - p) * 12}px)`,
        ...style,
      }}
    >
      {children}
    </div>
  );
};
