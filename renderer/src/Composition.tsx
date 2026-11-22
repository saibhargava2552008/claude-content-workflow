import React from "react";
import { AbsoluteFill, Audio, Sequence, staticFile } from "remotion";
import { CompositionProps } from "./schema";
import { TitleCard } from "./components/Title";
import { SceneWrapper } from "./components/Scene";

export const MainComposition: React.FC<CompositionProps> = ({ slug, scenes, audio }) => {
  return (
    <AbsoluteFill style={{ backgroundColor: "#0f1117" }}>
      {audio.file && (
        <Audio src={staticFile(`projects/${slug}/${audio.file}`)} volume={audio.volume} />
      )}
      {scenes.map((scene, idx) => (
        <Sequence key={idx} from={scene.startFrame} durationInFrames={scene.durationFrames}>
          <SceneWrapper type={scene.type} props={scene.props || {}}>
            {scene.type === "title_card" && (
              <TitleCard text={(scene.props?.text as string) || "Title"} />
            )}
          </SceneWrapper>
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};
