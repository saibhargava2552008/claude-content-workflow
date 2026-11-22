"""Scan project files for accidental secrets, personal paths, and tracked media."""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRECTORIES = {".git", ".pytest_cache", "__pycache__", "node_modules", ".venv", "venv"}
MEDIA_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".mp3", ".m4a", ".flac", ".jpg", ".jpeg", ".png", ".gif"}
SCANNABLE_EXTENSIONS = {".md", ".json", ".py", ".ts", ".tsx", ".txt", ".mjs", ".toml", ".yaml", ".yml"}
PERSONAL_PATH_PATTERN = re.compile(r"(?i)\b[a-z]:\\users\\[^\\\s]+")


def scan() -> list[str]:
    issues: list[str] = []
    for dirpath, dirnames, filenames in os.walk(PROJECT_ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRECTORIES]
        for filename in filenames:
            filepath = Path(dirpath) / filename
            relative = filepath.relative_to(PROJECT_ROOT)

            # Skip self
            if filepath == Path(__file__).resolve():
                continue

            # Check for tracked media files
            if filepath.suffix.lower() in MEDIA_EXTENSIONS:
                issues.append(f"tracked media file: {relative}")
                continue

            # Check for .env files
            if filepath.name == ".env" or filepath.name.startswith(".env."):
                issues.append(f"environment file: {relative}")
                continue

            # Scan text files for personal paths
            if filepath.suffix.lower() in SCANNABLE_EXTENSIONS:
                try:
                    content = filepath.read_text(encoding="utf-8").lower()
                except (UnicodeDecodeError, OSError):
                    continue
                if PERSONAL_PATH_PATTERN.search(content):
                    issues.append(f"possible personal path: {relative}")

    return issues


def main() -> int:
    issues = scan()
    if issues:
        print(f"Hygiene check found {len(issues)} issue(s):")
        for issue in issues:
            print(f"  - {issue}")
        return 1
    print("Hygiene check passed — no issues found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
