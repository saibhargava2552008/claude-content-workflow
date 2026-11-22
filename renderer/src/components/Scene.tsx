import React from "react";
import { AbsoluteFill } from "remotion";

interface SceneWrapperProps {
  type: string;
  props: Record<string, unknown>;
  children: React.ReactNode;
}

export const SceneWrapper: React.FC<SceneWrapperProps> = ({ children }) => {
  return (
    <AbsoluteFill
      style={{
        backgroundColor: "#0f1117",
      }}
    >
      {children}
    </AbsoluteFill>
  );
};
