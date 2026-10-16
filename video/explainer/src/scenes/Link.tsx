// Scene 3 (12.7–27.7 s): link your player profile, step by step, following the
// real website-claim flow (ADR-107): Discord -> /link (no ID) -> one-time code
// -> "Claim this profile" on your player page -> linked. Uses the real UI
// captured from player.html with a clearly labelled demo profile.
import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { clamp, easeInOut, easeOut, prog } from "../anim";
import { BotMessage, Code, CommandPopup, DC, DiscordWindow, Embed, InputBar } from "../components/discord";
import { Embers, Flash, Streaks, Tag, usePulse } from "../components/fx";
import { ACCENT, DISPLAY, MaskUp, typed } from "../components/type";
import { Browser, Cursor, Highlight, Shot } from "../components/ui";
import { C, FONT, SITE } from "../theme";

export const LINK_STEPS = [
  { at: 45, title: "Join the Discord", sub: "BRAWLISTAN's server is where you link." },
  { at: 104, title: "Run /link", sub: "Leave the ID empty to get a one-time code." },
  { at: 225, title: "Claim your profile", sub: "Find yourself on Players, open your profile, enter the code." },
  { at: 329, title: "You're linked", sub: "Your Discord and Brawlhalla account are connected." },
];

const STAGE = { x: 640, y: 150 };

const Rail: React.FC = () => {
  const frame = useCurrentFrame();
  const o = prog(frame, 38, 10);
  const activeIndex = LINK_STEPS.reduce((acc, s, i) => (frame >= s.at ? i : acc), 0);
  return (
    <div style={{ position: "absolute", left: 80, top: 150, width: 500, opacity: o, transform: `translateX(${(1 - o) * -40}px)` }}>
      <Tag color={C.ember}>Step by step</Tag>
      <div style={{ ...DISPLAY, fontSize: 64, marginTop: 18, lineHeight: 0.95 }}>
        Link your <span style={{ ...ACCENT, fontSize: 76 }}>profile</span>
      </div>
      <div style={{ marginTop: 44, display: "flex", flexDirection: "column", gap: 22 }}>
        {LINK_STEPS.map((s, i) => {
          const on = i === activeIndex;
          const done = i < activeIndex;
          const p = prog(frame, s.at - 4, 8);
          return (
            <div key={s.title} style={{ display: "flex", gap: 18, alignItems: "flex-start", opacity: on ? 1 : done ? 0.55 : 0.3, transform: `translateX(${on ? 8 * p : 0}px)` }}>
              <div
                style={{
                  flex: "0 0 auto",
                  width: 52,
                  height: 52,
                  borderRadius: 14,
                  display: "grid",
                  placeItems: "center",
                  fontFamily: FONT.sans,
                  fontWeight: 900,
                  fontSize: 26,
                  color: on ? "#fff" : C.cream,
                  background: on ? `linear-gradient(135deg, ${C.red}, ${C.ember})` : done ? "rgba(61,242,110,0.15)" : "rgba(255,255,255,0.06)",
                  border: done ? `1.5px solid ${C.green}` : "1px solid rgba(255,255,255,0.12)",
                  boxShadow: on ? `0 0 30px rgba(255,46,58,0.6)` : "none",
                }}
              >
                {done ? <span style={{ color: C.green }}>✓</span> : i + 1}
              </div>
              <div>
                <div style={{ fontFamily: FONT.sans, fontWeight: 800, fontSize: 30, color: C.cream }}>{s.title}</div>
                <div style={{ fontFamily: FONT.sans, fontSize: 21, color: C.muted, marginTop: 4, lineHeight: 1.35, maxHeight: on ? 120 : 0, overflow: "hidden", opacity: on ? p : 0 }}>{s.sub}</div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

/** Step 1: the real "Join Discord" button on the site's top bar. */
const StepJoin: React.FC = () => {
  const frame = useCurrentFrame();
  const W = 1180;
  const s = W / 2400;
  const bx = 2047 * s;
  const by = 116 * s;
  const zoom = interpolate(frame, [52, 78], [1, 2.3], { ...clamp, easing: easeInOut });
  const o = prog(frame, 45, 8) * (1 - prog(frame, 100, 5));
  const enter = prog(frame, 45, 12);
  const screenX = STAGE.x + bx;
  const screenY = STAGE.y + 46 + by;
  return (
    <div style={{ position: "absolute", left: STAGE.x, top: STAGE.y, opacity: o, transform: `translateY(${(1 - enter) * 60}px)` }}>
      <Browser url={SITE} width={W}>
        <div style={{ transform: `scale(${zoom})`, transformOrigin: `${bx}px ${by}px` }}>
          <Shot name="home" width={W} />
        </div>
      </Browser>
      <div style={{ position: "absolute", left: 0, top: 0 }}>
        <Highlight x={bx - 100 * 2.3 / 2.3 * 1.0 - 10} y={46 + by - 28} w={210} h={56} start={80} radius={30} />
      </div>
      <div style={{ position: "absolute", left: -STAGE.x, top: -STAGE.y }}>
        <Cursor keys={[{ f: 60, x: 1300, y: 760 }, { f: 82, x: screenX - 10, y: screenY + 4 }]} clicks={[86]} appear={58} />
      </div>
    </div>
  );
};

const LINK_CODE = "ABCD-EFGH"; // example code, not a real one

/** Step 2: /link in Discord returns the one-time code (real embed text). */
const StepCommand: React.FC = () => {
  const frame = useCurrentFrame();
  const o = prog(frame, 104, 8) * (1 - prog(frame, 221, 5));
  const typedText = frame < 150 ? typed(frame, 112, "/link", 11) : "";
  const showPopup = frame >= 118 && frame < 150;
  const used = frame >= 152;
  const reply = frame >= 160;
  const r = prog(frame, 160, 10);
  return (
    <div style={{ position: "absolute", left: STAGE.x + 20, top: STAGE.y + 10, opacity: o, transform: `scale(${0.96 + prog(frame, 104, 14) * 0.04})` }}>
      <DiscordWindow width={1140} height={740}>
        {used && (
          <div style={{ fontSize: 19, color: DC.muted, marginLeft: 64, marginBottom: -8 }}>
            ↱ <span style={{ color: "#fff", fontWeight: 600 }}>you</span> used <span style={{ color: DC.link }}>/link</span>
          </div>
        )}
        {reply && (
          <div style={{ opacity: r, transform: `translateY(${(1 - r) * 30}px)` }}>
            <BotMessage>
              <Embed color={DC.forest} title="🔗 Your BRAWLISTAN link code" footer="Never share this code. Staff will never ask for it." width={960}>
                <div style={{ margin: "6px 0 10px" }}>
                  <Code size={58}>{LINK_CODE}</Code>
                </div>
                <div>Expires in 15 minutes. Only this code works; asking for another replaces it.</div>
                <div style={{ marginTop: 10 }}>
                  <b>1.</b> Find yourself on <span style={{ color: DC.link }}>{SITE}/players</span>.<br />
                  <b>2.</b> Open your profile and choose <b>Claim this profile</b>.<br />
                  <b>3.</b> Enter the code.
                </div>
              </Embed>
            </BotMessage>
          </div>
        )}
        {showPopup && (
          <CommandPopup
            name="link"
            option="identifier"
            description="Link your Discord account to your Brawlhalla profile"
            optionHint="identifier — Your Brawlhalla or Steam64 ID — or leave empty for a website link code"
          />
        )}
        <InputBar text={typedText} caret={frame < 152 && Math.floor(frame / 8) % 2 === 0} />
      </DiscordWindow>
      {reply && (
        <div style={{ position: "absolute", left: 720, top: 150 }}>
          <Tag enter={172}>Example code</Tag>
        </div>
      )}
      <div style={{ position: "absolute", right: -10, bottom: -60 }}>
        <Tag enter={186} color={C.cream}>One-time · 15 minutes · single use</Tag>
      </div>
    </div>
  );
};

/** Step 3: the real claim form on a player page (demo profile). */
const StepClaim: React.FC = () => {
  const frame = useCurrentFrame();
  const W = 1140;
  const k = W / 1503; // element captures are 1503 px wide
  const o = prog(frame, 225, 8) * (1 - prog(frame, 326, 4));
  const panelTop = 24 + 213 * k + 22; // inside the page area, below the browser bar
  const state = frame < 262 ? "claim-1-form" : frame < 292 ? "claim-2-typed" : "claim-3-linked";
  // Camera: push in on the claim panel once the page has been seen.
  const z = interpolate(frame, [236, 252], [1, 1.55], { ...clamp, easing: easeInOut });
  const origin = { x: 24, y: panelTop + 120 * k };
  const toScreen = (pt: { x: number; y: number }) => ({
    x: STAGE.x + origin.x + (pt.x - origin.x) * z,
    y: STAGE.y + 46 + origin.y + (pt.y - origin.y) * z,
  });
  const input = toScreen({ x: 24 + 195 * k, y: panelTop + 197 * k });
  const btn = toScreen({ x: 24 + 475 * k, y: panelTop + 199 * k });
  const linked = frame >= 292;
  const glow = linked ? Math.exp(-(frame - 292) / 14) : 0;
  return (
    <>
      <div style={{ position: "absolute", left: STAGE.x, top: STAGE.y, opacity: o }}>
        <Browser url={`${SITE}/player/yourname-10000001/`} width={W + 48}>
          <div style={{ height: 560, background: "linear-gradient(180deg, #120c0c, #0d0909)" }}>
            <div style={{ padding: 24, transform: `scale(${z})`, transformOrigin: `${origin.x}px ${origin.y}px` }}>
              <Shot name="claim-head" width={W} style={{ borderRadius: 14 }} />
              <div style={{ height: 22 }} />
              <div style={{ position: "relative", borderRadius: 14, boxShadow: linked ? `0 0 ${40 + glow * 60}px rgba(61,242,110,${0.25 + glow * 0.5})` : "none" }}>
                <Shot name={state} width={W} style={{ borderRadius: 14 }} />
              </div>
            </div>
          </div>
        </Browser>
        <div style={{ position: "absolute", right: 24, top: 70 }}>
          <Tag enter={232} color={C.amber}>Demo profile</Tag>
        </div>
      </div>
      <Highlight x={btn.x - 78 * z} y={btn.y - 22 * z} w={156 * z} h={44 * z} start={270} end={292} radius={30} />
      {linked && (
        <div style={{ position: "absolute", left: STAGE.x + 40, top: STAGE.y + 600 }}>
          <Tag enter={296} color={C.green}>Claim accepted — the site updates within a few hours</Tag>
        </div>
      )}
      {frame < 330 && (
        <Cursor
          keys={[
            { f: 230, x: 1500, y: 900 },
            { f: 254, x: input.x, y: input.y },
            { f: 268, x: input.x + 20, y: input.y + 6 },
            { f: 282, x: btn.x, y: btn.y },
          ]}
          clicks={[256, 286]}
          appear={230}
          vanish={318}
        />
      )}
    </>
  );
};

/** Step 4: what linking gives you. */
const StepLinked: React.FC = () => {
  const frame = useCurrentFrame();
  const pulse = usePulse();
  const o = prog(frame, 329, 8);
  const card = prog(frame, 331, 14);
  const items = [
    { at: 346, icon: "🇵🇰", text: "You're on the BRAWLISTAN Pakistan rankings" },
    { at: 364, icon: "◆", text: "Your profile shows Claimed — staff can mark it ✓ Verified" },
    { at: 381, icon: "↻", text: "Your rating syncs every 6 hours" },
    { at: 398, icon: "→", text: "Next: pick your city and play for your team" },
  ];
  return (
    <div style={{ position: "absolute", left: STAGE.x, top: STAGE.y + 10, width: 1200, height: 760, opacity: o }}>
      <div
        style={{
          position: "absolute",
          left: 0,
          top: 40,
          width: 440,
          padding: 34,
          borderRadius: 26,
          background: "linear-gradient(160deg, rgba(40,22,20,0.95), rgba(18,12,12,0.95))",
          border: `1.5px solid rgba(61,242,110,${0.3 + pulse * 0.3})`,
          boxShadow: `0 30px 90px rgba(0,0,0,0.6), 0 0 ${40 + pulse * 30}px rgba(61,242,110,0.18)`,
          transform: `perspective(1200px) rotateY(${(1 - card) * -40}deg) translateX(${(1 - card) * -80}px)`,
          opacity: card,
          fontFamily: FONT.sans,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
          <div style={{ width: 96, height: 96, borderRadius: "50%", background: "#3b1d63", display: "grid", placeItems: "center", fontSize: 46, fontWeight: 800, color: C.cream }}>Y</div>
          <div>
            <div style={{ fontSize: 40, fontWeight: 800, color: C.cream }}>YourName</div>
            <div style={{ fontSize: 20, color: C.muted, marginTop: 4 }}>🇵🇰 Pakistan · Brawlhalla ID</div>
          </div>
        </div>
        <div style={{ display: "flex", gap: 12, marginTop: 26, flexWrap: "wrap" }}>
          <span style={{ padding: "8px 16px", borderRadius: 999, border: `1.5px solid ${C.ember}`, color: C.amber, fontWeight: 700, fontSize: 20, opacity: prog(frame, 346, 8) }}>Claimed</span>
          <span style={{ padding: "8px 16px", borderRadius: 999, border: `1.5px dashed ${C.green}`, color: C.green, fontWeight: 700, fontSize: 20, opacity: prog(frame, 364, 8) * 0.9 }}>✓ Verified (by staff)</span>
        </div>
        <div style={{ marginTop: 26, height: 1, background: C.line }} />
        <div style={{ marginTop: 18, fontSize: 19, color: C.muted, lineHeight: 1.4 }}>
          Linking proves you own the Discord account. Staff <Code>/verify</Code> confirms the Brawlhalla account.
        </div>
        <div style={{ position: "absolute", top: -18, right: 24 }}>
          <Tag enter={333} color={C.amber} style={{ fontSize: 15 }}>Demo profile</Tag>
        </div>
      </div>
      <div style={{ position: "absolute", left: 500, top: 60, width: 700 }}>
        <div style={{ ...DISPLAY, fontSize: 84, color: C.green, textShadow: "0 0 40px rgba(61,242,110,0.45)" }}>
          <MaskUp start={331}>Linked.</MaskUp>
        </div>
        <div style={{ marginTop: 30, display: "flex", flexDirection: "column", gap: 20 }}>
          {items.map((it) => {
            const p = prog(frame, it.at, 9);
            return (
              <div key={it.text} style={{ display: "flex", gap: 18, alignItems: "center", fontFamily: FONT.sans, fontSize: 29, fontWeight: 600, color: C.cream, opacity: p, transform: `translateX(${(1 - p) * 60}px)` }}>
                <span style={{ width: 48, height: 48, flex: "0 0 auto", borderRadius: 12, display: "grid", placeItems: "center", background: "rgba(255,106,31,0.12)", color: C.amber, fontSize: 24 }}>{it.icon}</span>
                {it.text}
              </div>
            );
          })}
        </div>
      </div>
      <div style={{ position: "absolute", left: 0, top: 650, opacity: prog(frame, 412, 10), fontFamily: FONT.sans, fontSize: 24, color: C.muted }}>
        Discord-only route: <Code size={22}>/link &lt;Brawlhalla or Steam64 ID&gt;</Code> → check the player → <b style={{ color: C.cream }}>Confirm</b>
      </div>
    </div>
  );
};

export const Link: React.FC = () => {
  const frame = useCurrentFrame();
  const introOut = prog(frame, 32, 8, easeOut);
  return (
    <AbsoluteFill style={{ background: C.bg, overflow: "hidden" }}>
      <AbsoluteFill style={{ background: "radial-gradient(ellipse at 70% 40%, rgba(255,46,58,0.13), transparent 60%)" }} />
      <Embers count={30} seed={6} opacity={0.4} />
      {frame < 42 && (
        <AbsoluteFill style={{ justifyContent: "center", paddingLeft: 140, opacity: 1 - introOut, transform: `scale(${1 + introOut * 0.08})` }}>
          <Tag enter={0} color={C.ember} style={{ alignSelf: "flex-start" }}>Step 1 of getting started</Tag>
          <div style={{ ...DISPLAY, fontSize: 200, marginTop: 24 }}>
            <MaskUp start={0} dur={7}>Link your</MaskUp>
          </div>
          <div style={{ ...DISPLAY, fontSize: 200 }}>
            <MaskUp start={8} dur={7}>
              <span style={{ ...ACCENT, fontSize: 240 }}>profile.</span>
            </MaskUp>
          </div>
        </AbsoluteFill>
      )}
      <Rail />
      <StepJoin />
      <StepCommand />
      <StepClaim />
      <StepLinked />
      <Streaks at={100} dur={8} />
      <Streaks at={221} dur={8} dir={-1} />
      <Flash at={292} dur={8} color={C.green} max={0.25} />
    </AbsoluteFill>
  );
};
