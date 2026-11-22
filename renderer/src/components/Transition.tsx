import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";

type TransitionType = "fade" | "slide_up" | "wipe_left";

interface TransitionProps {
  type: TransitionType;
  durationFrames: number;
  children: React.ReactNode;
}

export const Transition: React.FC<TransitionProps> = ({ type, durationFrames, children }) => {
  const frame = useCurrentFrame();
  const style: React.CSSProperties = {};

  if (type === "fade") {
    style.opacity = interpolate(frame, [0, durationFrames], [0, 1], { extrapolateRight: "clamp" });
  } else if (type === "slide_up") {
    const y = interpolate(frame, [0, durationFrames], [100, 0], { extrapolateRight: "clamp" });
    style.transform = `translateY(${y}%)`;
  } else if (type === "wipe_left") {
    const x = interpolate(frame, [0, durationFrames], [100, 0], { extrapolateRight: "clamp" });
    style.clipPath = `inset(0 0 0 ${x}%)`;
  }

  return <AbsoluteFill style={style}>{children}</AbsoluteFill>;
};
