// A recreation of Discord's chat UI showing BRAWLISTAN's real /link replies
// (src/bot/content/profile_embeds.py). The code shown is an example.
import React from "react";
import { Img, staticFile } from "remotion";
import { C, FONT } from "../theme";

export const DC = {
  bg: "#313338",
  side: "#2b2d31",
  input: "#383a40",
  embed: "#2b2d31",
  text: "#dbdee1",
  muted: "#949ba4",
  link: "#00a8fc",
  forest: "#1b4332",
  gold: "#d4af37",
};

export const DiscordWindow: React.FC<{ width: number; height: number; channel?: string; children: React.ReactNode }> = ({ width, height, channel = "bot-commands", children }) => (
  <div style={{ width, height, borderRadius: 16, overflow: "hidden", background: DC.bg, fontFamily: FONT.sans, color: DC.text, boxShadow: "0 40px 120px rgba(0,0,0,0.7)", border: "1px solid rgba(255,255,255,0.08)", display: "flex", flexDirection: "column" }}>
    <div style={{ height: 58, display: "flex", alignItems: "center", gap: 12, padding: "0 22px", borderBottom: "1px solid rgba(0,0,0,0.35)", fontWeight: 700, fontSize: 22 }}>
      <span style={{ color: DC.muted, fontSize: 30, fontWeight: 400 }}>#</span>
      {channel}
      <span style={{ marginLeft: "auto", fontSize: 16, color: DC.muted, fontWeight: 600, letterSpacing: 1 }}>BRAWLISTAN DISCORD</span>
    </div>
    <div style={{ flex: 1, position: "relative", padding: "20px 24px", display: "flex", flexDirection: "column", justifyContent: "flex-end", gap: 16 }}>{children}</div>
  </div>
);

export const BotMessage: React.FC<{ children: React.ReactNode; note?: string }> = ({ children, note = "Only you can see this" }) => (
  <div style={{ display: "flex", gap: 16 }}>
    <Img src={staticFile("img/mark.png")} style={{ width: 48, height: 48, borderRadius: "50%", background: "#000" }} />
    <div style={{ flex: 1 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 22 }}>
        <strong style={{ color: "#fff" }}>BRAWLISTAN</strong>
        <span style={{ background: "#5865f2", color: "#fff", fontSize: 12, fontWeight: 700, padding: "1px 6px", borderRadius: 4 }}>APP</span>
        <span style={{ color: DC.muted, fontSize: 14 }}>Today</span>
      </div>
      <div style={{ marginTop: 6 }}>{children}</div>
      <div style={{ fontSize: 14, color: DC.muted, marginTop: 6 }}>👁 {note}</div>
    </div>
  </div>
);

export const Embed: React.FC<{ color: string; title: string; children: React.ReactNode; footer?: string; width?: number }> = ({ color, title, children, footer, width = 760 }) => (
  <div style={{ width, background: DC.embed, borderLeft: `5px solid ${color}`, borderRadius: 6, padding: "18px 24px", fontSize: 23, lineHeight: 1.45 }}>
    <div style={{ fontWeight: 700, color: "#fff", fontSize: 26, marginBottom: 8 }}>{title}</div>
    {children}
    {footer && <div style={{ fontSize: 17, color: DC.muted, marginTop: 12 }}>{footer}</div>}
  </div>
);

export const Code: React.FC<{ children: React.ReactNode; size?: number }> = ({ children, size = 18 }) => (
  <code style={{ fontFamily: FONT.mono, fontSize: size, background: "#1e1f22", padding: "2px 6px", borderRadius: 4, color: "#e3e5e8" }}>{children}</code>
);

export const InputBar: React.FC<{ text: string; caret: boolean }> = ({ text, caret }) => (
  <div style={{ height: 64, borderRadius: 10, background: DC.input, display: "flex", alignItems: "center", padding: "0 18px", fontSize: 26, gap: 10 }}>
    <span style={{ width: 26, height: 26, borderRadius: "50%", background: DC.muted, color: DC.input, display: "grid", placeItems: "center", fontWeight: 900 }}>+</span>
    <span style={{ color: text ? DC.text : DC.muted }}>
      {text || "Message #bot-commands"}
      {caret && <span style={{ display: "inline-block", width: 2, height: 24, background: "#fff", marginLeft: 2, verticalAlign: "middle" }} />}
    </span>
  </div>
);

export const CommandPopup: React.FC<{ name: string; description: string; option?: string; optionHint?: string }> = ({ name, description, option, optionHint }) => (
  <div style={{ background: DC.side, borderRadius: 10, padding: 14, boxShadow: "0 10px 30px rgba(0,0,0,0.4)" }}>
    <div style={{ fontSize: 13, fontWeight: 700, color: DC.muted, letterSpacing: 1, marginBottom: 8 }}>BRAWLISTAN</div>
    <div style={{ display: "flex", alignItems: "baseline", gap: 12, background: "rgba(255,255,255,0.06)", borderRadius: 6, padding: "10px 12px" }}>
      <strong style={{ color: "#fff", fontSize: 26 }}>/{name}</strong>
      {option && <span style={{ color: DC.muted, fontSize: 20, border: `1px solid ${DC.muted}`, borderRadius: 4, padding: "0 6px" }}>{option}</span>}
      <span style={{ color: DC.muted, fontSize: 22 }}>{description}</span>
    </div>
    {optionHint && <div style={{ fontSize: 20, color: DC.muted, marginTop: 10, paddingLeft: 12 }}>{optionHint}</div>}
  </div>
);

export const Gold = C.gold;
