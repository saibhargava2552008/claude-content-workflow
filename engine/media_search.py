"""Search and download stock images with license tracking.

    python engine/media_search.py search "laptop coding" [--source openverse] [--limit 10]
    python engine/media_search.py download openverse <id>
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

USER_AGENT = "ContentWorkflow/1.0 (local production tool)"
ROOT = Path(__file__).resolve().parents[1]

LICENSE_MAP = {"cc0": "CC0-1.0", "pdm": "PDM-1.0", "by": "CC-BY-{v}", "by-sa": "CC-BY-SA-{v}"}


def _load_env_key(key: str) -> str | None:
    if os.environ.get(key):
        return os.environ[key]
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.startswith(key + "="):
                return line.split("=", 1)[1].strip()
    return None


def _fetch(url: str, headers: dict | None = None) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def _resolve_license(item: dict) -> str:
    lic = (item.get("license") or "").lower()
    template = LICENSE_MAP.get(lic)
    if not template:
        return f"UNKNOWN:{lic}"
    version = item.get("license_version") or "4.0"
    return template.format(v=version if "." in version else f"{version}.0")


def search_images(query: str, source: str = "openverse", limit: int = 10) -> list[dict]:
    if source == "openverse":
        params = urllib.parse.urlencode({
            "q": query, "license": "cc0,pdm,by,by-sa",
            "license_type": "commercial,modification",
            "page_size": limit, "mature": "false",
        })
        data = json.loads(_fetch(f"https://api.openverse.org/v1/images/?{params}"))
        return [{
            "source": "openverse", "id": it["id"], "title": it.get("title"),
            "url": it["url"], "license": _resolve_license(it),
            "attribution": it.get("attribution"), "page": it.get("foreign_landing_url"),
            "creator": it.get("creator"),
            "dimensions": f"{it.get('width')}x{it.get('height')}",
            "format": it.get("filetype"),
        } for it in data["results"]]
    raise SystemExit(f"Unsupported source: {source}")


def download_image(item: dict, output_dir: Path | None = None) -> Path:
    ext = (item.get("format") or "jpg").lower()
    dest = (output_dir or ROOT / "downloads")
    dest.mkdir(parents=True, exist_ok=True)
    filepath = dest / f"{item['source']}_{item['id']}.{ext}"
    filepath.write_bytes(_fetch(item["url"]))
    sidecar = filepath.parent / (filepath.name + ".license.json")
    sidecar.write_text(json.dumps(item, indent=2, ensure_ascii=False), encoding="utf-8")
    return filepath


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["search", "download"])
    ap.add_argument("args", nargs="*")
    ap.add_argument("--source", default="openverse")
    ap.add_argument("--limit", type=int, default=10)
    args = ap.parse_args()

    if args.command == "search":
        for i, r in enumerate(search_images(" ".join(args.args), args.source, args.limit)):
            print(f"[{i}] {r['source']}:{r['id']}  {r['license']:12} {r['dimensions']:>10}  {(r['title'] or '')[:50]}")
    elif args.command == "download":
        source, item_id = args.args[0], args.args[1]
        item = json.loads(_fetch(f"https://api.openverse.org/v1/images/{item_id}/"))
        resolved = {
            "source": source, "id": item["id"], "title": item.get("title"),
            "url": item["url"], "license": _resolve_license(item),
            "attribution": item.get("attribution"), "format": item.get("filetype"),
        }
        print(download_image(resolved))


if __name__ == "__main__":
    main()
