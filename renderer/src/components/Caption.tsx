import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";

interface CaptionProps {
  words: Array<{ text: string; startFrame: number; endFrame: number }>;
  fontSize?: number;
  color?: string;
  highlightColor?: string;
}

export const Caption: React.FC<CaptionProps> = ({
  words,
  fontSize = 48,
  color = "#e8eaf0",
  highlightColor = "#6c8cff",
}) => {
  const frame = useCurrentFrame();

  return (
    <AbsoluteFill
      style={{
        justifyContent: "flex-end",
        alignItems: "center",
        padding: "0 48px 280px",
      }}
    >
      <div style={{ textAlign: "center" }}>
        {words.map((word, i) => {
          const isActive = frame >= word.startFrame && frame < word.endFrame;
          return (
            <span
              key={i}
              style={{
                fontSize,
                fontFamily: "JetBrains Mono, monospace",
                fontWeight: 600,
                color: isActive ? highlightColor : color,
                marginRight: 12,
              }}
            >
              {word.text}
            </span>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
