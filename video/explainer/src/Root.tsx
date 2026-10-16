import React from "react";
import { Composition } from "remotion";
import "./fonts";
import { Explainer } from "./Explainer";
import { EndCard } from "./EndCard";
import { RECRUIT_DURATION, Recruit } from "./recruit/Recruit";
import { DURATION_S, FPS, HEIGHT, WIDTH } from "./theme";

export const Root: React.FC = () => (
  <>
  <Composition
    id="Explainer"
    component={Explainer}
    durationInFrames={Math.ceil(DURATION_S * FPS)}
    fps={FPS}
    width={WIDTH}
    height={HEIGHT}
  />
  {/* Recruitment-trailer end cards (video/recruitment/README.md) */}
  <Composition id="EndCardVertical" component={EndCard} durationInFrames={1} fps={FPS} width={1080} height={1920} defaultProps={{ vertical: true, showInvite: true }} />
  <Composition id="EndCardWide" component={EndCard} durationInFrames={1} fps={FPS} width={1920} height={1080} defaultProps={{ vertical: false, showInvite: true }} />
  {/* The Discord recruitment trailer (video/recruitment/README.md) */}
  <Composition id="RecruitVertical" component={Recruit} durationInFrames={RECRUIT_DURATION} fps={FPS} width={1080} height={1920} defaultProps={{ vertical: true }} />
  <Composition id="RecruitWide" component={Recruit} durationInFrames={RECRUIT_DURATION} fps={FPS} width={1920} height={1080} defaultProps={{ vertical: false }} />
  </>
);
