import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { clamp, easeOut, prog } from "../anim";
import { C, FONT } from "../theme";

export const DISPLAY: React.CSSProperties = {
  fontFamily: FONT.sans,
  fontWeight: 900,
  textTransform: "uppercase",
  letterSpacing: -2,
  lineHeight: 0.9,
  color: C.cream,
};

export const ACCENT: React.CSSProperties = {
  fontFamily: FONT.serif,
  fontStyle: "italic",
  fontWeight: 400,
  textTransform: "none",
  letterSpacing: -1,
  color: C.amber,
};

/** Text that rises out of a mask, with a slight skew settle. */
export const MaskUp: React.FC<{
  start: number;
  dur?: number;
  out?: number;
  outDur?: number;
  style?: React.CSSProperties;
  children: React.ReactNode;
}> = ({ start, dur = 10, out, outDur = 7, style, children }) => {
  const frame = useCurrentFrame();
  const p = prog(frame, start, dur);
  const q = out === undefined ? 0 : prog(frame, out, outDur, (t) => t * t);
  return (
    <span style={{ display: "inline-block", overflow: "hidden", verticalAlign: "bottom", paddingBottom: "0.08em", paddingTop: "0.04em" }}>
      <span
        style={{
          display: "inline-block",
          transform: `translateY(${(1 - p) * 110 - q * 110}%) skewY(${(1 - p) * 6}deg)`,
          ...style,
        }}
      >
        {children}
      </span>
    </span>
  );
};

/** Scale-down slam: big and blurred to crisp, on an impact frame. */
export const Slam: React.FC<{ at: number; from?: number; dur?: number; style?: React.CSSProperties; children: React.ReactNode }> = ({
  at,
  from = 2.4,
  dur = 7,
  style,
  children,
}) => {
  const frame = useCurrentFrame();
  if (frame < at) return null;
  const p = prog(frame, at, dur, easeOut);
  const scale = interpolate(p, [0, 1], [from, 1]);
  const blur = (1 - p) * 14;
  return (
    <div style={{ transform: `scale(${scale})`, filter: blur > 0.3 ? `blur(${blur}px)` : undefined, opacity: Math.min(1, p * 3), ...style }}>
      {children}
    </div>
  );
};

/** Types `text` from `start`, `cps` characters per second (at 30 fps). */
export function typed(frame: number, start: number, text: string, cps = 18): string {
  const n = Math.floor(Math.max(0, frame - start) * (cps / 30));
  return text.slice(0, n);
}

/** A number counting up from 0. */
export const CountUp: React.FC<{ to: number; start: number; dur?: number; style?: React.CSSProperties }> = ({ to, start, dur = 20, style }) => {
  const frame = useCurrentFrame();
  const v = Math.round(interpolate(frame, [start, start + dur], [0, to], { ...clamp, easing: easeOut }));
  return <span style={{ fontVariantNumeric: "tabular-nums", ...style }}>{v.toLocaleString("en-US")}</span>;
};
