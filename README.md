# SermonSeek

Find the sermon you actually need. Search by theme + pastor across a curated,
AI-tagged library of messages from renowned Bible teachers.

**Launch pastors**: Andrew Wommack, Joseph Prince, Creflo Dollar, Emmanuel Iren,
Joshua Selman, Joyce Meyer, Chris Oyakhilome.

## How it works

1. A weekly batch pipeline (Python) pulls each pastor's videos + transcripts
   from YouTube.
2. Claude Haiku (via OpenRouter) tags each sermon with its themes, key
   scriptures, and a 3-bullet summary.
3. Tagged JSON is committed to `data/sermons/*.json`.
4. The frontend is a single-file HTML PWA — reads the JSON, does fuzzy search
   client-side, saves favorites/notes/history to `localStorage`.

## Run locally

```bash
npx serve .
```

Open http://localhost:3000. Search works against the sample data in
`data/sermons/*.json`.

## Run the pipeline (adds real sermons)

```bash
cd scripts
cp .env.example .env         # add YOUTUBE_API_KEY + OPENROUTER_API_KEY
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

python fetch_videos.py --pastor wommack --limit 5
python fetch_transcripts.py --pastor wommack
python tag_sermons.py --pastor wommack
python build_data.py
```

Cost: ~1¢ per sermon tagged.

## Deploy

Push to GitHub, connect the repo on Netlify, publish.
Weekly refresh runs via `.github/workflows/refresh.yml` (needs
`YOUTUBE_API_KEY` and `OPENROUTER_API_KEY` as repo secrets).
