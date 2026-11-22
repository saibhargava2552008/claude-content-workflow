import React from "react";
import { Composition } from "remotion";
import { MainComposition } from "./Composition";
import { compositionSchema } from "./schema";

export const Root: React.FC = () => {
  return (
    <>
      <Composition
        id="Composition"
        component={MainComposition}
        durationInFrames={900}
        fps={30}
        width={1080}
        height={1920}
        schema={compositionSchema}
        defaultProps={{
          slug: "example",
          scenes: [],
          audio: { file: "vo.wav", volume: 1 },
        }}
      />
    </>
  );
};
