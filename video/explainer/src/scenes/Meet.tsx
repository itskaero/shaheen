// Scene 2 (5.8–12.7 s): meet the site. The real entrance page flies in, then
// the camera drops onto the real sidebar while the sections it lists slam in
// on the beat.
import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { clamp, easeInOut, easeOut, prog } from "../anim";
import { Embers, Flash, Streaks, Tag, usePulse } from "../components/fx";
import { ACCENT, DISPLAY, MaskUp } from "../components/type";
import { Browser, Highlight, Shot } from "../components/ui";
import { C, FONT, SITE } from "../theme";

// Sidebar items in the 2400 px wide home.png capture (centre y).
const NAV = [
  { label: "Rankings", y: 365, at: 70 },
  { label: "City Wars", y: 424, at: 87 },
  { label: "Clan Wars", y: 482, at: 104 },
  { label: "Players", y: 544, at: 121 },
  { label: "Teams", y: 602, at: 139 },
  { label: "Seasons", y: 721, at: 155 },
];
const CUT = 66;

export const Meet: React.FC = () => {
  const frame = useCurrentFrame();
  const pulse = usePulse();

  // Part A: entrance page in a browser
  const enter = prog(frame, 0, 18, easeOut);
  const rotY = interpolate(enter, [0, 1], [-28, -9]);
  const drift = interpolate(frame, [0, CUT], [0, -40]);

  // Part B: camera on the dashboard sidebar
  const k = 1.5; // home.png shown at 1.5x of its pixel size
  const W = 2400 * k;
  const active = [...NAV].reverse().find((n) => frame >= n.at);
  const camY = interpolate(frame, [CUT, CUT + 20, 175], [-260, -360, -430], { ...clamp, easing: easeInOut });

  return (
    <AbsoluteFill style={{ background: C.bg, overflow: "hidden" }}>
      <Embers count={40} seed={4} opacity={0.6} />
      {frame < CUT + 6 && (
        <AbsoluteFill style={{ opacity: 1 - prog(frame, CUT, 6) }}>
          <div style={{ position: "absolute", left: 90, top: 250, width: 640 }}>
            <Tag enter={4}>The website</Tag>
            <div style={{ ...DISPLAY, fontSize: 96, marginTop: 30 }}>
              <MaskUp start={6}>Meet</MaskUp>
            </div>
            <div style={{ ...DISPLAY, fontSize: 96 }}>
              <MaskUp start={12}>BRAWLISTAN</MaskUp>
            </div>
            <div style={{ fontFamily: FONT.sans, fontSize: 34, lineHeight: 1.35, color: C.muted, marginTop: 30, opacity: prog(frame, 22, 12) }}>
              Every ranked Pakistani player — the rankings, the rivalries between{" "}
              <span style={{ ...ACCENT, fontSize: 40 }}>cities</span> and <span style={{ ...ACCENT, fontSize: 40, color: C.ember }}>clans</span>.
            </div>
          </div>
          <div
            style={{
              position: "absolute",
              left: 820,
              top: 170,
              perspective: 1800,
            }}
          >
            <div style={{ transform: `translateX(${(1 - enter) * 600 + drift}px) rotateY(${rotY}deg) scale(${0.92 + pulse * 0.01})`, transformOrigin: "left center" }}>
              <Browser url={SITE} width={1240}>
                <Shot name="entrance" width={1240} />
              </Browser>
            </div>
          </div>
        </AbsoluteFill>
      )}

      {frame >= CUT && (
        <AbsoluteFill>
          <div style={{ position: "absolute", left: -270, top: 0, transform: `translateY(${camY}px)`, opacity: prog(frame, CUT, 6) }}>
            <div style={{ position: "relative", width: W }}>
              <Shot name="home" width={W} style={{ filter: "brightness(0.9)" }} />
              {active && <Highlight key={active.label} x={225 * k} y={(active.y - 30) * k} w={345 * k} h={60 * k} start={active.at} radius={16} />}
            </div>
          </div>
          <AbsoluteFill style={{ background: "linear-gradient(90deg, rgba(10,6,6,0) 0%, rgba(10,6,6,0) 34%, rgba(10,6,6,0.97) 47%, #0a0606 52%)" }} />
          <div style={{ position: "absolute", left: 1000, top: 150 }}>
            <Tag enter={CUT + 2} color={C.ember}>{SITE}</Tag>
            <div style={{ marginTop: 26 }}>
              {NAV.map((n) => {
                const on = active?.label === n.label;
                const p = prog(frame, n.at, 7);
                return (
                  <div
                    key={n.label}
                    style={{
                      ...DISPLAY,
                      fontSize: 92,
                      lineHeight: 1.02,
                      color: on ? C.cream : "rgba(244,234,216,0.32)",
                      transform: `translateX(${(1 - p) * 120}px) scale(${on ? 1 + pulse * 0.03 : 1})`,
                      transformOrigin: "left center",
                      opacity: p,
                      textShadow: on ? `0 0 40px rgba(255,106,31,0.55)` : "none",
                    }}
                  >
                    {on && <span style={{ color: C.ember, marginRight: 18 }}>›</span>}
                    {n.label}
                  </div>
                );
              })}
            </div>
            <div style={{ fontFamily: FONT.sans, fontSize: 28, color: C.muted, marginTop: 28, opacity: prog(frame, 172, 10) }}>
              Ranked data from the official Brawlhalla API, synced every 6 hours.
            </div>
          </div>
        </AbsoluteFill>
      )}
      <Streaks at={CUT - 4} dur={9} dir={-1} />
      <Flash at={CUT} dur={5} max={0.3} />
    </AbsoluteFill>
  );
};
