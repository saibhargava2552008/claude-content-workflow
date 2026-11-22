# Audio Assets & Sound Design Guide

This guide explains how to effectively integrate and mix the bundled audio collection (`assets/audio/`) into short-form vertical video workflows.

---

## 1. Asset Collection Overview

The repository bundles **44 royalty-free sound effects and audio tracks** across 8 core categories:

| Category | Folder | Suggested Use Cases | Recommended Mix Level (dB relative to dialogue) |
|---|---|---|---|
| **Clicks & Taps** | `assets/audio/clicks/` | UI button taps, code typing beats, checklist items | -12 dB to -16 dB |
| **Transitions** | `assets/audio/transitions/` | Slide cuts, card flips, page turns, scene changes | -10 dB to -14 dB |
| **Whooshes** | `assets/audio/whooshes/` | Fast visual reveals, pop-ins, camera pans | -12 dB to -18 dB |
| **Impacts** | `assets/audio/impacts/` | Major hook punchlines, statistic reveals, dramatic emphasis | -8 dB to -12 dB |
| **Risers** | `assets/audio/risers/` | Building tension before a revelation, hook intro swells | -14 dB to -20 dB |
| **Ambience** | `assets/audio/ambience/` | Room tone, vinyl warmth bed to eliminate sterile silence | -22 dB to -28 dB |
| **Notifications** | `assets/audio/notifications/` | Success chimes, alerts, error highlights | -10 dB to -14 dB |
| **Music Jingles** | `assets/audio/music/` | Hook intro themes, outro stingers, subtle pad loops | -16 dB to -22 dB |

---

## 2. Usage in Remotion Video Compositions

In Remotion (`renderer/src/`), audio assets can be loaded using `staticFile` or imported directly:

```tsx
import { Audio, Sequence, staticFile } from "remotion";

export const VideoScene: React.FC = () => {
  return (
    <>
      {/* Background ambient pad loop */}
      <Audio
        src={staticFile("assets/audio/music/synth_ambient_pad_loop.wav")}
        volume={0.15}
        loop
      />

      {/* Transition sound effect anchored to scene change at frame 60 */}
      <Sequence from={60} durationInFrames={30}>
        <Audio
          src={staticFile("assets/audio/transitions/page_turn_01.ogg")}
          volume={0.65}
        />
      </Sequence>

      {/* UI Click sound when graphic reveals at frame 90 */}
      <Sequence from={90} durationInFrames={15}>
        <Audio
          src={staticFile("assets/audio/clicks/synth_click_clean.wav")}
          volume={0.5}
        />
      </Sequence>
    </>
  );
};
```

---

## 3. Synchronizing Sound Effects with Speech Timing

When using the forced alignment engine (`engine/run_sync.py`), the generated `timing.json` file contains word and sentence boundary timestamps. Use these timestamps to automatically anchor sound effects:

1. **Hook Accent**: Place an impact (`assets/audio/impacts/synth_sub_bass_drop.wav`) on the first key emphasis word of your hook (usually word index 0 or 1).
2. **Key Takeaway Chime**: Trigger `synth_modern_chime.wav` when revealing a statistic or successful outcome.
3. **Slide / Swish**: Trigger `whoosh_fast_air.wav` 3 to 5 frames before a new scene or card enters the viewport.

---

## 4. Validating Audio Assets

To ensure all audio files are present and properly licensed, run:

```powershell
python scripts/validate_assets.py
```
