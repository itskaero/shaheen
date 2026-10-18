// Scene 6 (52.5–64.2 s): call to action. The four real steps, then the logo
// and the site's address, ending on the track's last big hit.
import React from "react";
import { AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame } from "remotion";
import { clamp, easeOut, prog, shake } from "../anim";
import { Embers, Flash, SpeedBurst, Streaks, usePulse } from "../components/fx";
import { DISPLAY, Slam, typed } from "../components/type";
import { Logo } from "../components/ui";
import { C, FONT, SITE } from "../theme";

const STEPS = [
  { at: 0, n: "1", text: "Join the Discord", code: false },
  { at: 33, n: "2", text: "/link", code: true },
  { at: 68, n: "3", text: "/city set", code: true },
  { at: 103, n: "4", text: "Play ranked", code: false },
];
const LOGO = 137;
const END_HIT = 312;

export const Cta: React.FC = () => {
  const frame = useCurrentFrame();
  const pulse = usePulse();
  const s = shake(frame, LOGO, 26, 13);
  const stepsOut = prog(frame, LOGO - 6, 6);
  const fadeOut = interpolate(frame, [330, 348], [1, 0], clamp);
  const url = typed(frame, 172, SITE, 30);
  return (
    <AbsoluteFill style={{ background: C.bg, overflow: "hidden", opacity: fadeOut }}>
      {/* Steps */}
      {frame < LOGO && (
        <AbsoluteFill style={{ opacity: 1 - stepsOut }}>
          <AbsoluteFill style={{ opacity: 0.25 }}>
            <Img src={staticFile("img/hero-scene.jpg")} style={{ width: "100%", height: "100%", objectFit: "cover", filter: "blur(4px)" }} />
          </AbsoluteFill>
          <AbsoluteFill style={{ background: "linear-gradient(90deg, rgba(10,6,6,0.95), rgba(10,6,6,0.6))" }} />
          <div style={{ position: "absolute", left: 130, top: 150, fontFamily: FONT.sans, fontWeight: 800, fontSize: 30, letterSpacing: 10, color: C.amber, opacity: prog(frame, 0, 8) }}>
            GET STARTED
          </div>
          <div style={{ position: "absolute", left: 130, top: 230, display: "flex", flexDirection: "column", gap: 22 }}>
            {STEPS.map((st) => {
              const p = prog(frame, st.at, 8);
              const active = frame >= st.at && (STEPS.find((x) => x.at > st.at)?.at ?? LOGO) > frame;
              return (
                <div key={st.n} style={{ display: "flex", alignItems: "center", gap: 40, opacity: p * (active ? 1 : 0.42), transform: `translateX(${(1 - p) * 200}px) scale(${active ? 1 + pulse * 0.02 : 1})`, transformOrigin: "left center" }}>
                  <div style={{ width: 150, height: 150, borderRadius: 34, display: "grid", placeItems: "center", ...DISPLAY, fontSize: 100, color: "#fff", background: active ? `linear-gradient(135deg, ${C.red}, ${C.ember})` : "rgba(255,255,255,0.06)", boxShadow: active ? "0 0 60px rgba(255,46,58,0.55)" : "none" }}>
                    {st.n}
                  </div>
                  <div style={{ ...(st.code ? { fontFamily: FONT.mono, fontWeight: 700, fontSize: 120, color: C.amber, letterSpacing: -3 } : { ...DISPLAY, fontSize: 130 }) }}>{st.text}</div>
                </div>
              );
            })}
          </div>
        </AbsoluteFill>
      )}

      {/* Logo end card */}
      {frame >= LOGO && (
        <AbsoluteFill style={{ transform: `translate(${s.x}px, ${s.y}px)` }}>
          <AbsoluteFill style={{ transform: `scale(${1.15 - prog(frame, LOGO, 200, easeOut) * 0.1})` }}>
            <Img src={staticFile("img/warriors.jpg")} style={{ width: "100%", height: "100%", objectFit: "cover", filter: `brightness(${0.38 + pulse * 0.12}) saturate(1.2)` }} />
          </AbsoluteFill>
          <AbsoluteFill style={{ background: "radial-gradient(ellipse at center, rgba(10,6,6,0.55) 0%, rgba(10,6,6,0.88) 70%)" }} />
          <Embers count={80} seed={14} green speed={1.2} />
          <AbsoluteFill style={{ alignItems: "center", paddingTop: 110 }}>
            <Slam at={LOGO} from={3}>
              <Logo width={640} style={{ filter: `drop-shadow(0 0 ${30 + pulse * 50}px rgba(61,242,110,0.4))` }} />
            </Slam>
            <div
              style={{
                marginTop: 30,
                padding: "18px 40px",
                borderRadius: 999,
                background: "rgba(10,6,6,0.75)",
                border: `2px solid ${C.ember}`,
                boxShadow: `0 0 ${30 + pulse * 40}px rgba(255,106,31,0.45)`,
                fontFamily: FONT.sans,
                fontWeight: 800,
                fontSize: 54,
                color: C.cream,
                letterSpacing: 1,
                opacity: prog(frame, 168, 6),
                minWidth: 760,
                textAlign: "center",
              }}
            >
              {url}
              <span style={{ opacity: url.length < SITE.length || Math.floor(frame / 8) % 2 ? 1 : 0, color: C.ember }}>|</span>
            </div>
            <div style={{ marginTop: 34, display: "flex", gap: 28, alignItems: "center", opacity: prog(frame, 207, 10) }}>
              <span style={{ fontFamily: FONT.sans, fontWeight: 700, fontSize: 32, color: C.cream, letterSpacing: 2 }}>Link your profile · Represent your city · Fight for your clan</span>
            </div>
            <div style={{ marginTop: 22, fontFamily: FONT.urdu, fontSize: 40, color: C.amber, direction: "rtl", opacity: prog(frame, 242, 10) }}>بلندیوں کی جانب</div>
          </AbsoluteFill>
          <div style={{ position: "absolute", left: 0, right: 0, bottom: 34, textAlign: "center", fontFamily: FONT.sans, fontSize: 18, color: "rgba(244,234,216,0.5)", opacity: prog(frame, 242, 10) }}>
            Music: “Brawlistan” (BRAWLISTAN original) · Data from the official Brawlhalla API · Not affiliated with Blue Mammoth Games
          </div>
        </AbsoluteFill>
      )}
      <Streaks at={0} dur={8} />
      <SpeedBurst at={LOGO} dur={16} color={C.amber} seed={31} cx={960} cy={380} />
      <Flash at={LOGO} dur={10} max={0.9} />
      <Flash at={END_HIT} dur={12} color={C.ember} max={0.45} />
      <SpeedBurst at={END_HIT} dur={14} color={C.green} seed={41} cx={960} cy={380} />
    </AbsoluteFill>
  );
};
