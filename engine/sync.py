"""Synchronize a project: align script to voice-over audio."""
from __future__ import annotations

import json
import time
from pathlib import Path

from . import audio_io
from .acoustic import FRAME_DURATION, AVAILABLE_MODELS, AcousticEngine
from .timing import assemble_timing
from .quality import run_quality_check, generate_report
from .schema import SCHEMA_VERSION, validate_timing
from .transcript import tokenize
from .graph import (
    append_wildcard_column, construct_graph, viterbi_decode,
    extract_spans, find_wildcard_regions,
)

DEFAULT_WILDCARD_PENALTY = -2.0
_engine_cache: dict[str, AcousticEngine] = {}


def _get_engine(key: str) -> AcousticEngine:
    if key not in _engine_cache:
        _engine_cache[key] = AcousticEngine(key)
    return _engine_cache[key]


def sync_project(
    project_dir: Path,
    model_key: str = "wav2vec2",
    wildcard_penalty: float | None = DEFAULT_WILDCARD_PENALTY,
    include_chars: bool = True,
    output_dir: Path | None = None,
) -> dict:
    """Run full sync pipeline on a project folder."""
    t0 = time.perf_counter()
    project_dir = Path(project_dir)
    project_name = project_dir.name
    script_path = project_dir / "script.txt"
    vo_path = audio_io.find_voiceover(project_dir)
    output_dir = output_dir or project_dir / "sync" / model_key
    output_dir.mkdir(parents=True, exist_ok=True)

    # Tokenize script
    tokens = tokenize(script_path.read_text(encoding="utf-8"))
    # Load audio
    pcm = audio_io.decode_audio(vo_path)
    duration = len(pcm) / audio_io.SAMPLE_RATE
    audio_hash = audio_io.compute_hash(vo_path)

    # Compute emissions
    engine = _get_engine(model_key)
    t_emit = time.perf_counter()
    emissions = engine.compute_emissions(pcm, cache_key=audio_hash)
    t_emit = time.perf_counter() - t_emit

    # Build token sequences
    word_token_ids = []
    for tok in tokens:
        ids, dropped = engine.text_to_tokens(tok.phonetic)
        if dropped:
            tok.flags.append("dropped_chars:" + "".join(sorted(set(dropped))))
        if not ids:
            raise ValueError(f"Token {tok.index} '{tok.raw}' has no alignable characters")
        word_token_ids.append(ids)

    # Optional wildcard states
    wc_col = None
    wc_positions: set[int] = set()
    if wildcard_penalty is not None:
        emissions, wc_col = append_wildcard_column(emissions, engine.blank_id, wildcard_penalty)
        wc_positions = {0, len(tokens)} | {
            tok.index for tok in tokens
            if tok.index > 0 and tok.sentence_id != tokens[tok.index - 1].sentence_id
        }

    # Build graph and decode
    graph = construct_graph(word_token_ids, engine.blank_id, wc_col, wc_positions, engine.separator_id)
    t_vit = time.perf_counter()
    path, frame_scores = viterbi_decode(emissions, graph)
    spans = extract_spans(path, frame_scores, graph, len(tokens))
    t_vit = time.perf_counter() - t_vit
    wildcards = find_wildcard_regions(path, graph) if wc_col is not None else []

    # Build timing
    timing = {
        "schema_version": SCHEMA_VERSION,
        "meta": {
            "project": project_name,
            "script_hash": audio_io.compute_hash(script_path),
            "audio_hash": audio_hash,
            "audio_file": vo_path.name,
            "duration_s": round(duration, 3),
            "model": {"key": model_key, "id": engine.config.hf_model_id, "license": engine.config.license_id},
            "frame_duration": FRAME_DURATION,
            "wildcard_penalty": wildcard_penalty,
        },
    }
    timing.update(assemble_timing(tokens, spans, pcm, duration, wildcards, include_chars))

    # QC
    qc = run_quality_check(timing, duration, len(tokens))
    timing["meta"]["qc_status"] = qc["status"]
    validate_timing(timing)

    runtime = {
        "emission_s": round(t_emit, 2),
        "viterbi_s": round(t_vit, 2),
        "total_s": round(time.perf_counter() - t0, 2),
    }
    qc["runtime"] = runtime

    # Save outputs
    (output_dir / "timing.json").write_text(json.dumps(timing, ensure_ascii=False, indent=1), encoding="utf-8")
    (output_dir / "qc.json").write_text(json.dumps(qc, ensure_ascii=False, indent=1), encoding="utf-8")
    model_info = {"id": engine.config.hf_model_id, "license": engine.config.license_id}
    (output_dir / "qc_report.md").write_text(generate_report(project_name, model_info, qc), encoding="utf-8")

    return {"timing": timing, "qc": qc, "output_dir": output_dir}


def available_models() -> list[str]:
    return list(AVAILABLE_MODELS)
