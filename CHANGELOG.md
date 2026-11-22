# Changelog

All notable changes to `claude-content-workflow` will be documented in this file.

## 0.1.0 — 2026-11-22

- Initial independent release of `claude-content-workflow`.
- Complete architectural redesign of script analysis and forced alignment pipeline.
- Added modular script tokenizer supporting spoken numeral expansion, abbreviation mapping, and boundary detection.
- Implemented robust CTC state graph construction and dynamic programming Viterbi decoder with unscripted audio wildcard states.
- Implemented video inspection CLI with resolution, framerate, black frame, freeze frame, and EBU R128 loudness metrics.
- Added two-pass loudness normalization CLI using FFmpeg loudnorm.
- Built stock media search client using Openverse CC API with attribution sidecars.
- Scaffolded Remotion-based vertical video renderer with animated titles and word-timed captions.
- Added automated pytest test suite for transcript tokenization and CTC graph decoding.
- Added repository hygiene scanner to prevent accidental leaks of personal directories and secrets.
