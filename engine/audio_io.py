"""Audio I/O utilities: decode, load, hash, and measure audio signals."""
from __future__ import annotations

import hashlib
import re
import subprocess
from pathlib import Path

import numpy as np

SAMPLE_RATE = 16000
SUPPORTED_FORMATS = (".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg")


def find_voiceover(directory: Path) -> Path:
    """Locate the voice-over audio file in a project directory."""
    for ext in SUPPORTED_FORMATS:
        candidate = directory / f"vo{ext}"
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        f"No vo audio file found in {directory}"
    )


def decode_audio(path: Path, sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Decode audio file to mono float32 PCM via ffmpeg."""
    cmd = [
        "ffmpeg", "-v", "error", "-nostdin",
        "-i", str(path), "-ac", "1", "-ar", str(sample_rate),
        "-f", "f32le", "-",
    ]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).copy()


def compute_hash(path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def measure_rms(samples: np.ndarray, start_s: float, end_s: float, rate: int = SAMPLE_RATE) -> float:
    """Compute RMS level in dB for a time range."""
    i0 = int(start_s * rate)
    i1 = max(int(end_s * rate), i0 + 1)
    segment = samples[i0:i1]
    rms = float(np.sqrt(np.mean(segment.astype(np.float64) ** 2)) + 1e-9)
    return float(20 * np.log10(rms))


def measure_loudness(path: Path) -> dict:
    """Measure EBU R128 loudness via ffmpeg."""
    cmd = [
        "ffmpeg", "-hide_banner", "-nostats", "-nostdin",
        "-i", str(path), "-af", "ebur128=framelog=quiet", "-f", "null", "-",
    ]
    stderr = subprocess.run(cmd, capture_output=True, text=True).stderr
    summary = stderr[stderr.rfind("Summary:"):]

    def _extract(label: str) -> float | None:
        m = re.search(label + r":\s+(-?[\d.]+)", summary)
        return float(m.group(1)) if m else None

    return {"integrated_lufs": _extract("I"), "loudness_range_lu": _extract("LRA")}
