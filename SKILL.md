---
name: claude-content-workflow
description: Plan, synchronize, and produce polished short-form vertical videos with script-to-audio alignment, scene planning, word-timed captions, automated QC, and Remotion rendering.
---

# Claude Content Workflow Skill

Use this workflow to transform scripts, voice-overs, and visual concepts into high-quality vertical videos.

## Workflow Phases

### Phase 1: Planning & Brief
1. Define the video target: platform (Shorts, Reels, TikTok), audience, duration, hook, and core takeaway.
2. Structure the script into concise sentences optimized for spoken delivery.
3. Use templates in `planner/templates/` (`brief.example.json`, `shotlist.example.json`) to draft scenes.
4. Consult `planner/components.md` for appropriate scene archetypes (talking head, title card, b-roll, code card, diagram).

### Phase 2: Speech Synchronization
1. Place `script.txt` and voice-over audio (`vo.wav`, `vo.mp3`, etc.) in the project directory (`projects/<slug>/`).
2. Run alignment:
   ```powershell
   python engine/run_sync.py projects/<slug>
   ```
3. Inspect `qc_report.md` for confidence levels, flagged words, or unscripted speech regions.

### Phase 3: Visual & Audio Composition
1. Identify required visual assets. Search Openverse for CC-licensed stock imagery:
   ```powershell
   python engine/media_search.py search "<query>" --limit 8
   ```
2. Configure typography and color themes in `config/palette.json` and `config/typography.json`.
3. Assemble the Remotion composition in `renderer/` using timing data from `timing.json`.

### Phase 4: Inspection & Mastering
1. Render draft or final video.
2. Run automated technical inspection:
   ```powershell
   python engine/inspect_video.py output/final.mp4 --contact-sheet output/sheet.jpg
   ```
3. If loudness does not meet the -14 LUFS standard, run loudness normalization:
   ```powershell
   python engine/normalize_audio.py output/final.mp4 output/mastered.mp4 --target -14
   ```
