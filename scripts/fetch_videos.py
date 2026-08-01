"""Fetch each pastor's most-viewed videos via YouTube Data API v3.

Resolves @handles to channelIds, walks the uploads playlist, then enriches
with view counts + duration. Writes to scripts/.cache/videos/<slug>.json.

Usage:
    python fetch_videos.py --pastor wommack --limit 100
    python fetch_videos.py --all --limit 100
"""
import argparse
import os
import sys
import time

import isodate
import requests
from dotenv import load_dotenv

from common import CACHE, load_pastors, pastor_by_slug, read_json, write_json

load_dotenv()
KEY = os.getenv("YOUTUBE_API_KEY")
if not KEY:
    sys.exit("Set YOUTUBE_API_KEY in .env")

BASE = "https://www.googleapis.com/youtube/v3"


def api(endpoint, **params):
    params["key"] = KEY
    r = requests.get(f"{BASE}/{endpoint}", params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def resolve_channel_id(pastor):
    if pastor.get("channel_id"):
        return pastor["channel_id"]
    handle = pastor["handle"].lstrip("@")
    data = api("channels", part="id", forHandle=handle)
    items = data.get("items", [])
    if not items:
        raise SystemExit(f"Could not resolve handle @{handle}")
    return items[0]["id"]


def uploads_playlist(channel_id):
    data = api("channels", part="contentDetails", id=channel_id)
    return data["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]


def playlist_video_ids(playlist_id, limit):
    ids, page = [], None
    while len(ids) < limit:
        params = dict(part="contentDetails", playlistId=playlist_id, maxResults=50)
        if page:
            params["pageToken"] = page
        data = api("playlistItems", **params)
        for item in data.get("items", []):
            ids.append(item["contentDetails"]["videoId"])
        page = data.get("nextPageToken")
        if not page:
            break
    return ids[:limit]


def enrich(video_ids):
    """Fetch title / duration / views in batches of 50."""
    out = []
    for i in range(0, len(video_ids), 50):
        chunk = video_ids[i:i+50]
        data = api("videos", part="snippet,contentDetails,statistics", id=",".join(chunk))
        for v in data.get("items", []):
            try:
                dur = int(isodate.parse_duration(v["contentDetails"]["duration"]).total_seconds())
            except Exception:
                dur = 0
            out.append({
                "video_id": v["id"],
                "title": v["snippet"]["title"],
                "published_at": v["snippet"]["publishedAt"],
                "duration_sec": dur,
                "view_count": int(v.get("statistics", {}).get("viewCount", 0)),
                "thumbnail": v["snippet"]["thumbnails"].get("medium", {}).get("url", ""),
            })
        time.sleep(0.1)
    return out


def fetch_for(slug, limit):
    pastor = pastor_by_slug(slug)
    channel_id = resolve_channel_id(pastor)
    print(f"[{slug}] channel {channel_id}")
    playlist = uploads_playlist(channel_id)
    print(f"[{slug}] uploads playlist {playlist}")
    ids = playlist_video_ids(playlist, limit=max(limit, 200))  # over-fetch, then keep top-viewed
    print(f"[{slug}] fetched {len(ids)} video ids")
    videos = enrich(ids)
    videos = [v for v in videos if v["duration_sec"] >= 600]  # drop shorts / promos
    videos.sort(key=lambda v: v["view_count"], reverse=True)
    videos = videos[:limit]
    print(f"[{slug}] kept top {len(videos)} by view_count")
    out_path = CACHE / "videos" / f"{slug}.json"
    write_json(out_path, {"pastor": slug, "channel_id": channel_id, "videos": videos})
    print(f"[{slug}] wrote {out_path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pastor", help="single pastor slug")
    ap.add_argument("--all", action="store_true", help="all pastors")
    ap.add_argument("--limit", type=int, default=100)
    args = ap.parse_args()

    if args.all:
        for p in load_pastors():
            fetch_for(p["slug"], args.limit)
    elif args.pastor:
        fetch_for(args.pastor, args.limit)
    else:
        ap.error("--pastor SLUG or --all required")


if __name__ == "__main__":
    main()
