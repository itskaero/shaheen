import React from "react";
import { Composition } from "remotion";
import "./fonts";
import { Explainer } from "./Explainer";
import { DURATION_S, FPS, HEIGHT, WIDTH } from "./theme";

export const Root: React.FC = () => (
  <Composition
    id="Explainer"
    component={Explainer}
    durationInFrames={Math.ceil(DURATION_S * FPS)}
    fps={FPS}
    width={WIDTH}
    height={HEIGHT}
  />
);
