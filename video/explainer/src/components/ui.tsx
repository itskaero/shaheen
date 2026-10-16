import React from "react";
import { Img, interpolate, staticFile, useCurrentFrame } from "remotion";
import { clamp, easeInOut, prog } from "../anim";
import { C, FONT } from "../theme";

/** A browser window around a real screenshot of the site. */
export const Browser: React.FC<{ url: string; width: number; children: React.ReactNode; style?: React.CSSProperties }> = ({
  url,
  width,
  children,
  style,
}) => (
  <div
    style={{
      width,
      borderRadius: 18,
      overflow: "hidden",
      background: "#0d0909",
      border: `1px solid rgba(255,255,255,0.12)`,
      boxShadow: "0 40px 120px rgba(0,0,0,0.75), 0 0 0 1px rgba(255,106,31,0.08), 0 0 80px rgba(255,46,58,0.18)",
      ...style,
    }}
  >
    <div style={{ height: 46, display: "flex", alignItems: "center", gap: 10, padding: "0 18px", background: "#171111", borderBottom: "1px solid rgba(255,255,255,0.07)" }}>
      {["#ff5f57", "#febc2e", "#28c840"].map((c) => (
        <span key={c} style={{ width: 13, height: 13, borderRadius: "50%", background: c, opacity: 0.85 }} />
      ))}
      <div
        style={{
          marginLeft: 18,
          flex: 1,
          maxWidth: 720,
          height: 30,
          borderRadius: 999,
          background: "rgba(255,255,255,0.06)",
          display: "flex",
          alignItems: "center",
          gap: 10,
          padding: "0 16px",
          fontFamily: FONT.sans,
          fontSize: 17,
          color: C.muted,
        }}
      >
        <svg width="13" height="15" viewBox="0 0 13 15"><rect x="1" y="6" width="11" height="8" rx="2" fill={C.muted} /><path d="M3.5 6V4.5a3 3 0 0 1 6 0V6" stroke={C.muted} strokeWidth="1.6" fill="none" /></svg>
        <span style={{ color: C.cream }}>{url}</span>
      </div>
    </div>
    <div style={{ position: "relative", overflow: "hidden" }}>{children}</div>
  </div>
);

/** A screenshot, sized by width. */
export const Shot: React.FC<{ name: string; width: number; style?: React.CSSProperties }> = ({ name, width, style }) => (
  <Img src={staticFile(`shots/${name}.png`)} style={{ width, display: "block", ...style }} />
);

type Key = { f: number; x: number; y: number };

/** Animated pointer: moves through keyframes, clicks ripple. */
export const Cursor: React.FC<{ keys: Key[]; clicks?: number[]; appear?: number; vanish?: number }> = ({ keys, clicks = [], appear = 0, vanish }) => {
  const frame = useCurrentFrame();
  if (frame < appear || (vanish !== undefined && frame > vanish + 6)) return null;
  const xs = keys.map((k) => k.x);
  const ys = keys.map((k) => k.y);
  const fs = keys.map((k) => k.f);
  const x = fs.length > 1 ? interpolate(frame, fs, xs, { ...clamp, easing: easeInOut }) : xs[0];
  const y = fs.length > 1 ? interpolate(frame, fs, ys, { ...clamp, easing: easeInOut }) : ys[0];
  const press = clicks.some((c) => frame >= c && frame < c + 4);
  const o = Math.min(prog(frame, appear, 6), vanish === undefined ? 1 : 1 - prog(frame, vanish, 6));
  return (
    <div style={{ position: "absolute", left: 0, top: 0, pointerEvents: "none", opacity: o }}>
      {clicks.map((c) => {
        const a = frame - c;
        if (a < 0 || a > 18) return null;
        const p = a / 18;
        return (
          <div
            key={c}
            style={{
              position: "absolute",
              left: x - 10 - p * 50,
              top: y - 10 - p * 50,
              width: 20 + p * 100,
              height: 20 + p * 100,
              borderRadius: "50%",
              border: `3px solid ${C.amber}`,
              opacity: 1 - p,
            }}
          />
        );
      })}
      <svg
        width="44"
        height="52"
        viewBox="0 0 22 26"
        style={{ position: "absolute", left: x - 4, top: y - 2, transform: `scale(${press ? 0.85 : 1})`, transformOrigin: "4px 2px", filter: "drop-shadow(0 4px 10px rgba(0,0,0,0.7))" }}
      >
        <path d="M2 1 L2 21 L7.5 16 L11 24.5 L14.5 23 L11 14.8 L18.5 14.8 Z" fill="#fff" stroke="#111" strokeWidth="1.4" strokeLinejoin="round" />
      </svg>
    </div>
  );
};

/** Glowing outline that draws attention to a rectangle. */
export const Highlight: React.FC<{ x: number; y: number; w: number; h: number; start: number; end?: number; radius?: number; color?: string }> = ({
  x,
  y,
  w,
  h,
  start,
  end,
  radius = 14,
  color = C.ember,
}) => {
  const frame = useCurrentFrame();
  const p = prog(frame, start, 8);
  const q = end === undefined ? 0 : prog(frame, end, 6);
  const o = p * (1 - q);
  if (o <= 0) return null;
  const grow = (1 - p) * 30;
  return (
    <div
      style={{
        position: "absolute",
        left: x - grow,
        top: y - grow,
        width: w + grow * 2,
        height: h + grow * 2,
        borderRadius: radius,
        border: `3px solid ${color}`,
        boxShadow: `0 0 30px ${color}, inset 0 0 20px rgba(255,106,31,0.25)`,
        opacity: o,
      }}
    />
  );
};

export const Logo: React.FC<{ width: number; style?: React.CSSProperties }> = ({ width, style }) => (
  <Img src={staticFile("img/logo.png")} style={{ width, display: "block", ...style }} />
);
