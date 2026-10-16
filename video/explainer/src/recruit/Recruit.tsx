// The 30 s Discord recruitment trailer (video/recruitment/README.md), built
// from the owner's Hailuo clips (public/recruit/h*.mp4) and Suno track, with
// all text, the logo and the end card added here so they are spelled exactly.
// `vertical` switches between the 9:16 master and the 16:9 cut.
import React from "react";
import { AbsoluteFill, Audio, Img, OffthreadVideo, Sequence, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { clamp, easeInOut, easeOut, prog, shake } from "../anim";
import { Finish, Flash, SpeedBurst, Embers } from "../components/fx";
import { MaskUp, Slam, typed } from "../components/type";
import { EndCard } from "../EndCard";
import { FONT } from "../theme";
import { MUSIC_START, RECRUIT_BEATS } from "./beats";

const FPS = 30;
const s = (sec: number) => Math.round(sec * FPS);
export const RECRUIT_DURATION = s(30);
export { s as sec, FPS as RECRUIT_FPS };

const EMERALD = "#1ee08a";
const GREEN = "#3df26e";
const MAGENTA = "#f0168c";
const CREAM = "#fbf9d8";
const RED = "#ff2e3a";

// Cuts, on the track's beats (src/recruit/beats.ts). The big hit is at 15.0.
const T = {
  rival: 3.97,
  clash: 5.828,
  people: 8.336,
  map: 10.611,
  flash1: 12.492,
  flash2: 13.119,
  flash3: 13.769,
  riser: 14.373,
  drop: 15.0,
  city: 16.881,
  become: 19.156,
  waiting: 21.037,
  end: 23.545,
  final: 28.955,
};

type V = { vertical: boolean };

/** Beat pulse at the current frame (0..1), from the trailer track. */
export function usePulse(beats: ReadonlyArray<readonly [number, number]> = RECRUIT_BEATS): number {
  const t = useCurrentFrame() / FPS;
  let best = 0;
  for (const [bt, st] of beats) {
    if (bt > t) break;
    const age = t - bt;
    if (age < 0.35) best = Math.max(best, (0.4 + 0.6 * (st / 9)) * Math.exp(-age * 9));
  }
  return best;
}

/** One Hailuo clip from `from` to `to` (seconds), starting `offset` seconds in. */
export const Clip: React.FC<{ src: string; from: number; to: number; offset?: number; pos?: string; zoom?: [number, number]; filter?: string; rate?: number }> = ({
  src,
  from,
  to,
  offset = 0,
  pos = "50% 50%",
  zoom = [1, 1],
  filter,
  rate = 1,
}) => (
  <Sequence from={s(from)} durationInFrames={s(to) - s(from)} name={src}>
    <ClipInner src={src} len={to - from} offset={offset} pos={pos} zoom={zoom} filter={filter} rate={rate} />
  </Sequence>
);

const ClipInner: React.FC<{ src: string; len: number; offset: number; pos: string; zoom: [number, number]; filter?: string; rate: number }> = ({ src, len, offset, pos, zoom, filter, rate }) => {
  const frame = useCurrentFrame();
  const z = interpolate(frame, [0, s(len)], zoom, clamp);
  return (
    <AbsoluteFill style={{ overflow: "hidden" }}>
      <OffthreadVideo
        src={staticFile(`recruit/${src}`)}
        muted
        startFrom={s(offset)}
        playbackRate={rate}
        style={{ width: "100%", height: "100%", objectFit: "cover", objectPosition: pos, transform: `scale(${z})`, filter }}
      />
    </AbsoluteFill>
  );
};

/** Big kinetic line, cream with an optional emerald word. */
export const Line: React.FC<{ at: number; out?: number; size: number; children: React.ReactNode; delay?: number }> = ({ at, out, size, children, delay = 0 }) => {
  const frame = useCurrentFrame();
  if (frame < s(at) - 1 || (out !== undefined && frame > s(out) + 8)) return null;
  return (
    <div
      style={{
        fontFamily: FONT.sans,
        fontWeight: 900,
        fontSize: size,
        lineHeight: 0.95,
        letterSpacing: -size * 0.025,
        textTransform: "uppercase",
        color: CREAM,
        textAlign: "center",
        textShadow: "0 6px 40px rgba(0,0,0,0.85), 0 0 2px rgba(0,0,0,0.9)",
      }}
    >
      <MaskUp start={s(at) + delay} dur={6} out={out === undefined ? undefined : s(out)} outDur={6}>
        {children}
      </MaskUp>
    </div>
  );
};

export const G: React.FC<{ children: React.ReactNode }> = ({ children }) => <span style={{ color: GREEN }}>{children}</span>;

/** Scene 3 flashes: the site's real features, 0.6 s each. */
export const FeatureFlash: React.FC<V & { times?: [number, number, number, number] }> = ({ vertical, times = [T.flash1, T.flash2, T.flash3, T.riser] }) => {
  const frame = useCurrentFrame();
  const t = frame / FPS;
  if (t < times[0] || t >= times[3]) return null;
  const which = t < times[1] ? 0 : t < times[2] ? 1 : 2;
  const start = times[which];
  const p = prog(frame, s(start), 5);
  const label = ["City Wars", "Clan Wars", "Pakistan Rankings"][which];
  const cities = ["Karachi", "Lahore", "Islamabad", "Peshawar", "Quetta", "Multan", "Faisalabad", "Hyderabad", "Sialkot"];
  const card = (child: React.ReactNode) => (
    <div style={{ transform: `perspective(1400px) rotateY(${(1 - p) * -25 + (which - 1) * 6}deg) scale(${0.9 + p * 0.1})`, opacity: p }}>{child}</div>
  );
  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", flexDirection: "column", gap: vertical ? 40 : 28, background: "rgba(4,8,6,0.55)" }}>
      <div style={{ fontFamily: FONT.sans, fontWeight: 800, fontSize: vertical ? 54 : 46, letterSpacing: 8, color: EMERALD, textTransform: "uppercase", textShadow: `0 0 30px ${EMERALD}` }}>{label}</div>
      {which === 0 &&
        card(
          <div style={{ display: "grid", gridTemplateColumns: vertical ? "1fr 1fr" : "1fr 1fr 1fr", gap: "10px 36px", fontFamily: FONT.serif, fontStyle: "italic", fontSize: vertical ? 84 : 66, color: CREAM, textAlign: "center" }}>
            {cities.map((c, i) => (
              <span key={c} style={{ opacity: frame >= s(start) + i ? 1 : 0, color: i % 3 === 0 ? GREEN : CREAM }}>{c}</span>
            ))}
          </div>,
        )}
      {which === 1 &&
        card(
          <div style={{ display: "flex", alignItems: "center", gap: vertical ? 30 : 50 }}>
            <Img src={staticFile("img/teams/sigma-grinders.png")} style={{ width: vertical ? 330 : 300, filter: "drop-shadow(0 0 40px rgba(139,61,255,0.6))" }} />
            <span style={{ fontFamily: FONT.sans, fontWeight: 900, fontSize: vertical ? 90 : 100, color: CREAM }}>VS</span>
            <Img src={staticFile("img/teams/delight-esports.png")} style={{ width: vertical ? 330 : 300, filter: "drop-shadow(0 0 40px rgba(233,196,106,0.6))" }} />
          </div>,
        )}
      {which === 2 &&
        card(
          // The real Rankings table, cropped to the board so it reads on a phone.
          <div style={{ width: vertical ? 980 : 1300, height: vertical ? 760 : 640, borderRadius: 24, overflow: "hidden", border: `2px solid ${EMERALD}`, boxShadow: `0 0 60px rgba(30,224,138,0.35)`, position: "relative" }}>
            <Img src={staticFile("shots/rankings.png")} style={{ position: "absolute", width: vertical ? 1500 : 1900, left: vertical ? -400 : -500, top: vertical ? -130 : -150, display: "block" }} />
          </div>,
        )}
    </AbsoluteFill>
  );
};

/** The drop: the BRAWLISTAN logo slams onto the emerald burst. */
export const LogoDrop: React.FC<V & { drop?: number; lift?: number; until?: number; beats?: ReadonlyArray<readonly [number, number]> }> = ({ vertical, drop = T.drop, lift = T.city, until = T.waiting, beats }) => {
  const frame = useCurrentFrame();
  const pulse = usePulse(beats);
  const d = s(drop);
  if (frame < d || frame >= s(until) + 6) return null;
  const drift = interpolate(frame, [s(lift) - 10, s(lift) + 8], [0, vertical ? -260 : -150], { ...clamp, easing: easeInOut });
  const out = prog(frame, s(until) - 2, 8);
  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", opacity: 1 - out }}>
      <div style={{ transform: `translateY(${drift}px) scale(${1 + pulse * 0.025})` }}>
        <Slam at={d} from={2.6} dur={7}>
          <Img src={staticFile("img/logo.png")} style={{ width: vertical ? 820 : 760, display: "block", filter: `drop-shadow(0 0 ${40 + pulse * 50}px rgba(61,242,110,0.45))` }} />
        </Slam>
      </div>
    </AbsoluteFill>
  );
};

export const Recruit: React.FC<V> = ({ vertical }) => {
  const frame = useCurrentFrame();
  const { width } = useVideoConfig();
  const t = frame / FPS;
  const big = vertical ? 132 : 116;
  const shakeAt = [T.rival, T.clash, T.drop].map((x) => shake(frame, s(x), x === T.drop ? 30 : 16, Math.round(x * 10)));
  const sh = shakeAt.reduce((a, b) => ({ x: a.x + b.x, y: a.y + b.y }), { x: 0, y: 0 });
  // The fight is red; from the community scene on, everything turns emerald.
  const grade = t < T.people ? "saturate(1.15) contrast(1.05)" : "saturate(1.1)";
  const textTop = vertical ? "62%" : "64%";
  // Ducked a little under the end card, faded out after the last hit.
  const musicVol = (f: number) => 0.9 * interpolate(f, [s(T.end), s(T.end) + 15], [1, 0.75], clamp) * interpolate(f, [s(T.final) + 6, s(30)], [1, 0], clamp);

  return (
    <AbsoluteFill style={{ background: "#040806" }}>
      <AbsoluteFill style={{ transform: `translate(${sh.x}px, ${sh.y}px) scale(1.04)`, filter: grade }}>
        {/* 1 · The Call */}
        <Clip src="h1-arena.mp4" from={0} to={T.rival} offset={0.4} zoom={[1.0, 1.12]} pos={vertical ? "50% 50%" : "50% 60%"} />
        {/* 2 · The Action */}
        <Clip src="h2a-knight.mp4" from={T.rival} to={T.clash} offset={1.2} zoom={[1.08, 1.22]} pos={vertical ? "50% 40%" : "50% 30%"} rate={1.15} />
        <Clip src="h2b-clash.mp4" from={T.clash} to={T.people} offset={0.6} zoom={[1.0, 1.1]} pos="50% 45%" />
        {/* 3 · The Community */}
        <Clip src="h3-landscape.mp4" from={T.people} to={T.map} offset={0.3} zoom={[1.05, 1.15]} pos={vertical ? "38% 50%" : "50% 50%"} />
        <Clip src="h3b-map.mp4" from={T.map} to={T.drop} offset={1.0} zoom={[1.0, 1.08]} pos="50% 45%" filter={t >= T.flash1 ? "brightness(0.45) blur(4px)" : undefined} />
        {/* 4 · The Identity */}
        <Clip src="h4-burst.mp4" from={T.drop} to={T.waiting} offset={1.0} zoom={[1.0, 1.12]} pos="50% 50%" />
        {/* 5 · The Recruitment */}
        <Clip src="h3-landscape.mp4" from={T.waiting} to={30} offset={3.2} zoom={[1.18, 1.3]} pos={vertical ? "70% 50%" : "50% 50%"} filter="brightness(0.75)" />
      </AbsoluteFill>

      {/* Riser: a beat of darkness before the drop */}
      {t >= T.riser && t < T.drop && <AbsoluteFill style={{ background: "#000", opacity: interpolate(frame, [s(T.riser), s(T.riser) + 6], [0, 0.92], clamp) }} />}

      <Embers count={vertical ? 40 : 50} seed={17} speed={1.2} opacity={t < T.people ? 0.6 : 0.9} palette={t < T.people ? [RED, "#ff6a1f", "#ffc283"] : [EMERALD, GREEN, "#ffffff", MAGENTA]} />
      <AbsoluteFill style={{ background: "radial-gradient(ellipse at 50% 55%, transparent 40%, rgba(0,0,0,0.55) 100%)" }} />

      {/* A soft dark band so the text reads over busy shots */}
      {t >= T.rival && t < T.flash1 && (
        <AbsoluteFill style={{ background: `radial-gradient(ellipse 90% 22% at 50% ${vertical ? 62 : 64}%, rgba(0,0,0,0.6), transparent 100%)` }} />
      )}
      {t >= T.city && t < T.waiting && (
        <AbsoluteFill style={{ background: `radial-gradient(ellipse 85% 16% at 50% ${vertical ? 66 : 76}%, rgba(0,0,0,0.65), transparent 100%)` }} />
      )}

      {/* Text */}
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", paddingLeft: 60, paddingRight: 60 }}>
        <div style={{ position: "absolute", top: textTop, left: 0, right: 0, transform: "translateY(-50%)", display: "flex", flexDirection: "column", alignItems: "center", gap: 10 }}>
          {t < T.rival && (
            <div style={{ fontFamily: FONT.sans, fontWeight: 900, fontSize: vertical ? 88 : 84, lineHeight: 1, color: CREAM, textAlign: "center", textTransform: "uppercase", letterSpacing: -1, textShadow: "0 6px 40px #000", opacity: 1 - prog(frame, s(T.rival) - 5, 5), maxWidth: width - 120 }}>
              {typed(frame, s(0.418), "Pakistani", 20)}
              <br />
              <span style={{ color: GREEN }}>{typed(frame, s(0.9), "Brawlhalla", 20)}</span>
              <br />
              {typed(frame, s(1.5), "players…", 18)}
            </div>
          )}
          <Line at={T.rival} out={T.people - 0.2} size={big}>Your next rival</Line>
          <Line at={T.clash} out={T.people - 0.2} size={big}>
            <span style={{ color: t < T.people ? "#ff6a1f" : GREEN }}>is out there.</span>
          </Line>
          <Line at={T.people + 0.1} out={T.flash1 - 0.25} size={big}>Find your <G>people.</G></Line>
          <Line at={T.map + 0.05} out={T.flash1 - 0.25} size={big}>Build your <G>rivalries.</G></Line>
        </div>
        {/* Under the logo */}
        <div style={{ position: "absolute", top: vertical ? "61%" : "68%", left: 0, right: 0, display: "flex", flexDirection: "column", alignItems: "center", gap: 10 }}>
          <Line at={T.city} out={T.waiting - 0.2} size={vertical ? 96 : 80}>Represent your <G>city.</G></Line>
          <Line at={T.become} out={T.waiting - 0.2} size={vertical ? 72 : 60}>Become part of <G>BRAWLISTAN.</G></Line>
        </div>
        {t >= T.waiting - 0.05 && t < T.end + 0.3 && (
          <div style={{ position: "absolute", top: "50%", left: 0, right: 0, transform: "translateY(-50%)", opacity: 1 - prog(frame, s(T.end) - 4, 8) }}>
            <Line at={T.waiting} size={vertical ? 140 : 120}>Your community</Line>
            <Line at={T.waiting + 0.35} size={vertical ? 140 : 120}><G>is waiting.</G></Line>
          </div>
        )}
      </AbsoluteFill>

      <FeatureFlash vertical={vertical} />
      <LogoDrop vertical={vertical} />

      {/* End card: the main call to action */}
      <Sequence from={s(T.end)} name="end card">
        <EndCardIn vertical={vertical} />
      </Sequence>

      <SpeedBurst at={s(T.rival)} dur={12} color="#ffc283" seed={3} cx={width / 2} cy={vertical ? 900 : 540} />
      <SpeedBurst at={s(T.drop)} dur={16} color={GREEN} seed={9} cx={width / 2} cy={vertical ? 900 : 540} />
      <Flash at={s(T.rival)} dur={6} color={RED} max={0.6} />
      <Flash at={s(T.clash)} dur={5} max={0.55} />
      <Flash at={s(T.people)} dur={6} color={EMERALD} max={0.35} />
      <Flash at={s(T.drop)} dur={10} max={0.95} />
      <Flash at={s(T.final)} dur={10} color={EMERALD} max={0.3} />
      <Finish />

      <Audio src={staticFile("recruit/storming-the-gate.mp3")} startFrom={s(MUSIC_START)} volume={musicVol} />
      {CUES.map(([at, name, vol], i) => (
        <Sequence key={i} from={s(at)} durationInFrames={s(3)} name={`sfx ${name}`}>
          <Audio src={staticFile(`sfx/${name}.wav`)} volume={vol} />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};

export const EndCardIn: React.FC<V> = ({ vertical }) => {
  const frame = useCurrentFrame();
  const p = prog(frame, 0, 12, easeOut);
  return (
    <AbsoluteFill style={{ opacity: Math.min(1, p * 1.5), transform: `translateY(${(1 - p) * 120}px)` }}>
      <EndCard vertical={vertical} showInvite />
    </AbsoluteFill>
  );
};

// Restrained: the track already has its own hits.
const CUES: Array<readonly [number, string, number]> = [
  [0.05, "sweep", 0.35],
  [T.rival, "impact", 0.55],
  [T.clash - 0.1, "whoosh", 0.4],
  [T.clash, "hit", 0.45],
  [T.people - 0.15, "whoosh-long", 0.4],
  [T.map - 0.1, "whoosh", 0.35],
  [T.flash1, "tick", 0.5],
  [T.flash2, "tick", 0.5],
  [T.flash3, "tick", 0.5],
  [T.riser - 0.4, "sweep", 0.45],
  [T.drop, "boom", 0.7],
  [T.waiting - 0.1, "whoosh", 0.35],
  [T.end - 0.1, "whoosh", 0.45],
  [T.end + 0.2, "click", 0.4],
  [T.final, "impact", 0.5],
];
