// Scene 1 (0–5.8 s): the hook. Silence, a slash of light, then the drop hits
// on "FIGHT FOR YOUR CITY", whips to "REPRESENT YOUR CLAN", and the BRAWLISTAN
// logo slams in.
import React from "react";
import { AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame } from "remotion";
import { clamp, easeOut, prog, shake } from "../anim";
import { Embers, Flash, SpeedBurst, Streaks, usePulse } from "../components/fx";
import { ACCENT, DISPLAY, MaskUp, Slam } from "../components/type";
import { Logo } from "../components/ui";
import { C, FONT } from "../theme";

const HIT = 36; // 1.184 s, the first big hit
const WHIP = 87; // 2.903 s
const LOGO = 139; // 4.644 s

export const Hook: React.FC = () => {
  const frame = useCurrentFrame();
  const pulse = usePulse();
  const s = { x: shake(frame, HIT, 22, 1).x + shake(frame, LOGO, 26, 7).x, y: shake(frame, HIT, 22, 1).y + shake(frame, LOGO, 26, 7).y };

  const slash = prog(frame, 4, 26);
  const preO = 1 - prog(frame, HIT - 4, 4);
  const bg1 = frame >= HIT && frame < WHIP + 4;
  const bg2 = frame >= WHIP && frame < LOGO;
  const bgZoom = interpolate(frame, [HIT, HIT + 14, WHIP], [1.35, 1.12, 1.05], { ...clamp, easing: easeOut });
  const whipX = interpolate(frame, [WHIP, WHIP + 8], [-140, 0], { ...clamp, easing: easeOut });
  const logoBg = frame >= LOGO;

  return (
    <AbsoluteFill style={{ background: C.bg, overflow: "hidden" }}>
      <AbsoluteFill style={{ transform: `translate(${s.x}px, ${s.y}px)` }}>
        {bg1 && (
          <AbsoluteFill style={{ transform: `scale(${bgZoom + pulse * 0.015})` }}>
            <Img src={staticFile("img/warriors.jpg")} style={{ width: "100%", height: "100%", objectFit: "cover", filter: `brightness(${0.5 + pulse * 0.15}) saturate(1.15)` }} />
          </AbsoluteFill>
        )}
        {bg2 && (
          <AbsoluteFill style={{ transform: `translateX(${whipX}px) scale(${1.12 - prog(frame, WHIP, 50) * 0.06})` }}>
            <Img src={staticFile("img/hero-scene.jpg")} style={{ width: "100%", height: "100%", objectFit: "cover", filter: `brightness(${0.42 + pulse * 0.15}) saturate(1.1)` }} />
          </AbsoluteFill>
        )}
        {logoBg && (
          <AbsoluteFill style={{ transform: `scale(${1.2 - prog(frame, LOGO, 40) * 0.12})` }}>
            <Img src={staticFile("img/warriors.jpg")} style={{ width: "100%", height: "100%", objectFit: "cover", filter: "brightness(0.28) blur(3px) saturate(1.2)" }} />
          </AbsoluteFill>
        )}
        <AbsoluteFill style={{ background: "linear-gradient(90deg, rgba(10,6,6,0.88) 0%, rgba(10,6,6,0.35) 55%, rgba(10,6,6,0.1) 100%)" }} />
        <Embers count={70} seed={2} opacity={frame < HIT ? 0.35 : 1} />

        {/* Pre-hit: a slash of light and the setting */}
        {frame < HIT && (
          <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", opacity: preO }}>
            <div style={{ width: 1500 * slash, height: 3, background: `linear-gradient(90deg, transparent, ${C.red}, ${C.amber}, ${C.red}, transparent)`, boxShadow: `0 0 30px ${C.red}` }} />
            <div style={{ position: "absolute", top: 580, fontFamily: FONT.sans, fontWeight: 700, fontSize: 30, letterSpacing: 14 * (0.6 + slash * 0.4), color: C.cream, opacity: prog(frame, 8, 14) }}>
              PAKISTAN · BRAWLHALLA
            </div>
          </AbsoluteFill>
        )}

        {/* FIGHT FOR YOUR CITY */}
        {frame >= HIT && frame < WHIP && (
          <div style={{ position: "absolute", left: 120, top: 300 }}>
            <div style={{ ...DISPLAY, fontSize: 210 }}>
              <MaskUp start={HIT} dur={7}>Fight for</MaskUp>
            </div>
            <div style={{ ...DISPLAY, fontSize: 210, marginTop: 10 }}>
              <MaskUp start={HIT + 17} dur={7}>
                your <span style={{ ...ACCENT, fontSize: 250, color: C.amber }}>city.</span>
              </MaskUp>
            </div>
          </div>
        )}

        {/* REPRESENT YOUR CLAN */}
        {frame >= WHIP && frame < LOGO && (
          <div style={{ position: "absolute", left: 120, top: 300 }}>
            <div style={{ ...DISPLAY, fontSize: 210 }}>
              <MaskUp start={WHIP} dur={6}>Represent</MaskUp>
            </div>
            <div style={{ ...DISPLAY, fontSize: 210, marginTop: 10 }}>
              <MaskUp start={WHIP + 17} dur={7}>
                your <span style={{ ...ACCENT, fontSize: 250, color: C.ember }}>clan.</span>
              </MaskUp>
            </div>
            <div style={{ ...DISPLAY, fontSize: 64, letterSpacing: 6, marginTop: 34, color: C.amber }}>
              <MaskUp start={122} dur={6}>Climb Pakistan's rankings.</MaskUp>
            </div>
          </div>
        )}

        {/* Logo reveal */}
        {logoBg && (
          <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", flexDirection: "column" }}>
            <Slam at={LOGO} from={2.6} dur={8}>
              <Logo width={760} style={{ filter: `drop-shadow(0 0 ${30 + pulse * 40}px rgba(61,242,110,0.35))` }} />
            </Slam>
            <div style={{ marginTop: 10, fontFamily: FONT.urdu, fontSize: 44, color: C.amber, opacity: prog(frame, LOGO + 10, 8), direction: "rtl" }}>
              بلندیوں کی جانب
            </div>
          </AbsoluteFill>
        )}
      </AbsoluteFill>

      <SpeedBurst at={HIT} dur={14} />
      <SpeedBurst at={LOGO} dur={16} seed={9} color={C.green} />
      <Streaks at={WHIP - 3} dur={10} dir={1} />
      <Flash at={HIT} dur={9} color={C.red} max={0.9} />
      <Flash at={WHIP} dur={5} color="#fff" max={0.35} />
      <Flash at={LOGO} dur={10} color="#fff" max={0.9} />
    </AbsoluteFill>
  );
};
