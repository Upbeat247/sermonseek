"""Shared helpers for the SermonSeek batch pipeline."""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CACHE = Path(__file__).resolve().parent / ".cache"
CACHE.mkdir(exist_ok=True)
(CACHE / "videos").mkdir(exist_ok=True)
(CACHE / "transcripts").mkdir(exist_ok=True)
(CACHE / "tagged").mkdir(exist_ok=True)


def load_pastors():
    with open(DATA / "pastors.json") as f:
        return json.load(f)["pastors"]


def pastor_by_slug(slug):
    for p in load_pastors():
        if p["slug"] == slug:
            return p
    raise SystemExit(f"Unknown pastor slug: {slug}")


def read_json(path, default=None):
    if not Path(path).exists():
        return default
    with open(path) as f:
        return json.load(f)


def write_json(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
