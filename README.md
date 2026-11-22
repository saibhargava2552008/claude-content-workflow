# claude-content-workflow

An AI-assisted workflow and toolkit for planning, synchronizing, and producing short-form vertical videos. Combines script tokenization, CTC forced alignment, automated quality inspection, stock media discovery, and Remotion-based motion graphics rendering.

**Project Maintainer**: Sai Bhargava Reddy Sathi
**Repository**: `claude-content-workflow`

---

## Features

- **Script Tokenization & Structure Analysis**: Normalizes text, handles abbreviations, spoken numerals, punctuation weights, sentence/phrase segmentation, and signpost marker detection.
- **Speech-to-Text Forced Alignment**: Aligns audio recordings with known transcripts using CTC acoustic models (wav2vec 2.0 / MMS) and an unconstrained Viterbi decoder with optional wildcard speech absorption.
- **Automated Video & Audio QC**: Inspects video files for resolution (1080x1920), framerate (30fps), pixel format (yuv420p), loudness (EBU R128 integrated LUFS), silence/black frame detection, and frozen frame warnings.
- **Two-Pass Audio Normalization**: Normalizes audio loudness to standard targets (-14 LUFS) with true-peak limiting.
- **Stock Media Integration**: Searches Openverse for commercial-friendly CC-licensed stock imagery, generating provenance and license sidecars.
- **Bundled Royalty-Free Audio Collection**: 44 CC0-licensed sound effects and music tracks categorized across transitions, whooshes, clicks, impacts, risers, ambience, notifications, and background music.
- **Data-Driven Video Rendering**: Remotion and React-based vertical rendering framework for titles, captions, and layered motion scenes.

---

## Project Structure

```text
claude-content-workflow/
├── .gitignore
├── LICENSE
├── README.md
├── CHANGELOG.md
├── CONTRIBUTING.md
├── SKILL.md
├── config/                    # Design system tokens and styling
│   ├── CONFIG.md
│   ├── palette.json
│   └── typography.json
├── planner/                   # Video planning and templates
│   ├── guide.md
│   ├── components.md
│   └── templates/
│       ├── brief.example.json
│       └── shotlist.example.json
├── engine/                    # Python processing engine
│   ├── __init__.py
│   ├── requirements.txt
│   ├── transcript.py          # Script parsing and tokenization
│   ├── graph.py               # CTC state graph and Viterbi decoder
│   ├── acoustic.py            # Acoustic model wrapper
│   ├── audio_io.py            # Audio loading, hashing, loudness
│   ├── timing.py              # Word timing and boundary builder
│   ├── quality.py             # Alignment QC and anomaly detection
│   ├── schema.py              # Schema definition for timing outputs
│   ├── sync.py                # Full alignment pipeline
│   ├── run_sync.py            # CLI alignment entrypoint
│   ├── inspect_video.py       # Technical video and audio verification
│   ├── media_search.py        # Stock asset search via Openverse
│   ├── normalize_audio.py     # EBU R128 loudness normalizer
│   └── tests/                 # Automated test suite
│       ├── conftest.py
│       ├── test_transcript.py
│       └── test_graph.py
├── renderer/                  # Remotion-based vertical video renderer
│   ├── package.json
│   ├── tsconfig.json
│   ├── remotion.config.ts
│   └── src/
│       ├── index.ts
│       ├── Root.tsx
│       ├── schema.ts
│       ├── Composition.tsx
│       └── components/
│           ├── Title.tsx
│           ├── Caption.tsx
│           ├── Scene.tsx
│           └── Transition.tsx
├── guides/                    # Video production reference guides
│   ├── audio-mixing.md
│   ├── color-theory.md
│   ├── export-checklist.md
│   └── editing-principles.md
├── examples/                  # Sample project guidance
│   └── README.md
└── scripts/                   # Repository maintenance scripts
    └── hygiene_check.py
```

---

## Prerequisites

- **Python**: 3.10 or higher
- **Node.js**: 20.x or higher with npm
- **FFmpeg / FFprobe**: Accessible in system PATH
- **PyTorch & Transformers**: For acoustic model inference

Install Python engine dependencies:
```powershell
python -m pip install -r engine/requirements.txt
```

---

## Quickstart

### 1. Set Up a Project Directory
Create a project folder (e.g. `projects/demo-video/`) containing:
- `script.txt`: The spoken script
- `vo.wav`: Voice-over audio file (or `.mp3`, `.m4a`, `.flac`)

### 2. Run Forced Alignment & Timing Generation
```powershell
python engine/run_sync.py projects/demo-video
```
This generates:
- `timing.json`: Word-by-word timestamps, boundaries, speech rate, and confidence scores
- `qc.json`: Quantitative QC metrics and flag reports
- `qc_report.md`: Markdown summary of alignment accuracy

### 3. Search Stock Media
```powershell
python engine/media_search.py search "laptop coding" --limit 5
```

### 4. Technical Video QC & Loudness Mastering
```powershell
python engine/inspect_video.py output/final.mp4 --contact-sheet output/sheet.jpg
python engine/normalize_audio.py output/final.mp4 output/mastered.mp4 --target -14
```

---

## Testing & Quality Checks

Run the automated test suite:
```powershell
python -m pytest engine/tests/ -v
```

Validate audio assets and licenses:
```powershell
python scripts/validate_assets.py
```

Run repository hygiene checks:
```powershell
python scripts/hygiene_check.py
```

---

## Acknowledgments & Upstream Foundation

The speech-to-text forced alignment pipeline, CTC graph construction, and technical video QC foundations of this project were adapted from the MIT-licensed [Video Editing Workflow](https://github.com/maheswarreddygondireddy12/claude-content-skill) (`claude-content-skill`) project originally created by Video Editing Workflow contributors.

This repository refactors and modularizes those concepts into an independently maintained workflow, complete with automated quality validation, a Remotion-based React renderer, and a curated collection of CC0 audio assets. All original copyright notices and license terms are preserved in [LICENSE](LICENSE).

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for terms and attribution details.
