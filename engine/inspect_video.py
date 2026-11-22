"""Video technical inspection and loudness normalization.

    python engine/inspect_video.py <video.mp4> [--contact-sheet out.jpg] [--expect-duration 60]
    python engine/inspect_video.py <video.mp4> --normalize <output.mp4>
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

TARGET_LOUDNESS = -14.0
LOUDNESS_TOLERANCE = 2.0
FREEZE_THRESHOLD_S = 3.0


def probe(path: Path) -> dict:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout
    return json.loads(out)


def _run_filter(path: Path, vf: str | None = None, af: str | None = None) -> str:
    cmd = ["ffmpeg", "-hide_banner", "-nostats", "-nostdin", "-i", str(path)]
    if vf:
        cmd += ["-vf", vf, "-an"]
    if af:
        cmd += ["-af", af, "-vn"]
    cmd += ["-f", "null", "-"]
    return subprocess.run(cmd, capture_output=True, text=True).stderr


def check_loudness(path: Path) -> dict:
    stderr = _run_filter(path, af="ebur128=framelog=quiet:peak=true")
    summary = stderr[stderr.rfind("Summary:"):]
    def _get(key):
        m = re.search(key + r":\s+(-?[\d.]+)", summary)
        return float(m.group(1)) if m else None
    return {"integrated_lufs": _get("I"), "range_lu": _get("LRA"), "peak_dbfs": _get("Peak")}


def detect_black_frames(path: Path) -> list[dict]:
    stderr = _run_filter(path, vf="blackdetect=d=0.4:pix_th=0.06")
    return [{"start": float(a), "end": float(b)}
            for a, b in re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", stderr)]


def detect_frozen_frames(path: Path) -> list[dict]:
    stderr = _run_filter(path, vf=f"freezedetect=n=0.002:d={FREEZE_THRESHOLD_S}")
    starts = [float(x) for x in re.findall(r"freeze_start: ([\d.]+)", stderr)]
    ends = [float(x) for x in re.findall(r"freeze_end: ([\d.]+)", stderr)]
    return [{"start": s, "end": e} for s, e in zip(starts, ends + [None] * (len(starts) - len(ends)))]


def make_contact_sheet(path: Path, output: Path, duration: float, cols: int = 6, rows: int = 4) -> None:
    n = cols * rows
    fps = n / max(duration, 0.1)
    subprocess.run([
        "ffmpeg", "-y", "-v", "error", "-nostdin", "-i", str(path),
        "-vf", f"fps={fps:.5f},scale=270:-1,tile={cols}x{rows}:padding=6:color=0x202020",
        "-frames:v", "1", "-q:v", "3", str(output),
    ], check=True)


def normalize(source: Path, dest: Path) -> dict:
    stderr = _run_filter(source, af=f"loudnorm=I={TARGET_LOUDNESS}:TP=-1:LRA=11:print_format=json")
    measured = json.loads(stderr[stderr.rfind("{"):stderr.rfind("}") + 1])
    af = (f"loudnorm=I={TARGET_LOUDNESS}:TP=-1:LRA=11:"
          f"measured_I={measured['input_i']}:measured_TP={measured['input_tp']}:"
          f"measured_LRA={measured['input_lra']}:measured_thresh={measured['input_thresh']}:"
          f"offset={measured['target_offset']}:linear=true")
    subprocess.run([
        "ffmpeg", "-y", "-v", "error", "-nostdin", "-i", str(source),
        "-c:v", "copy", "-af", af, "-ar", "48000", "-c:a", "aac", "-b:a", "192k", str(dest),
    ], check=True)
    return {"before_lufs": float(measured["input_i"]), "after": check_loudness(dest)}


def inspect(path: Path, sheet: Path | None, expect_duration: float | None) -> dict:
    info = probe(path)
    video = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
    audio = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    duration = float(info["format"]["duration"])
    checks = {}

    if video:
        num, den = (int(x) for x in video["r_frame_rate"].split("/"))
        checks["resolution"] = (video["width"] == 1080 and video["height"] == 1920, f"{video['width']}x{video['height']}")
        checks["framerate"] = (abs(num / den - 30) < 0.01, f"{num / den:.2f}")
        checks["codec"] = (video["codec_name"] == "h264" and video.get("pix_fmt") == "yuv420p",
                          f"{video['codec_name']}/{video.get('pix_fmt')}")
    else:
        checks["video"] = (False, "no video stream")
    checks["audio"] = (audio is not None, audio["codec_name"] if audio else "missing")
    if expect_duration:
        checks["duration"] = (abs(duration - expect_duration) < 1.5, f"{duration:.2f}s (expected ~{expect_duration:.2f}s)")

    loud = check_loudness(path) if audio else {}
    blacks = detect_black_frames(path)
    checks["black_frames"] = (not blacks, f"{len(blacks)} segment(s)")
    freezes = detect_frozen_frames(path)

    warnings = [f"frozen {f['start']:.1f}–{f['end']}s" for f in freezes]
    if audio and loud.get("integrated_lufs") is not None:
        if abs(loud["integrated_lufs"] - TARGET_LOUDNESS) > LOUDNESS_TOLERANCE:
            warnings.append(f"loudness {loud['integrated_lufs']} LUFS (target {TARGET_LOUDNESS}±{LOUDNESS_TOLERANCE})")

    if sheet:
        make_contact_sheet(path, sheet, duration)

    status = "PASS" if all(ok for ok, _ in checks.values()) else "FAIL"
    if status == "PASS" and warnings:
        status = "WARN"

    return {
        "status": status, "duration_s": round(duration, 3),
        "checks": {k: {"pass": ok, "detail": val} for k, (ok, val) in checks.items()},
        "loudness": loud, "black_frames": blacks, "frozen_frames": freezes,
        "warnings": warnings, "contact_sheet": str(sheet) if sheet else None,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video", type=Path)
    ap.add_argument("--contact-sheet", type=Path)
    ap.add_argument("--expect-duration", type=float)
    ap.add_argument("--normalize", type=Path, help="Write loudness-normalized copy")
    args = ap.parse_args()

    if args.normalize:
        print(json.dumps(normalize(args.video, args.normalize), indent=2))
        return
    result = inspect(args.video, args.contact_sheet, args.expect_duration)
    for k, c in result["checks"].items():
        print(f"  {'OK ' if c['pass'] else 'BAD'} {k:13} {c['detail']}")
    for w in result["warnings"]:
        print(f"  WARN {w}")
    print(f"QC {result['status']}" + (f" · sheet: {result['contact_sheet']}" if result["contact_sheet"] else ""))
    sys.exit(1 if result["status"] == "FAIL" else 0)


if __name__ == "__main__":
    main()
