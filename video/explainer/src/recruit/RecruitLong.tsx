// The 60 s cut of the Discord recruitment trailer (video/recruitment/README.md).
// It plays "Storming the Gate" from the top: the quiet intro carries the
// lonely-grinder opening, the silence at 10 s lands on the Discord ping, the
// big hit at 26.70 s on the logo, and the slam at 60.0 s ends it. Built from
// the owner's Hailuo and Gemini clips; all text, the logo and the end card
// are added here.
import React from "react";
import { AbsoluteFill, Audio, Sequence, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { clamp, prog, shake } from "../anim";
import { Embers, Finish, Flash, SpeedBurst } from "../components/fx";
import { typed } from "../components/type";
import { FONT } from "../theme";
import { TRACK_BEATS } from "./beats";
import { Clip, EndCardIn, FeatureFlash, G, Line, LogoDrop, sec as s } from "./Recruit";

export const RECRUIT_LONG_DURATION = s(62);

const EMERALD = "#1ee08a";
const GREEN = "#3df26e";
const MAGENTA = "#f0168c";
const CREAM = "#fbf9d8";
const RED = "#ff2e3a";

// Cuts on the track's beats (track time = video time).
const T = {
  alone: 4.203,
  ping: 6.687,
  silence: 10.286,
  arena: 10.867,
  rival: 12.121,
  knight: 13.375,
  clash: 15.047,
  crowds: 17.531,
  landmark: 18.808,
  map: 20.039,
  flash1: 22.941,
  flash2: 23.568,
  flash3: 24.195,
  fight: 24.822,
  drop: 26.703,
  city: 28.584,
  clan: 30.859,
  win: 33.367,
  oneCommunity: 37.547,
  everyCity: 38.777,
  battles: 40.031,
  landmark2: 41.912,
  become: 42.516,
  waiting: 46.719,
  end: 53.592,
  final: 60.0,
};

type V = { vertical: boolean };

const BigWords: React.FC<{ words: Array<[number, React.ReactNode]>; until: number; size: number }> = ({ words, until, size }) => {
  const frame = useCurrentFrame();
  if (frame < s(words[0][0]) - 1 || frame > s(until) + 2) return null;
  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", flexDirection: "column", gap: 4 }}>
      {words.map(([at, w], i) => {
        if (frame < s(at)) return null;
        const p = prog(frame, s(at), 5);
        return (
          <div
            key={i}
            style={{
              fontFamily: FONT.sans,
              fontWeight: 900,
              fontSize: size,
              lineHeight: 0.95,
              textTransform: "uppercase",
              color: CREAM,
              letterSpacing: -size * 0.025,
              transform: `scale(${2 - p})`,
              opacity: p,
              filter: p < 1 ? `blur(${(1 - p) * 10}px)` : undefined,
              textShadow: "0 6px 40px #000",
            }}
          >
            {w}
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

export const RecruitLong: React.FC<V> = ({ vertical }) => {
  const frame = useCurrentFrame();
  const { width } = useVideoConfig();
  const t = frame / 30;
  const big = vertical ? 124 : 110;
  const hits = [T.arena, T.knight, T.clash, T.drop, T.clan, T.final].map((x) => shake(frame, s(x), x === T.drop || x === T.final ? 30 : 14, Math.round(x * 10)));
  const sh = hits.reduce((a, b) => ({ x: a.x + b.x, y: a.y + b.y }), { x: 0, y: 0 });
  // Gemini's photographic clips are graded towards the anime clips' palette.
  const real = "saturate(1.15) contrast(1.08) brightness(0.95)";
  const textTop = vertical ? "62%" : "64%";
  const musicVol = (f: number) => 0.9 * interpolate(f, [s(T.end), s(T.end) + 15], [1, 0.8], clamp) * interpolate(f, [s(T.final) + 12, s(62)], [1, 0], clamp);
  const band = (at: number, until: number, y: number) =>
    t >= at && t < until ? <AbsoluteFill style={{ background: `radial-gradient(ellipse 90% 20% at 50% ${y}%, rgba(0,0,0,0.6), transparent 100%)` }} /> : null;

  return (
    <AbsoluteFill style={{ background: "#040806" }}>
      <AbsoluteFill style={{ transform: `translate(${sh.x}px, ${sh.y}px) scale(1.04)` }}>
        {/* Alone, then the ping */}
        <Clip src="g-grinder.mp4" from={0} to={T.ping} offset={0.3} zoom={[1.05, 1.18]} pos={vertical ? "38% 50%" : "50% 50%"} filter={real} />
        <Clip src="g-ping.mp4" from={T.ping} to={T.arena} offset={1.69} zoom={[1.1, 1.22]} pos={vertical ? "58% 50%" : "50% 50%"} filter={real} />
        {/* Your next rival is out there */}
        <Clip src="h1-arena.mp4" from={T.arena} to={T.knight} offset={0.6} zoom={[1.0, 1.1]} />
        <Clip src="h2a-knight.mp4" from={T.knight} to={T.clash} offset={1.2} zoom={[1.08, 1.2]} pos={vertical ? "50% 40%" : "50% 30%"} rate={1.15} />
        <Clip src="h2b-clash.mp4" from={T.clash} to={T.crowds} offset={0.6} zoom={[1.0, 1.1]} pos="50% 45%" />
        {/* Find your people */}
        <Clip src="h7-crowds.mp4" from={T.crowds} to={T.landmark} offset={0} zoom={[1.3, 1.4]} pos="50% 85%" />
        <Clip src="h5-landmark.mp4" from={T.landmark} to={T.map} offset={0.3} zoom={[1.0, 1.06]} pos="50% 60%" />
        <Clip src="h3b-map.mp4" from={T.map} to={T.drop} offset={0} rate={0.85} zoom={[1.0, 1.1]} pos="50% 45%" filter={t >= T.flash1 ? "brightness(0.4) blur(4px)" : undefined} />
        {/* The drop */}
        <Clip src="h4-burst.mp4" from={T.drop} to={T.clan} offset={1.0} zoom={[1.0, 1.12]} />
        {/* Fight for your clan, find your fighters */}
        <Clip src="h6-clan.mp4" from={T.clan} to={T.win} offset={0.5} zoom={[1.05, 1.15]} pos="50% 40%" />
        <Clip src="g-win.mp4" from={T.win} to={T.oneCommunity} offset={3.2} zoom={[1.0, 1.06]} pos={vertical ? "46% 50%" : "50% 50%"} filter={real} />
        {/* One community. Every city. Endless battles. */}
        <Clip src="h3-landscape.mp4" from={T.oneCommunity} to={T.landmark2} offset={0.3} zoom={[1.05, 1.15]} pos={vertical ? "38% 50%" : "50% 50%"} />
        <Clip src="h5-landmark.mp4" from={T.landmark2} to={T.waiting} offset={0.5} zoom={[1.1, 1.2]} pos="50% 55%" />
        <Clip src="h3-landscape.mp4" from={T.waiting} to={62} offset={0} rate={0.8} zoom={[1.18, 1.3]} pos={vertical ? "70% 50%" : "50% 50%"} filter="brightness(0.75)" />
      </AbsoluteFill>

      {/* Pakistan, it's time to fight: darkness before the drop */}
      {t >= T.fight && t < T.drop && <AbsoluteFill style={{ background: "#000", opacity: interpolate(frame, [s(T.fight), s(T.fight) + 4], [0, 0.94], clamp) }} />}

      <Embers count={vertical ? 40 : 50} seed={23} speed={1.2} opacity={t < T.arena ? 0.25 : t < T.crowds ? 0.6 : 0.85} palette={t >= T.arena && t < T.crowds ? [RED, "#ff6a1f", "#ffc283"] : [EMERALD, GREEN, "#ffffff", MAGENTA]} />
      <AbsoluteFill style={{ background: "radial-gradient(ellipse at 50% 55%, transparent 40%, rgba(0,0,0,0.55) 100%)" }} />

      {band(0.9, T.ping, vertical ? 62 : 64)}
      {band(T.rival, T.clash, vertical ? 62 : 64)}
      {band(T.crowds, T.flash1, vertical ? 62 : 64)}
      {band(T.city, T.oneCommunity, vertical ? 66 : 74)}
      {band(T.oneCommunity, T.end, vertical ? 50 : 50)}

      <AbsoluteFill>
        <div style={{ position: "absolute", top: textTop, left: 60, right: 60, transform: "translateY(-50%)", display: "flex", flexDirection: "column", alignItems: "center", gap: 10 }}>
          {t < T.alone && (
            <div style={{ fontFamily: FONT.sans, fontWeight: 900, fontSize: vertical ? 88 : 84, lineHeight: 1, color: CREAM, textAlign: "center", textTransform: "uppercase", letterSpacing: -1, textShadow: "0 6px 40px #000", opacity: 1 - prog(frame, s(T.alone) - 5, 5) }}>
              {typed(frame, s(1.0), "Pakistani", 20)}
              <br />
              <span style={{ color: GREEN }}>{typed(frame, s(1.6), "Brawlhalla", 20)}</span>
              <br />
              {typed(frame, s(2.3), "players…", 18)}
            </div>
          )}
          <Line at={T.alone} out={T.ping - 0.2} size={vertical ? 104 : 96}>Still grinding</Line>
          <Line at={T.alone + 0.6} out={T.ping - 0.2} size={vertical ? 104 : 96}><G>alone?</G></Line>
          <Line at={T.rival} out={T.clash - 0.2} size={big}>Your next rival</Line>
          <Line at={T.knight} out={T.clash - 0.2} size={big}><span style={{ color: "#ff6a1f" }}>is out there.</span></Line>
          <Line at={T.crowds + 0.05} out={T.flash1 - 0.25} size={big}>Find your <G>people.</G></Line>
          <Line at={T.map + 0.05} out={T.flash1 - 0.25} size={big}>Build your <G>rivalries.</G></Line>
        </div>
        <div style={{ position: "absolute", top: vertical ? "61%" : "68%", left: 0, right: 0, display: "flex", flexDirection: "column", alignItems: "center", gap: 10 }}>
          <Line at={T.city} out={T.clan - 0.2} size={vertical ? 96 : 80}>Represent your <G>city.</G></Line>
        </div>
        <div style={{ position: "absolute", top: textTop, left: 60, right: 60, transform: "translateY(-50%)", display: "flex", flexDirection: "column", alignItems: "center", gap: 10 }}>
          <Line at={T.clan + 0.1} out={T.win - 0.2} size={big}>Fight for your <G>clan.</G></Line>
          <Line at={T.win + 0.1} out={T.oneCommunity - 0.2} size={big}>Find your <G>fighters.</G></Line>
        </div>
        <div style={{ position: "absolute", top: "50%", left: 60, right: 60, transform: "translateY(-50%)", display: "flex", flexDirection: "column", alignItems: "center", gap: 10 }}>
          <Line at={T.oneCommunity} out={T.landmark2 - 0.2} size={big}>One community.</Line>
          <Line at={T.everyCity} out={T.landmark2 - 0.2} size={big}><G>Every city.</G></Line>
          <Line at={T.battles} out={T.landmark2 - 0.2} size={big}>Endless battles.</Line>
          <Line at={T.become} out={T.waiting - 0.2} size={vertical ? 100 : 90}>Become part of</Line>
          <Line at={T.become + 0.3} out={T.waiting - 0.2} size={vertical ? 100 : 90}><G>BRAWLISTAN.</G></Line>
          {t >= T.waiting - 0.05 && t < T.end + 0.3 && (
            <div style={{ opacity: 1 - prog(frame, s(T.end) - 4, 8) }}>
              <Line at={T.waiting + 0.3} size={vertical ? 140 : 120}>Your community</Line>
              <Line at={T.waiting + 0.9} size={vertical ? 140 : 120}><G>is waiting.</G></Line>
            </div>
          )}
        </div>
      </AbsoluteFill>

      <BigWords words={[[T.fight, "Pakistan,"], [25.472, "it's time"], [26.076, <G key="f">to fight.</G>]]} until={T.drop - 0.04} size={vertical ? 150 : 140} />
      <FeatureFlash vertical={vertical} times={[T.flash1, T.flash2, T.flash3, T.fight]} />
      <LogoDrop vertical={vertical} drop={T.drop} lift={T.city} until={T.clan} beats={TRACK_BEATS} />

      <Sequence from={s(T.end)} name="end card">
        <EndCardIn vertical={vertical} />
      </Sequence>

      <SpeedBurst at={s(T.knight)} dur={12} color="#ffc283" seed={3} cx={width / 2} cy={vertical ? 900 : 540} />
      <SpeedBurst at={s(T.drop)} dur={16} color={GREEN} seed={9} cx={width / 2} cy={vertical ? 900 : 540} />
      <SpeedBurst at={s(T.final)} dur={16} color={GREEN} seed={19} cx={width / 2} cy={vertical ? 520 : 400} />
      <Flash at={s(T.silence)} dur={10} color={EMERALD} max={0.35} />
      <Flash at={s(T.arena)} dur={6} max={0.4} />
      <Flash at={s(T.knight)} dur={6} color={RED} max={0.6} />
      <Flash at={s(T.clash)} dur={5} max={0.55} />
      <Flash at={s(T.crowds)} dur={6} color={EMERALD} max={0.35} />
      <Flash at={s(T.drop)} dur={10} max={0.95} />
      <Flash at={s(T.clan)} dur={6} color={EMERALD} max={0.4} />
      <Flash at={s(T.final)} dur={12} color={EMERALD} max={0.5} />
      <Finish />

      <Audio src={staticFile("recruit/storming-the-gate.mp3")} volume={musicVol} />
      {CUES.map(([at, name, vol], i) => (
        <Sequence key={i} from={s(at)} durationInFrames={s(3)} name={`sfx ${name}`}>
          <Audio src={staticFile(`sfx/${name}.wav`)} volume={vol} />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};

const CUES: Array<readonly [number, string, number]> = [
  [T.ping, "whoosh", 0.3],
  [T.silence, "success", 0.55],
  [T.arena - 0.1, "whoosh", 0.35],
  [T.knight, "impact", 0.5],
  [T.clash, "hit", 0.45],
  [T.crowds - 0.1, "whoosh-long", 0.4],
  [T.flash1, "tick", 0.5],
  [T.flash2, "tick", 0.5],
  [T.flash3, "tick", 0.5],
  [T.fight, "hit", 0.5],
  [25.472, "hit", 0.5],
  [26.076, "hit", 0.55],
  [T.drop, "boom", 0.7],
  [T.clan - 0.1, "whoosh", 0.4],
  [T.win - 0.1, "whoosh", 0.35],
  [T.oneCommunity - 0.1, "whoosh-long", 0.35],
  [T.waiting - 0.1, "whoosh", 0.35],
  [T.end - 0.1, "whoosh", 0.45],
  [T.end + 0.2, "click", 0.4],
  [T.final, "boom", 0.6],
];
