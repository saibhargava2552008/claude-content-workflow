import { z } from "zod";

const sceneSchema = z.object({
  type: z.enum(["title_card", "talking_head", "broll", "text_overlay", "diagram", "code_snippet"]),
  startFrame: z.number(),
  durationFrames: z.number(),
  props: z.record(z.unknown()).optional(),
});

const audioSchema = z.object({
  file: z.string(),
  volume: z.number().min(0).max(1).default(1),
});

export const compositionSchema = z.object({
  slug: z.string(),
  scenes: z.array(sceneSchema),
  audio: audioSchema,
});

export type CompositionProps = z.infer<typeof compositionSchema>;
export type SceneConfig = z.infer<typeof sceneSchema>;
