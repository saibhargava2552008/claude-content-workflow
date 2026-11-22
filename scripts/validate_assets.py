"""Asset validation script: verify audio files on disk match ASSET_LICENSES.md records."""
from __future__ import annotations

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
AUDIO_DIR = PROJECT_ROOT / "assets" / "audio"
LICENSE_FILE = PROJECT_ROOT / "ASSET_LICENSES.md"

VALID_EXTENSIONS = {".wav", ".ogg", ".mp3"}


def parse_licensed_assets(doc_path: Path) -> dict[str, dict]:
    """Parse asset records from ASSET_LICENSES.md."""
    if not doc_path.exists():
        raise FileNotFoundError(f"Missing license documentation: {doc_path}")

    text = doc_path.read_text(encoding="utf-8")
    records = {}

    # Regex to match table rows: | `path` | Category | Creator | License | Attribution |
    row_pattern = re.compile(
        r"\|\s*`([^`]+)`\s*\|\s*([^|]+)\|\s*([^|]+)\|\s*([^|]+)\|\s*([^|]+)\|"
    )

    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|") or "---" in line or "File Path" in line:
            continue
        match = row_pattern.match(line)
        if match:
            rel_path, category, creator, lic, attrib = [m.strip() for m in match.groups()]
            records[rel_path] = {
                "category": category,
                "creator": creator,
                "license": lic,
                "attribution": attrib,
            }

    return records


def scan_audio_files(base_dir: Path) -> set[str]:
    """Find all audio files in the assets/audio directory."""
    if not base_dir.exists():
        return set()

    found = set()
    for path in base_dir.rglob("*"):
        if path.is_file() and path.suffix.lower() in VALID_EXTENSIONS:
            rel = path.relative_to(PROJECT_ROOT).as_posix()
            found.add(rel)
    return found


def validate() -> bool:
    print(f"Validating audio assets in {AUDIO_DIR.relative_to(PROJECT_ROOT)}...")
    disk_files = scan_audio_files(AUDIO_DIR)
    licensed_assets = parse_licensed_assets(LICENSE_FILE)

    missing_on_disk = []
    missing_in_license = []
    empty_files = []

    # Check that licensed files exist on disk
    for rel_path in licensed_assets:
        disk_path = PROJECT_ROOT / rel_path
        if not disk_path.exists():
            missing_on_disk.append(rel_path)
        elif disk_path.stat().st_size < 500:
            empty_files.append((rel_path, disk_path.stat().st_size))

    # Check that disk files are recorded in license file
    for rel_path in disk_files:
        if rel_path not in licensed_assets:
            missing_in_license.append(rel_path)

    has_errors = False

    if missing_on_disk:
        print(f"\n[FAIL] {len(missing_on_disk)} asset(s) listed in ASSET_LICENSES.md are missing from disk:")
        for f in missing_on_disk:
            print(f"  - {f}")
        has_errors = True

    if missing_in_license:
        print(f"\n[FAIL] {len(missing_in_license)} asset(s) on disk are not recorded in ASSET_LICENSES.md:")
        for f in missing_in_license:
            print(f"  - {f}")
        has_errors = True

    if empty_files:
        print(f"\n[FAIL] {len(empty_files)} asset(s) appear empty or corrupt (<500 bytes):")
        for f, size in empty_files:
            print(f"  - {f} ({size} bytes)")
        has_errors = True

    if not has_errors:
        print(f"[PASS] All {len(disk_files)} audio assets exist on disk, are non-empty, and are documented in ASSET_LICENSES.md.")
        return True
    return False


if __name__ == "__main__":
    success = validate()
    sys.exit(0 if success else 1)
