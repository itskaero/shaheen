// End card for the Discord recruitment trailer (video/recruitment/). Rendered
// as stills to drop into CapCut, so the logo, invite and URL are exact rather
// than AI-generated. `showInvite: false` leaves the CTA slot empty for a
// different invite or QR.
import React from "react";
import { AbsoluteFill, Img, staticFile } from "remotion";
import "./fonts";
import { FONT } from "./theme";

export const INVITE = "discord.gg/UXVDWxBzy"; // web/assets/js/config.js
const SITE = "brawlistan.rekorex.online";
const EMERALD = "#1ee08a";
const GREEN = "#3df26e";
const CREAM = "#fbf9d8";

type Props = { vertical: boolean; showInvite: boolean };

export const EndCard: React.FC<Props> = ({ vertical, showInvite }) => {
  const W = vertical ? 1080 : 1920;
  const cta = (
    <div
      style={{
        width: vertical ? 900 : 900,
        padding: vertical ? "44px 44px" : "40px 44px",
        borderRadius: 36,
        background: "linear-gradient(160deg, rgba(10,40,26,0.92), rgba(6,14,10,0.94))",
        border: `3px solid ${EMERALD}`,
        boxShadow: `0 0 80px rgba(30,224,138,0.35), inset 0 0 40px rgba(30,224,138,0.08)`,
        display: "flex",
        flexDirection: vertical ? "column" : "row",
        alignItems: "center",
        gap: vertical ? 34 : 40,
      }}
    >
      <div style={{ flex: 1, textAlign: vertical ? "center" : "left" }}>
        <div style={{ fontFamily: FONT.sans, fontWeight: 900, fontSize: vertical ? 70 : 54, lineHeight: 0.98, color: CREAM, textTransform: "uppercase", letterSpacing: -1.5 }}>
          Join the<br />
          <span style={{ color: GREEN }}>BRAWLISTAN</span> Discord
        </div>
        <div
          style={{
            marginTop: 26,
            display: "inline-block",
            padding: "14px 26px",
            borderRadius: 18,
            background: showInvite ? "#5865f2" : "transparent",
            border: showInvite ? "none" : `3px dashed rgba(251,249,216,0.45)`,
            fontFamily: FONT.sans,
            fontWeight: 800,
            fontSize: vertical ? 48 : 38,
            color: showInvite ? "#fff" : "rgba(251,249,216,0.55)",
            minWidth: vertical ? 620 : 0,
            textAlign: "center",
          }}
        >
          {showInvite ? INVITE : "discord.gg/your-invite"}
        </div>
      </div>
      <div
        style={{
          width: vertical ? 290 : 250,
          height: vertical ? 290 : 250,
          flex: "0 0 auto",
          borderRadius: 26,
          background: showInvite ? "#fff" : "transparent",
          border: showInvite ? "none" : `3px dashed rgba(251,249,216,0.45)`,
          display: "grid",
          placeItems: "center",
          fontFamily: FONT.sans,
          fontWeight: 700,
          fontSize: 28,
          color: "rgba(251,249,216,0.55)",
        }}
      >
        {showInvite ? <Img src={staticFile("img/discord-qr.png")} style={{ width: "94%", height: "94%" }} /> : "QR CODE"}
      </div>
    </div>
  );

  return (
    <AbsoluteFill style={{ background: "#040806", overflow: "hidden" }}>
      <AbsoluteFill>
        <Img src={staticFile("img/hero-scene.jpg")} style={{ width: "100%", height: "100%", objectFit: "cover", filter: "brightness(0.32) saturate(1.2) blur(2px)" }} />
      </AbsoluteFill>
      <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% ${vertical ? 30 : 40}%, rgba(30,224,138,0.22), transparent 60%), linear-gradient(180deg, rgba(4,8,6,0.2), rgba(4,8,6,0.85))` }} />
      {vertical ? (
        <AbsoluteFill style={{ alignItems: "center", paddingTop: 100 }}>
          <Img src={staticFile("img/logo.png")} style={{ width: 540, filter: "drop-shadow(0 0 50px rgba(61,242,110,0.35))" }} />
          <div style={{ marginTop: 24, fontFamily: FONT.sans, fontWeight: 900, fontSize: 62, color: CREAM, textTransform: "uppercase", letterSpacing: -1, textAlign: "center", lineHeight: 1 }}>
            Your community<br />is waiting.
          </div>
          <div style={{ marginTop: 40 }}>{cta}</div>
          <div style={{ marginTop: 32, fontFamily: FONT.sans, fontWeight: 700, fontSize: 36, color: "rgba(251,249,216,0.8)", letterSpacing: 1 }}>{SITE}</div>
          <div style={{ marginTop: 10, fontFamily: FONT.urdu, fontSize: 34, color: EMERALD, direction: "rtl" }}>بلندیوں کی جانب</div>
        </AbsoluteFill>
      ) : (
        <AbsoluteFill style={{ flexDirection: "row", alignItems: "center", padding: "0 90px", gap: 50 }}>
          <div style={{ width: 760, flex: "0 0 auto", display: "flex", flexDirection: "column", alignItems: "center" }}>
            <Img src={staticFile("img/logo.png")} style={{ width: 600, filter: "drop-shadow(0 0 50px rgba(61,242,110,0.35))" }} />
            <div style={{ marginTop: 26, fontFamily: FONT.sans, fontWeight: 900, fontSize: 58, color: CREAM, textTransform: "uppercase", letterSpacing: -1, textAlign: "center", lineHeight: 1 }}>
              Your community is waiting.
            </div>
            <div style={{ marginTop: 24, fontFamily: FONT.sans, fontWeight: 700, fontSize: 34, color: "rgba(251,249,216,0.8)" }}>{SITE}</div>
          </div>
          {cta}
        </AbsoluteFill>
      )}
      <div style={{ position: "absolute", left: 0, right: 0, bottom: vertical ? 34 : 26, textAlign: "center", fontFamily: FONT.sans, fontSize: vertical ? 22 : 18, color: "rgba(251,249,216,0.4)" }}>
        Fan community · Not affiliated with Blue Mammoth Games
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 0, height: 0, width: W }} />
    </AbsoluteFill>
  );
};
