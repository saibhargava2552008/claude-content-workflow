# Examples

This directory is for sample project layouts.

## Standard Project Layout

To organize a video project:

```text
projects/my-video/
├── script.txt      # Spoken script text
├── vo.wav          # Clean voice-over audio recording
└── assets/         # Project-specific graphics, screenshots, or b-roll
```

## Running the Sync Pipeline

Run the synchronization engine from the project root:

```powershell
python engine/run_sync.py projects/my-video
```

Outputs will be saved in `projects/my-video/sync/wav2vec2/`:
- `timing.json`
- `qc.json`
- `qc_report.md`
