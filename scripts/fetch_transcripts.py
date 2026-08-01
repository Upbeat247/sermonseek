"""Fetch YouTube auto-captions for each cached video.

Skips videos already transcribed. Skips (and marks) videos with no captions.

Usage:
    python fetch_transcripts.py --pastor wommack
    python fetch_transcripts.py --all
"""
import argparse
import json
import time
from pathlib import Path

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    NoTranscriptFound, TranscriptsDisabled, VideoUnavailable,
)

from common import CACHE, load_pastors, read_json

_yta = YouTubeTranscriptApi()


def transcript_path(video_id):
    return CACHE / "transcripts" / f"{video_id}.txt"


def missing_path(video_id):
    return CACHE / "transcripts" / f"{video_id}.MISSING"


def fetch_one(video_id):
    if transcript_path(video_id).exists() or missing_path(video_id).exists():
        return "skip"
    try:
        fetched = _yta.fetch(video_id, languages=["en", "en-US", "en-GB"])
    except (NoTranscriptFound, TranscriptsDisabled, VideoUnavailable):
        missing_path(video_id).write_text("no captions")
        return "missing"
    except Exception as e:
        print(f"  ! {video_id}: {e}")
        return "error"
    # v1 returns a FetchedTranscript that iterates FetchedTranscriptSnippet objects
    text = " ".join(s.text.replace("\n", " ") for s in fetched)
    transcript_path(video_id).write_text(text)
    return "ok"


def fetch_for(slug):
    cache = read_json(CACHE / "videos" / f"{slug}.json")
    if not cache:
        print(f"[{slug}] no cached videos — run fetch_videos.py first")
        return
    videos = cache["videos"]
    print(f"[{slug}] {len(videos)} videos")
    counts = {"ok": 0, "skip": 0, "missing": 0, "error": 0}
    for v in videos:
        status = fetch_one(v["video_id"])
        counts[status] = counts.get(status, 0) + 1
        if status == "ok":
            print(f"  + {v['video_id']}")
            time.sleep(0.3)
    print(f"[{slug}] {counts}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pastor")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()

    if args.all:
        for p in load_pastors():
            fetch_for(p["slug"])
    elif args.pastor:
        fetch_for(args.pastor)
    else:
        ap.error("--pastor SLUG or --all required")


if __name__ == "__main__":
    main()
