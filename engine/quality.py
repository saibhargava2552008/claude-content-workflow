"""Alignment quality assessment: detect anomalies and generate reports."""
from __future__ import annotations

import numpy as np

# Detection thresholds
MIN_DURATION_S = 0.055          # words shorter than this are likely misaligned
MAX_BASE_DURATION_S = 1.3       # base limit for stretched words
DURATION_PER_CHAR_S = 0.11      # additional allowance per character
ELONGATED_LIMIT_S = 2.6
OUTLIER_Z_THRESHOLD = -3.0      # robust z-score for low confidence
PRONUNCIATION_Z = -1.8          # threshold for uncertain pronunciations
UNSCRIPTED_MIN_DURATION = 0.3
SILENCE_MARGIN_DB = 14.0
ANOMALY_WINDOW = 4
ANOMALY_MIN_COUNT = 2


def _robust_zscore(values: np.ndarray) -> np.ndarray:
    """Compute robust z-scores using median absolute deviation."""
    median = np.median(values)
    mad = np.median(np.abs(values - median)) * 1.4826 or 1e-6
    return (values - median) / mad


def run_quality_check(timing: dict, duration: float, expected_words: int) -> dict:
    """Run comprehensive quality checks on alignment results."""
    words = timing["words"]
    errors = []

    # Structural checks
    if len(words) != expected_words:
        errors.append(f"word count mismatch: got {len(words)}, expected {expected_words}")
    for a, b in zip(words, words[1:]):
        if b["start"] < a["end"] - 1e-6:
            errors.append(f"overlap: word {a['i']} ends at {a['end']}, word {b['i']} starts at {b['start']}")
    for w in words:
        if not (0 <= w["start"] < w["end"] <= duration + 0.05):
            errors.append(f"word {w['i']} '{w['display']}' has invalid span {w['start']:.3f}–{w['end']:.3f}")

    # Per-word anomaly detection
    scores = np.array([w["score"] for w in words])
    z_scores = _robust_zscore(scores)
    median_rms = float(np.median([w["rms_db"] for w in words]))

    anomaly_types = {"too_short", "too_long", "low_confidence", "check_pronunciation"}

    for w, z in zip(words, z_scores):
        w["score_z"] = round(float(z), 2)
        word_duration = w["end"] - w["start"]
        num_chars = len(w["phonetic"].replace(" ", ""))
        new_flags: list[str] = []

        if num_chars >= 3 and word_duration < MIN_DURATION_S:
            new_flags.append("too_short")
        limit = ELONGATED_LIMIT_S if "elongated" in w["tags"] else MAX_BASE_DURATION_S + DURATION_PER_CHAR_S * num_chars
        if word_duration > limit:
            new_flags.append("too_long")
        if z < OUTLIER_Z_THRESHOLD:
            new_flags.append("low_confidence")
        if "check_pronunciation" in w["flags"] and z < PRONUNCIATION_Z:
            new_flags.append("check_pronunciation")

        w["flags"] = sorted(set(w["flags"]) | set(new_flags))

    # Filter unscripted regions
    significant_unscripted = [
        u for u in timing.get("unscripted_regions", [])
        if u["duration"] >= UNSCRIPTED_MIN_DURATION and u["rms_db"] > median_rms - SILENCE_MARGIN_DB
    ]

    # Identify flagged words and mismatch regions
    flagged = [w for w in words if anomaly_types & set(w["flags"])]
    regions = _find_mismatch_regions(words, anomaly_types, significant_unscripted)

    flagged_ratio = len(flagged) / max(len(words), 1)
    if errors:
        status = "FAIL"
    elif regions or flagged_ratio > 0.02:
        status = "WARN"
    else:
        status = "PASS"

    return {
        "status": status,
        "errors": errors,
        "word_count": len(words),
        "duration_s": round(duration, 3),
        "flagged_words": [
            {"i": w["i"], "display": w["display"], "start": w["start"], "end": w["end"],
             "flags": [f for f in w["flags"] if f in anomaly_types], "score_z": w["score_z"]}
            for w in flagged
        ],
        "flagged_ratio": round(flagged_ratio, 4),
        "unscripted_speech": significant_unscripted,
        "mismatch_regions": regions,
        "statistics": {
            "median_score": round(float(np.median(scores)), 4),
            "median_confidence": round(float(np.median([w["conf"] for w in words])), 4),
            "words_per_minute": round(len(words) / duration * 60, 1),
            "median_rms_db": round(median_rms, 2),
            "median_word_duration": round(float(np.median([w["end"] - w["start"] for w in words])), 3),
        },
    }


def _find_mismatch_regions(words, anomaly_types, unscripted):
    """Cluster flagged words into suspected mismatch regions."""
    is_flagged = np.array([bool(anomaly_types & set(w["flags"])) for w in words])
    hot = np.zeros(len(words), dtype=bool)

    for i in range(len(words)):
        window = slice(i, min(i + ANOMALY_WINDOW, len(words)))
        if is_flagged[window].sum() >= ANOMALY_MIN_COUNT:
            indices = np.nonzero(is_flagged[window])[0] + i
            hot[indices[0]:indices[-1] + 1] = True

    for i, w in enumerate(words):
        if {"too_short", "too_long"} & set(w["flags"]):
            hot[i] = True

    regions = []
    i = 0
    while i < len(words):
        if hot[i]:
            j = i
            while j + 1 < len(words) and hot[j + 1]:
                j += 1
            regions.append(_make_region(words, i, j, "flagged_cluster"))
            i = j + 1
        else:
            i += 1

    for u in unscripted:
        bw = u.get("next_word", -1)
        a = max(bw - 1, 0) if bw >= 0 else len(words) - 1
        b = bw if bw >= 0 else len(words) - 1
        r = _make_region(words, a, b, "unscripted_audio")
        r["start"] = min(r["start"], u["start"])
        r["end"] = max(r["end"], u["end"])
        regions.append(r)

    return sorted(regions, key=lambda r: r["start"])


def _make_region(words, a, b, kind):
    return {
        "kind": kind,
        "word_start": a, "word_end": b,
        "start": words[a]["start"], "end": words[b]["end"],
        "sentence_ids": sorted({words[k]["sentence_id"] for k in range(a, b + 1)}),
        "text": " ".join(words[k]["display"] for k in range(a, b + 1)),
    }


def generate_report(project_name: str, model_info: dict, qc: dict) -> str:
    """Generate a markdown QC report."""
    s = qc["statistics"]
    lines = [
        f"# Sync QC Report — {project_name}",
        "",
        f"**Status: {qc['status']}**  ·  model `{model_info['id']}` ({model_info['license']})",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Words | {qc['word_count']} |",
        f"| Duration | {qc['duration_s']} s |",
        f"| Speech rate | {s['words_per_minute']} words/min |",
        f"| Median confidence | {s['median_confidence']} |",
        f"| Median word duration | {s['median_word_duration']} s |",
        f"| Flagged words | {len(qc['flagged_words'])} ({qc['flagged_ratio'] * 100:.1f}%) |",
        f"| Mismatch regions | {len(qc['mismatch_regions'])} |",
        "",
    ]
    if qc["errors"]:
        lines += ["## Errors", ""] + [f"- {e}" for e in qc["errors"]] + [""]
    if qc["mismatch_regions"]:
        lines += ["## Mismatch Regions", "", "| Time | Kind | Words | Text |", "|------|------|-------|------|"]
        for r in qc["mismatch_regions"]:
            lines.append(f"| {r['start']:.2f}–{r['end']:.2f} s | {r['kind']} | {r['word_start']}–{r['word_end']} | {r['text']} |")
        lines.append("")
    if qc["flagged_words"]:
        lines += ["## Flagged Words", "", "| # | Word | Time | Flags | Z-score |", "|---|------|------|-------|---------|"]
        for w in qc["flagged_words"]:
            lines.append(f"| {w['i']} | {w['display']} | {w['start']:.2f}–{w['end']:.2f} | {', '.join(w['flags'])} | {w['score_z']} |")
        lines.append("")
    return "\n".join(lines)
