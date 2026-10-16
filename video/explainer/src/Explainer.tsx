import React from "react";
import { AbsoluteFill, Audio, Sequence, staticFile, useCurrentFrame } from "remotion";
import { beatPulse } from "./anim";
import { Finish, PulseContext } from "./components/fx";
import { Hook } from "./scenes/Hook";
import { Meet } from "./scenes/Meet";
import { Link } from "./scenes/Link";
import { CityWars } from "./scenes/CityWars";
import { ClanWars } from "./scenes/ClanWars";
import { Cta } from "./scenes/Cta";
import { SCENES, f } from "./theme";
import { CUES } from "./cues";

const order: Array<[keyof typeof SCENES, React.FC]> = [
  ["hook", Hook],
  ["meet", Meet],
  ["link", Link],
  ["city", CityWars],
  ["clan", ClanWars],
  ["cta", Cta],
];
const ends = ["meet", "link", "city", "clan", "cta", "end"] as const;

export const Explainer: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <PulseContext.Provider value={beatPulse(frame)}>
      <AbsoluteFill style={{ background: "#0a0606" }}>
        {order.map(([key, Scene], i) => {
          const from = f(SCENES[key]);
          const to = f(SCENES[ends[i]]);
          return (
            <Sequence key={key} from={from} durationInFrames={to - from} name={key}>
              <Scene />
            </Sequence>
          );
        })}
        <Finish />
        <Audio src={staticFile("audio/music.mp3")} volume={0.9} />
        {CUES.map(([at, name, vol], i) => (
          <Sequence key={i} from={f(at)} durationInFrames={f(3.2)} name={`sfx ${name}`}>
            <Audio src={staticFile(`sfx/${name}.wav`)} volume={vol} />
          </Sequence>
        ))}
      </AbsoluteFill>
    </PulseContext.Provider>
  );
};
