"""Send each cached transcript to Claude (via OpenRouter) for theme tagging.

Costs ~$0.011 per sermon. Cached by video_id — safe to re-run.

Usage:
    python tag_sermons.py --pastor wommack
    python tag_sermons.py --all
"""
import argparse
import json
import os
import re
import sys
import time

import requests
from dotenv import load_dotenv

from common import CACHE, load_pastors, read_json, write_json

load_dotenv()
KEY = os.getenv("OPENROUTER_API_KEY")
MODEL = os.getenv("OPENROUTER_MODEL", "anthropic/claude-haiku-4.5")
if not KEY:
    sys.exit("Set OPENROUTER_API_KEY in .env")

URL = "https://openrouter.ai/api/v1/chat/completions"

SYSTEM = """You are an expert theological librarian. Given the full transcript of a Christian sermon, extract structured metadata for a searchable library.

Respond with a single JSON object — no markdown, no code fences, no prose before or after. Just the JSON.

The JSON must have this exact shape:
{
  "primary_theme": "<one dominant theme, 1-3 words, lowercase>",
  "themes": ["<3-6 themes total, lowercase, ordered by prominence>"],
  "key_scriptures": ["<3-8 bible references cited or clearly alluded to, formatted 'Book Chapter:Verse' or 'Book Chapter:Verse-Verse'>"],
  "summary": ["<sentence 1>", "<sentence 2>", "<sentence 3>"],
  "tone": "<one of: teaching | testimony | prophetic | encouragement>",
  "difficulty": "<one of: intro | intermediate | deep>"
}

Guidelines:
- Themes are short spiritual topics people search for: "love", "grace", "healing", "faith", "identity in Christ", "purpose", "prayer", "kingdom", etc.
- Do NOT include the pastor's name, church, or generic words like "sermon" or "message" as themes.
- Summary: 3 concise sentences capturing the core message, not the outline.
- Scriptures: only include ones actually referenced. Do not invent."""


def tagged_path(video_id):
    return CACHE / "tagged" / f"{video_id}.json"


def call_model(transcript):
    body = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"Transcript:\n\n{transcript[:60000]}"},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.2,
    }
    r = requests.post(
        URL,
        headers={
            "Authorization": f"Bearer {KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://sermonseek.app",
            "X-Title": "SermonSeek",
        },
        json=body,
        timeout=120,
    )
    r.raise_for_status()
    data = r.json()
    return data["choices"][0]["message"]["content"], data.get("usage", {})


REQUIRED = {"primary_theme", "themes", "key_scriptures", "summary", "tone", "difficulty"}


def validate(tag):
    if not isinstance(tag, dict) or not REQUIRED.issubset(tag):
        return False
    if not isinstance(tag["themes"], list) or not tag["themes"]:
        return False
    if not isinstance(tag["summary"], list) or len(tag["summary"]) < 2:
        return False
    return True


def extract_json(text):
    """Handle bare JSON or JSON inside a ```json ... ``` fence."""
    text = text.strip()
    if text.startswith("```"):
        m = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
        if m:
            text = m.group(1).strip()
    return json.loads(text)


def tag_one(video):
    vid = video["video_id"]
    if tagged_path(vid).exists():
        return "skip"
    transcript_path = CACHE / "transcripts" / f"{vid}.txt"
    if not transcript_path.exists():
        return "no-transcript"
    transcript = transcript_path.read_text()
    for attempt in (1, 2):
        try:
            raw, usage = call_model(transcript)
            parsed = extract_json(raw)
            if not validate(parsed):
                if attempt == 1:
                    continue
                return "invalid"
            parsed["_usage"] = usage
            write_json(tagged_path(vid), parsed)
            return "ok"
        except Exception as e:
            print(f"    ! {vid} attempt {attempt}: {e}")
            time.sleep(2)
    return "error"


def tag_for(slug):
    cache = read_json(CACHE / "videos" / f"{slug}.json")
    if not cache:
        print(f"[{slug}] no cached videos")
        return
    videos = cache["videos"]
    counts = {"ok": 0, "skip": 0, "no-transcript": 0, "invalid": 0, "error": 0}
    for i, v in enumerate(videos, 1):
        status = tag_one(v)
        counts[status] = counts.get(status, 0) + 1
        print(f"  [{i}/{len(videos)}] {v['video_id']} — {status}")
    print(f"[{slug}] {counts}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pastor")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()

    if args.all:
        for p in load_pastors():
            tag_for(p["slug"])
    elif args.pastor:
        tag_for(args.pastor)
    else:
        ap.error("--pastor SLUG or --all required")


if __name__ == "__main__":
    main()
