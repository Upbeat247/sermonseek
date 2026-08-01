"""Merge cached videos + tags into public data/sermons/*.json + search_index.json.

Only includes videos that have been both fetched AND tagged.

Usage:
    python build_data.py
"""
import datetime as dt
from pathlib import Path

from common import CACHE, DATA, load_pastors, read_json, write_json


def build_pastor(slug):
    videos = read_json(CACHE / "videos" / f"{slug}.json")
    if not videos:
        return []
    out = []
    for v in videos["videos"]:
        tag = read_json(CACHE / "tagged" / f"{v['video_id']}.json")
        if not tag:
            continue
        out.append({
            "video_id": v["video_id"],
            "title": v["title"],
            "published_at": v["published_at"],
            "duration_sec": v["duration_sec"],
            "view_count": v["view_count"],
            "primary_theme": tag["primary_theme"],
            "themes": tag["themes"],
            "key_scriptures": tag["key_scriptures"],
            "summary": tag["summary"],
            "tone": tag["tone"],
            "difficulty": tag["difficulty"],
        })
    return out


def main():
    all_index = []
    for p in load_pastors():
        slug = p["slug"]
        sermons = build_pastor(slug)
        if not sermons:
            print(f"[{slug}] no tagged sermons — skipping")
            continue
        write_json(DATA / "sermons" / f"{slug}.json", {"pastor": slug, "sermons": sermons})
        print(f"[{slug}] wrote {len(sermons)} sermons")
        for s in sermons:
            all_index.append({
                "id": s["video_id"],
                "pastor": slug,
                "title": s["title"],
                "themes": s["themes"],
                "scriptures": s["key_scriptures"],
                "views": s["view_count"],
            })
    write_json(DATA / "search_index.json", {
        "generated_at": dt.datetime.utcnow().isoformat() + "Z",
        "sermons": all_index,
    })
    print(f"wrote search_index.json with {len(all_index)} sermons")


if __name__ == "__main__":
    main()
