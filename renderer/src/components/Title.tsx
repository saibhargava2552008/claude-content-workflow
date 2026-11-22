import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";

interface TitleCardProps {
  text: string;
  color?: string;
}

export const TitleCard: React.FC<TitleCardProps> = ({ text, color = "#e8eaf0" }) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: "clamp" });
  const translateY = interpolate(frame, [0, 15], [40, 0], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill
      style={{
        justifyContent: "center",
        alignItems: "center",
        padding: "0 60px",
      }}
    >
      <h1
        style={{
          color,
          fontSize: 72,
          fontFamily: "Inter, system-ui, sans-serif",
          fontWeight: 700,
          textAlign: "center",
          opacity,
          transform: `translateY(${translateY}px)`,
          lineHeight: 1.2,
        }}
      >
        {text}
      </h1>
    </AbsoluteFill>
  );
};
