"""Audio loudness normalization using ffmpeg two-pass loudnorm.

    python engine/normalize_audio.py <input.mp4> <output.mp4> [--target -14]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def normalize_loudness(input_path: Path, output_path: Path, target_lufs: float = -14.0) -> dict:
    """Two-pass EBU R128 loudness normalization."""
    # Pass 1: measure
    cmd1 = [
        "ffmpeg", "-hide_banner", "-nostats", "-nostdin",
        "-i", str(input_path), "-af",
        f"loudnorm=I={target_lufs}:TP=-1:LRA=11:print_format=json",
        "-f", "null", "-",
    ]
    stderr = subprocess.run(cmd1, capture_output=True, text=True).stderr
    measured = json.loads(stderr[stderr.rfind("{"):stderr.rfind("}") + 1])

    # Pass 2: apply
    af = (
        f"loudnorm=I={target_lufs}:TP=-1:LRA=11:"
        f"measured_I={measured['input_i']}:measured_TP={measured['input_tp']}:"
        f"measured_LRA={measured['input_lra']}:measured_thresh={measured['input_thresh']}:"
        f"offset={measured['target_offset']}:linear=true"
    )
    subprocess.run([
        "ffmpeg", "-y", "-v", "error", "-nostdin",
        "-i", str(input_path), "-c:v", "copy",
        "-af", af, "-ar", "48000", "-c:a", "aac", "-b:a", "192k",
        str(output_path),
    ], check=True)

    return {"input_lufs": float(measured["input_i"]), "target_lufs": target_lufs}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", type=Path)
    ap.add_argument("output", type=Path)
    ap.add_argument("--target", type=float, default=-14.0, help="Target LUFS (default: -14)")
    args = ap.parse_args()
    result = normalize_loudness(args.input, args.output, args.target)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
