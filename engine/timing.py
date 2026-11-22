"""Build word-level timing data from alignment results."""
from __future__ import annotations

import numpy as np

from .acoustic import FRAME_DURATION
from .audio_io import measure_rms
from .transcript import Token, punctuation_break_weight
from .graph import WordSpan


def _frame_to_seconds(frame: int) -> float:
    return round(frame * FRAME_DURATION, 3)


def build_word_records(
    tokens: list[Token], spans: list[WordSpan],
    audio: np.ndarray, include_chars: bool = False,
) -> list[dict]:
    """Create per-word timing records with confidence and RMS."""
    durations = np.array([max(s.last_frame - s.first_frame, 1) * FRAME_DURATION for s in spans])
    char_counts = np.array([max(len(t.phonetic.replace(" ", "")), 1) for t in tokens])
    log_rate = np.log(durations / char_counts)
    mean_lr, std_lr = log_rate.mean(), log_rate.std() or 1.0

    records = []
    for tok, span, lr in zip(tokens, spans, log_rate):
        t0 = _frame_to_seconds(span.first_frame)
        t1 = _frame_to_seconds(span.last_frame)
        rec = {
            "i": tok.index,
            "raw": tok.raw,
            "display": tok.display,
            "phonetic": tok.phonetic,
            "start": t0,
            "end": t1,
            "score": round(span.mean_score, 4),
            "conf": round(float(np.exp(span.mean_score)), 4),
            "language": tok.language,
            "tags": list(tok.tags),
            "punctuation": tok.punctuation,
            "sentence_id": tok.sentence_id,
            "phrase_id": tok.phrase_id,
            "is_signpost": tok.is_signpost,
            "rms_db": round(measure_rms(audio, t0, t1), 2),
            "duration_z": round(float((lr - mean_lr) / std_lr), 3),
            "flags": list(tok.flags),
        }
        if include_chars:
            rec["chars"] = [[_frame_to_seconds(a), _frame_to_seconds(b)] for a, b in span.char_spans]
        records.append(rec)
    return records


def detect_boundaries(tokens: list[Token], word_records: list[dict]) -> list[dict]:
    """Compute boundary strength between consecutive words."""
    boundaries = []
    for curr_rec, next_rec, tok in zip(word_records, word_records[1:], tokens):
        gap = max(0.0, (next_rec["start"] - curr_rec["end"]) * 1000)
        punct_weight = punctuation_break_weight(tok)
        lang_change = (
            curr_rec["language"] in ("en", "num") and next_rec["language"] in ("en", "num")
            and curr_rec["language"] != next_rec["language"]
        )
        strength = (
            0.55 * punct_weight
            + 0.25 * min(gap / 250.0, 1.0)
            + 0.12 * next_rec["is_signpost"]
            + 0.08 * lang_change
        )
        boundaries.append({
            "after_word": curr_rec["i"],
            "gap_ms": round(gap, 1),
            "punctuation": tok.punctuation,
            "punct_weight": punct_weight,
            "signpost_follows": next_rec["is_signpost"],
            "language_change": bool(lang_change),
            "sentence_boundary": curr_rec["sentence_id"] != next_rec["sentence_id"],
            "strength": round(min(strength, 1.0), 3),
        })
    return boundaries


def _group_by_key(word_records: list[dict], key: str) -> list[dict]:
    """Group consecutive words sharing the same key value."""
    groups: list[dict] = []
    for w in word_records:
        if not groups or groups[-1]["id"] != w[key]:
            groups.append({
                "id": w[key], "first_word": w["i"], "last_word": w["i"],
                "start": w["start"], "end": w["end"], "_words": [],
            })
        g = groups[-1]
        g["last_word"] = w["i"]
        g["end"] = w["end"]
        g["_words"].append(w["display"])
    for g in groups:
        g["text"] = " ".join(g.pop("_words"))
    return groups


def compute_speech_rate(word_records: list[dict], duration: float, window: float = 3.0, step: float = 0.5) -> dict:
    """Windowed speech rate in words per second."""
    starts = np.array([w["start"] for w in word_records])
    measurements = []
    t = 0.0
    while t + window <= duration + 1e-6:
        count = int(((starts >= t) & (starts < t + window)).sum())
        measurements.append([round(t + window / 2, 2), round(count / window, 2)])
        t += step
    return {"window_s": window, "step_s": step, "unit": "words_per_second", "values": measurements}


def assemble_timing(
    tokens: list[Token], spans: list[WordSpan], audio: np.ndarray,
    duration: float, wildcard_regions: list[tuple[int, int, int]],
    include_chars: bool = False,
) -> dict:
    """Assemble the complete timing data structure."""
    word_records = build_word_records(tokens, spans, audio, include_chars)
    return {
        "words": word_records,
        "boundaries": detect_boundaries(tokens, word_records),
        "sentences": _group_by_key(word_records, "sentence_id"),
        "phrases": _group_by_key(word_records, "phrase_id"),
        "speech_rate": compute_speech_rate(word_records, duration),
        "unscripted_regions": [
            {
                "start": _frame_to_seconds(a), "end": _frame_to_seconds(b),
                "next_word": nw, "duration": round((b - a) * FRAME_DURATION, 3),
                "rms_db": round(measure_rms(audio, _frame_to_seconds(a), _frame_to_seconds(b)), 2),
            }
            for a, b, nw in wildcard_regions
        ],
    }
