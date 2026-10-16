// Scene 4 (27.7–40.4 s): City Wars (ADR-128/130). Real rules: linked players
// pick one of 17 fixed cities with /city set; a city's score is the average of
// its best 5 placed 1v1 ratings this season. The score demo uses clearly
// labelled illustrative numbers; the standings shown are the real page.
import React from "react";
import { AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame } from "remotion";
import { clamp, easeInOut, easeOut, prog, shake } from "../anim";
import { BotMessage, DC, DiscordWindow, InputBar } from "../components/discord";
import { Embers, Flash, FlagRibbon, SpeedBurst, Streaks, Tag, usePulse } from "../components/fx";
import { ACCENT, CountUp, DISPLAY, MaskUp, Slam, typed } from "../components/type";
import { Browser, Shot } from "../components/ui";
import { C, FONT, SITE } from "../theme";

// The fixed list from src/services/cities.py.
const CITIES = [
  "Karachi", "Lahore", "Islamabad / Rawalpindi", "Faisalabad", "Multan", "Peshawar", "Quetta", "Hyderabad", "Sialkot",
  "Gujranwala", "Bahawalpur", "Sukkur", "Abbottabad", "Mardan", "Sargodha", "Azad Kashmir", "Gilgit-Baltistan",
];
const DROP = 35;

const Intro: React.FC = () => {
  const frame = useCurrentFrame();
  const pulse = usePulse();
  const idx = Math.min(CITIES.length - 1, Math.floor(frame / 2));
  const s = shake(frame, DROP, 24, 3);
  const out = prog(frame, 80, 8);
  return (
    <AbsoluteFill style={{ opacity: 1 - out, transform: `translate(${s.x}px, ${s.y}px) scale(${1 + out * 0.1})` }}>
      {frame < DROP && (
        <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
          <div style={{ ...ACCENT, fontSize: 170, color: idx % 2 ? C.cream : C.amber, opacity: 0.4 + 0.6 * (frame / DROP) }}>{CITIES[idx]}</div>
        </AbsoluteFill>
      )}
      <FlagRibbon progress={prog(frame, 6, 30, easeInOut)} top={985} angle={-3} opacity={0.85} />
      {frame >= DROP && (
        <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", flexDirection: "column" }}>
          <Slam at={DROP} from={2.8}>
            <div style={{ ...DISPLAY, fontSize: 290, letterSpacing: -6, textShadow: `0 0 ${40 + pulse * 60}px rgba(255,106,31,0.5)` }}>
              City <span style={{ color: C.ember }}>Wars</span>
            </div>
          </Slam>
          <div style={{ fontFamily: FONT.serif, fontStyle: "italic", fontSize: 76, color: C.amber, marginTop: 10, opacity: prog(frame, 50, 10) }}>
            Which city rules the arena?
          </div>
        </AbsoluteFill>
      )}
    </AbsoluteFill>
  );
};

/** /city set, with the real choice list and the bot's real reply. */
const Represent: React.FC = () => {
  const frame = useCurrentFrame();
  const o = prog(frame, 84, 8) * (1 - prog(frame, 168, 6));
  const cmd = typed(frame, 92, "/city set", 16);
  const listOpen = frame >= 104 && frame < 140;
  const scroll = interpolate(frame, [106, 130], [0, 1], { ...clamp, easing: easeInOut });
  const pick = "Lahore"; // example choice
  const picked = frame >= 132;
  const reply = frame >= 142;
  const visible = CITIES.slice(0, 8);
  return (
    <AbsoluteFill style={{ opacity: o }}>
      <div style={{ position: "absolute", left: 110, top: 250, width: 640 }}>
        <Tag enter={86} color={C.ember}>Join or represent</Tag>
        <div style={{ ...DISPLAY, fontSize: 120, marginTop: 24 }}>
          <MaskUp start={88}>Represent</MaskUp>
        </div>
        <div style={{ ...DISPLAY, fontSize: 120 }}>
          <MaskUp start={95}>
            your <span style={{ ...ACCENT, fontSize: 140 }}>city</span>
          </MaskUp>
        </div>
        <div style={{ fontFamily: FONT.sans, fontSize: 30, color: C.muted, marginTop: 30, lineHeight: 1.4, opacity: prog(frame, 104, 10) }}>
          Once you're linked, pick one of <b style={{ color: C.cream }}>17 cities and regions</b> with <b style={{ color: C.cream }}>/city set</b>. Change it any time with <b style={{ color: C.cream }}>/city clear</b>.
        </div>
      </div>
      <div style={{ position: "absolute", left: 830, top: 200, transform: `translateX(${(1 - prog(frame, 84, 14)) * 120}px)` }}>
        <DiscordWindow width={1000} height={680}>
          {reply && (
            <div style={{ opacity: prog(frame, 142, 8) }}>
              <BotMessage>
                <div style={{ fontSize: 25, lineHeight: 1.45 }}>
                  🏙️ You now represent <b style={{ color: "#fff" }}>{pick}</b> on City Wars. It counts once you're placed this season.
                </div>
              </BotMessage>
            </div>
          )}
          {listOpen && (
            <div style={{ background: DC.side, borderRadius: 10, padding: 12, height: 360, overflow: "hidden" }}>
              <div style={{ fontSize: 15, fontWeight: 700, color: DC.muted, letterSpacing: 1, margin: "0 0 8px 8px" }}>CITY — YOUR CITY</div>
              <div style={{ transform: `translateY(${-scroll * 0}px)` }}>
                {visible.map((c) => {
                  const on = picked ? c === pick : c === visible[Math.min(visible.length - 1, Math.floor(scroll * 2))];
                  return (
                    <div key={c} style={{ padding: "6px 12px", borderRadius: 6, fontSize: 23, color: on ? "#fff" : DC.text, background: on ? "rgba(88,101,242,0.35)" : "transparent" }}>
                      {c}
                    </div>
                  );
                })}
                <div style={{ padding: "6px 12px", fontSize: 18, color: DC.muted }}>+ 9 more…</div>
              </div>
            </div>
          )}
          <InputBar text={frame < 140 ? (picked ? `/city set city: ${pick}` : cmd + (frame >= 104 ? " city:" : "")) : ""} caret={frame < 140 && Math.floor(frame / 8) % 2 === 0} />
        </DiscordWindow>
        {reply && (
          <div style={{ position: "absolute", right: 20, top: -24 }}>
            <Tag enter={146}>Example pick</Tag>
          </div>
        )}
      </div>
    </AbsoluteFill>
  );
};

const RATINGS = [1850, 1790, 1720, 1680, 1610]; // illustrative
const AVG = Math.round(RATINGS.reduce((a, b) => a + b, 0) / RATINGS.length);

const Score: React.FC = () => {
  const frame = useCurrentFrame();
  const o = prog(frame, 172, 8) * (1 - prog(frame, 256, 6));
  const merge = prog(frame, 222, 16, easeInOut);
  const max = 1900;
  return (
    <AbsoluteFill style={{ opacity: o }}>
      <div style={{ position: "absolute", left: 110, top: 150 }}>
        <Tag enter={173} color={C.ember}>How a city scores</Tag>
        <div style={{ ...DISPLAY, fontSize: 96, marginTop: 22 }}>
          <MaskUp start={175}>Your city's</MaskUp>
        </div>
        <div style={{ ...DISPLAY, fontSize: 96 }}>
          <MaskUp start={180}>
            best <span style={{ color: C.ember }}>5</span> count
          </MaskUp>
        </div>
        <div style={{ fontFamily: FONT.sans, fontSize: 32, color: C.muted, marginTop: 30, width: 740, lineHeight: 1.4, opacity: prog(frame, 190, 10) }}>
          Score = the <b style={{ color: C.cream }}>average of its best 5 placed 1v1 ratings</b> this season. One star and a big city compete fairly.
        </div>
        <div style={{ fontFamily: FONT.sans, fontSize: 24, color: C.muted, marginTop: 18, opacity: prog(frame, 205, 10) }}>
          Unplaced players and players without a city don't count.
        </div>
      </div>
      <div style={{ position: "absolute", left: 1000, top: 200, width: 800, height: 620 }}>
        <div style={{ position: "absolute", right: 0, top: -30 }}>
          <Tag enter={180}>Illustrative values</Tag>
        </div>
        {RATINGS.map((r, i) => {
          const p = prog(frame, 186 + i * 5, 12);
          const h = (r / max) * 420 * p;
          const x = interpolate(merge, [0, 1], [i * 150, 300]);
          return (
            <div key={i} style={{ position: "absolute", left: x, bottom: 120, width: 110, height: h, borderRadius: "14px 14px 4px 4px", background: `linear-gradient(180deg, ${C.ember}, ${C.red})`, opacity: (1 - merge) * Math.min(1, p * 2), boxShadow: "0 0 30px rgba(255,46,58,0.35)" }}>
              <div style={{ position: "absolute", top: -40, width: "100%", textAlign: "center", fontFamily: FONT.sans, fontWeight: 800, fontSize: 28, color: C.cream, opacity: (1 - merge) * p }}>{r.toLocaleString("en-US")}</div>
              <div style={{ position: "absolute", bottom: -44, width: "100%", textAlign: "center", fontFamily: FONT.sans, fontWeight: 700, fontSize: 22, color: C.muted, opacity: (1 - merge) * p }}>#{i + 1}</div>
            </div>
          );
        })}
        {merge > 0.6 && (
          <div style={{ position: "absolute", left: 120, top: 110, width: 470, textAlign: "center", opacity: prog(frame, 232, 8) }}>
            <div style={{ fontFamily: FONT.sans, fontWeight: 700, fontSize: 26, letterSpacing: 4, color: C.amber }}>CITY SCORE</div>
            <div style={{ ...DISPLAY, fontSize: 190, color: C.cream, textShadow: "0 0 50px rgba(255,106,31,0.6)" }}>
              <CountUp to={AVG} start={232} dur={14} />
            </div>
          </div>
        )}
      </div>
    </AbsoluteFill>
  );
};

/** The real City Wars page (snapshot of the live data). */
const RealPage: React.FC = () => {
  const frame = useCurrentFrame();
  const o = prog(frame, 258, 8);
  const W = 1500;
  const k = W / 2400;
  // Camera over the 2400 px capture: whole page, then the hero, then the podium and standings.
  const keys = [258, 288, 336];
  const z = interpolate(frame, keys, [1, 1.6, 1.6], { ...clamp, easing: easeInOut });
  const tx = interpolate(frame, keys, [0, -643, -643], { ...clamp, easing: easeInOut });
  const ty = interpolate(frame, keys, [0, -160, -560], { ...clamp, easing: easeInOut });
  void k;
  return (
    <AbsoluteFill style={{ opacity: o }}>
      <div style={{ position: "absolute", left: 210, top: 120, transform: `translateY(${(1 - prog(frame, 258, 14)) * 80}px)` }}>
        <Browser url={`${SITE}/cities.html`} width={W}>
          <div style={{ height: 760, overflow: "hidden" }}>
            <div style={{ transform: `translate(${tx}px, ${ty}px) scale(${z})`, transformOrigin: "0 0" }}>
              <Shot name="cities-full" width={W} />
            </div>
          </div>
        </Browser>
      </div>
      <div style={{ position: "absolute", left: 210, top: 950, display: "flex", gap: 16, alignItems: "center" }}>
        <Tag enter={266} color={C.ember}>Live standings</Tag>
        <div style={{ fontFamily: FONT.sans, fontSize: 28, color: C.cream, opacity: prog(frame, 270, 10) }}>
          City Wars page · Rankings → Cities tab · <code style={{ fontFamily: FONT.mono, color: C.amber }}>/rankings board:city</code>
        </div>
      </div>
    </AbsoluteFill>
  );
};

export const CityWars: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{ background: C.bg, overflow: "hidden" }}>
      <AbsoluteFill style={{ opacity: 0.22 }}>
        <Img src={staticFile("img/banner.jpg")} style={{ width: "100%", height: "100%", objectFit: "cover", filter: "blur(2px) saturate(1.1)" }} />
      </AbsoluteFill>
      <AbsoluteFill style={{ background: "linear-gradient(180deg, rgba(10,6,6,0.6), rgba(10,6,6,0.92))" }} />
      <Embers count={60} seed={8} green speed={1.3} />
      <Intro />
      <Represent />
      <Score />
      <RealPage />
      <SpeedBurst at={DROP} dur={14} color={C.amber} />
      <Flash at={DROP} dur={9} color={C.ember} max={0.8} />
      <Streaks at={80} dur={9} />
      <Streaks at={166} dur={9} dir={-1} />
      <Streaks at={252} dur={9} />
    </AbsoluteFill>
  );
};
