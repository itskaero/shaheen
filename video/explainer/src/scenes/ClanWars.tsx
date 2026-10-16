// Scene 5 (40.4–52.5 s): Clan Wars (ADR-131). Real rules: a weekly team league
// scored from ranked play — 10 points per ranked 1v1 win plus every rating
// point gained, losses cost nothing, a team's best 5 members count, the week
// ends Monday 00:00 PKT. Standings are the real snapshot (web/data/clan-wars.json,
// captured 2026-10-16, week of Oct 12, in progress).
import React from "react";
import { AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame } from "remotion";
import { clamp, easeInOut, prog, shake } from "../anim";
import { Embers, Flash, SpeedBurst, Streaks, Tag, usePulse } from "../components/fx";
import { ACCENT, CountUp, DISPLAY, MaskUp, Slam } from "../components/type";
import { C, FONT } from "../theme";

const TEAMS = [
  { slug: "sigma-grinders", name: "Sigma Grinders", tag: "SG", accent: "#8b3dff", points: 70, scorer: "hmmm 70" },
  { slug: "delight-esports", name: "Delight Esports", tag: "DE", accent: "#e9c46a", points: 63, scorer: "scoooot!!! 63" },
  { slug: "clan-monke", name: "Clan Monke", tag: "MONKE", accent: "#e8b923", points: 0, scorer: "" },
  { slug: "revenant-wolf", name: "Revenant Wolf", tag: "RW", accent: "#e3122d", points: 0, scorer: "" },
  { slug: "shaheen", name: "SHAHEEN", tag: "SHN", accent: "#3df26e", points: 0, scorer: "" },
];

const Intro: React.FC = () => {
  const frame = useCurrentFrame();
  const pulse = usePulse();
  const s = shake(frame, 0, 22, 4);
  const out = prog(frame, 30, 7);
  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", flexDirection: "column", opacity: 1 - out, transform: `translate(${s.x}px, ${s.y}px) scale(${1 - out * 0.1})` }}>
      <Slam at={0} from={2.8}>
        <div style={{ ...DISPLAY, fontSize: 290, letterSpacing: -6, color: C.amber, textShadow: `0 0 ${40 + pulse * 60}px rgba(233,185,73,0.5)` }}>
          Clan <span style={{ color: C.cream }}>Wars</span>
        </div>
      </Slam>
      <div style={{ fontFamily: FONT.serif, fontStyle: "italic", fontSize: 72, color: C.cream, opacity: prog(frame, 10, 8) }}>
        Every win is a <span style={{ color: C.ember }}>blow</span> for your clan
      </div>
    </AbsoluteFill>
  );
};

const Teams: React.FC = () => {
  const frame = useCurrentFrame();
  const o = prog(frame, 34, 6) * (1 - prog(frame, 116, 6));
  const at = [35, 44, 52, 61, 69];
  return (
    <AbsoluteFill style={{ opacity: o }}>
      <div style={{ position: "absolute", left: 0, right: 0, top: 150, textAlign: "center" }}>
        <Tag enter={36} color={C.amber}>A weekly team league</Tag>
        <div style={{ ...DISPLAY, fontSize: 110, marginTop: 22 }}>
          <MaskUp start={38}>
            Be on a <span style={{ ...ACCENT, fontSize: 130 }}>team</span>
          </MaskUp>
        </div>
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 470, display: "flex", justifyContent: "center", gap: 44 }}>
        {TEAMS.map((t, i) => {
          const p = prog(frame, at[i], 10);
          return (
            <div key={t.slug} style={{ width: 270, textAlign: "center", opacity: p, transform: `translateY(${(1 - p) * 80}px) scale(${0.7 + p * 0.3})` }}>
              <div style={{ width: 210, height: 210, margin: "0 auto", borderRadius: 32, background: "rgba(255,255,255,0.04)", border: `2px solid ${t.accent}55`, display: "grid", placeItems: "center", boxShadow: `0 0 50px ${t.accent}33` }}>
                <Img src={staticFile(`img/teams/${t.slug}.png`)} style={{ width: 170, height: 170, objectFit: "contain" }} />
              </div>
              <div style={{ fontFamily: FONT.sans, fontWeight: 800, fontSize: 30, color: C.cream, marginTop: 18 }}>{t.name}</div>
              <div style={{ fontFamily: FONT.sans, fontWeight: 700, fontSize: 20, color: t.accent, letterSpacing: 2 }}>[{t.tag}]</div>
            </div>
          );
        })}
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 880, textAlign: "center", fontFamily: FONT.sans, fontSize: 30, color: C.muted, opacity: prog(frame, 72, 10) }}>
        Captains add players with <b style={{ color: C.cream }}>/team</b> — or the roster follows your in-game clan.
      </div>
    </AbsoluteFill>
  );
};

const RULES = [
  { at: 121, big: "+10", line: "per ranked 1v1 win" },
  { at: 139, big: "+1", line: "per rating point gained" },
  { at: 156, big: "0", line: "for a loss — playing never hurts" },
  { at: 173, big: "TOP 5", line: "members count for the team" },
];

const Scoring: React.FC = () => {
  const frame = useCurrentFrame();
  const pulse = usePulse();
  const o = prog(frame, 118, 6) * (1 - prog(frame, 222, 6));
  return (
    <AbsoluteFill style={{ opacity: o }}>
      <div style={{ position: "absolute", left: 120, top: 140 }}>
        <Tag enter={119} color={C.amber}>How points work · this week</Tag>
        <div style={{ ...DISPLAY, fontSize: 100, marginTop: 20 }}>
          <MaskUp start={121}>Score from ranked</MaskUp>
        </div>
      </div>
      <div style={{ position: "absolute", left: 120, top: 400, display: "flex", gap: 30 }}>
        {RULES.map((r) => {
          const p = prog(frame, r.at, 8);
          const hit = frame >= r.at && frame < r.at + 8 ? 1 - (frame - r.at) / 8 : 0;
          return (
            <div
              key={r.big}
              style={{
                width: 395,
                height: 400,
                borderRadius: 28,
                padding: 34,
                background: "linear-gradient(160deg, rgba(48,26,18,0.95), rgba(20,13,12,0.95))",
                border: `1.5px solid rgba(233,185,73,${0.25 + hit * 0.6})`,
                boxShadow: `0 30px 80px rgba(0,0,0,0.5), 0 0 ${30 + hit * 60}px rgba(255,106,31,${0.15 + hit * 0.4})`,
                opacity: p,
                transform: `translateY(${(1 - p) * 70}px) scale(${1 + hit * 0.05})`,
                display: "flex",
                flexDirection: "column",
                justifyContent: "space-between",
              }}
            >
              <div style={{ ...DISPLAY, fontSize: r.big.length > 3 ? 120 : 170, color: r.big === "0" ? C.green : C.amber, letterSpacing: -4, textShadow: `0 0 ${20 + pulse * 30}px rgba(255,194,131,0.35)` }}>{r.big}</div>
              <div style={{ fontFamily: FONT.sans, fontWeight: 700, fontSize: 32, color: C.cream, lineHeight: 1.25 }}>{r.line}</div>
            </div>
          );
        })}
      </div>
      <div style={{ position: "absolute", left: 120, top: 860, fontFamily: FONT.sans, fontSize: 28, color: C.muted, opacity: prog(frame, 184, 8) }}>
        A big roster can't win on numbers alone. Nothing to report — scored automatically from ranked play.
      </div>
    </AbsoluteFill>
  );
};

const Standings: React.FC = () => {
  const frame = useCurrentFrame();
  const o = prog(frame, 225, 7) * (1 - prog(frame, 306, 6));
  const max = 70;
  return (
    <AbsoluteFill style={{ opacity: o }}>
      <div style={{ position: "absolute", left: 120, top: 120 }}>
        <Tag enter={226} color={C.green}>Real standings · week of Oct 12 · in progress</Tag>
        <div style={{ ...DISPLAY, fontSize: 92, marginTop: 20 }}>
          <MaskUp start={228}>This week</MaskUp>
        </div>
      </div>
      <div style={{ position: "absolute", left: 120, top: 330, width: 1100, display: "flex", flexDirection: "column", gap: 14 }}>
        {TEAMS.map((t, i) => {
          const p = prog(frame, 232 + i * 5, 10);
          const bar = interpolate(frame, [242 + i * 5, 266 + i * 5], [0, t.points / max], { ...clamp, easing: easeInOut });
          return (
            <div
              key={t.slug}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 22,
                height: 100,
                padding: "0 26px",
                borderRadius: 20,
                background: i === 0 ? "linear-gradient(90deg, rgba(255,46,58,0.22), rgba(30,16,14,0.9))" : "rgba(26,17,16,0.92)",
                border: i === 0 ? `1.5px solid rgba(255,46,58,0.6)` : `1px solid ${C.line}`,
                opacity: p,
                transform: `translateX(${(1 - p) * -80}px)`,
              }}
            >
              <div style={{ width: 54, height: 54, borderRadius: 14, display: "grid", placeItems: "center", fontFamily: FONT.sans, fontWeight: 900, fontSize: 26, color: "#fff", background: i === 0 ? `linear-gradient(135deg, ${C.red}, ${C.ember})` : "rgba(255,255,255,0.06)" }}>{i + 1}</div>
              <Img src={staticFile(`img/teams/${t.slug}.png`)} style={{ width: 64, height: 64, objectFit: "contain" }} />
              <div style={{ width: 330 }}>
                <div style={{ fontFamily: FONT.sans, fontWeight: 800, fontSize: 30, color: C.cream }}>{t.name}</div>
                <div style={{ fontFamily: FONT.sans, fontSize: 19, color: C.muted }}>[{t.tag}]{t.scorer ? ` · ${t.scorer}` : ""}</div>
              </div>
              <div style={{ flex: 1, height: 10, borderRadius: 5, background: "rgba(255,255,255,0.07)", overflow: "hidden" }}>
                <div style={{ width: `${bar * 100}%`, height: "100%", background: `linear-gradient(90deg, ${C.red}, ${C.ember})` }} />
              </div>
              <div style={{ width: 130, textAlign: "right", fontFamily: FONT.sans, fontWeight: 900, fontSize: 40, color: C.cream }}>
                <CountUp to={t.points} start={242 + i * 5} dur={24} />
                <span style={{ fontSize: 18, color: C.muted, fontWeight: 600, marginLeft: 6 }}>pts</span>
              </div>
            </div>
          );
        })}
      </div>
      <div style={{ position: "absolute", left: 1300, top: 340, width: 500 }}>
        <div style={{ borderRadius: 24, padding: 32, background: "rgba(26,17,16,0.92)", border: `1px solid ${C.line}`, opacity: prog(frame, 250, 10) }}>
          <div style={{ fontFamily: FONT.sans, fontWeight: 700, fontSize: 22, letterSpacing: 3, color: C.amber }}>THE WAR ENDS</div>
          <div style={{ ...DISPLAY, fontSize: 64, marginTop: 10 }}>Monday</div>
          <div style={{ ...DISPLAY, fontSize: 64, color: C.ember }}>00:00 PKT</div>
          <div style={{ fontFamily: FONT.sans, fontSize: 24, color: C.muted, marginTop: 20, lineHeight: 1.4 }}>
            Weekly wins build the season table. Check yours with <b style={{ color: C.cream }}>/clanwars</b> or the Clan Wars page.
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

const VERSUS = [
  { k: "You represent", city: "Your city", clan: "Your team" },
  { k: "Runs", city: "All season", clan: "Every week" },
  { k: "Scored by", city: "Avg. of best 5 ratings", clan: "Wins + rating gained, best 5" },
];

const Compare: React.FC = () => {
  const frame = useCurrentFrame();
  const o = prog(frame, 310, 6);
  const split = prog(frame, 310, 12, easeInOut);
  return (
    <AbsoluteFill style={{ opacity: o }}>
      <div style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: 960 * split, overflow: "hidden", background: "linear-gradient(160deg, rgba(1,65,28,0.55), rgba(10,6,6,0.9))" }} />
      <div style={{ position: "absolute", right: 0, top: 0, bottom: 0, width: 960 * split, overflow: "hidden", background: "linear-gradient(200deg, rgba(120,70,10,0.5), rgba(10,6,6,0.9))" }} />
      <div style={{ position: "absolute", left: 958, top: 0, bottom: 0, width: 4, background: C.cream, opacity: split, boxShadow: `0 0 30px ${C.amber}` }} />
      <div style={{ position: "absolute", left: 952 - 70, top: 120, width: 140, textAlign: "center", ...DISPLAY, fontSize: 60, color: C.cream, background: C.bg, borderRadius: 999, padding: "16px 0", opacity: prog(frame, 316, 6) }}>VS</div>
      {(["city", "clan"] as const).map((side, si) => (
        <div key={side} style={{ position: "absolute", left: si ? 1040 : 120, top: 240, width: 760 }}>
          <div style={{ ...DISPLAY, fontSize: 120, color: si ? C.amber : C.cream }}>
            <MaskUp start={314 + si * 4}>{si ? "Clan Wars" : "City Wars"}</MaskUp>
          </div>
          <div style={{ marginTop: 40, display: "flex", flexDirection: "column", gap: 26 }}>
            {VERSUS.map((v, i) => {
              const p = prog(frame, 322 + i * 6, 8);
              return (
                <div key={v.k} style={{ opacity: p, transform: `translateY(${(1 - p) * 20}px)` }}>
                  <div style={{ fontFamily: FONT.sans, fontWeight: 700, fontSize: 20, letterSpacing: 3, color: C.muted, textTransform: "uppercase" }}>{v.k}</div>
                  <div style={{ fontFamily: FONT.sans, fontWeight: 800, fontSize: 44, color: C.cream, marginTop: 4 }}>{side === "city" ? v.city : v.clan}</div>
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </AbsoluteFill>
  );
};

export const ClanWars: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{ background: C.bg, overflow: "hidden" }}>
      <AbsoluteFill style={{ opacity: frame < 310 ? 0.3 : 0.12 }}>
        <Img src={staticFile("img/warriors.jpg")} style={{ width: "100%", height: "100%", objectFit: "cover", filter: "blur(3px) sepia(0.4) saturate(1.3) hue-rotate(10deg)" }} />
      </AbsoluteFill>
      <AbsoluteFill style={{ background: "linear-gradient(180deg, rgba(10,6,6,0.55), rgba(10,6,6,0.94))" }} />
      <Embers count={55} seed={11} speed={1.4} />
      <Intro />
      <Teams />
      <Scoring />
      <Standings />
      <Compare />
      <SpeedBurst at={0} dur={14} color={C.gold} seed={21} />
      <Flash at={0} dur={9} color={C.gold} max={0.75} />
      <Streaks at={114} dur={8} dir={-1} color={C.gold} />
      <Streaks at={220} dur={8} color={C.gold} />
      <Flash at={310} dur={6} max={0.35} />
    </AbsoluteFill>
  );
};
