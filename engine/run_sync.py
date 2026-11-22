"""CLI: synchronize a project folder.

    python engine/run_sync.py projects/<slug> [--model wav2vec2|mms] [--force]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from engine.sync import sync_project, available_models


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project_dir", type=Path, help="Path to project folder")
    ap.add_argument("--model", default="wav2vec2", choices=available_models())
    ap.add_argument("--force", action="store_true", help="Force re-sync even if timing exists")
    args = ap.parse_args()

    result = sync_project(args.project_dir, args.model)
    qc = result["qc"]
    print(f"[{args.model}] {qc['status']}  words={qc['word_count']}  "
          f"flagged={len(qc['flagged_words'])}  regions={len(qc['mismatch_regions'])}  "
          f"runtime={qc['runtime']}  -> {result['output_dir']}")


if __name__ == "__main__":
    main()
