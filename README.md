# ranked-channel

Browser-orchestrated ranked “channel” playlist engine with explicit exploration/exploitation controls and a minimal web UI.

## What it does

1. Start from a **seed video URL**
2. Use Playwright to extract:
   - stable `id_video` from embedded `<script>` (regex)
   - tags from the page DOM
   - related-video cards (URLs, title, stable IDs when present)
3. Build a directed **co-occurrence graph** (A → B edge weight increments when B appears as related on A)
4. Rank candidates with a combined score:
   - relatedness frequency (graph signal)
   - taste similarity to an “enjoyed” tag profile
   - diversity penalty against the last K picks
   - novelty bonus for under-explored items
5. Sample the next pick with a policy (softmax temperature by default)
6. Serve a minimal web “channel” player UI and accept feedback (👍/⏭/👎)

## Quickstart

### 1) Install dependencies

Using `uv` (recommended):

```bash
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
python -m playwright install chromium
```

Or with `pip`:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
```

### 2) Run the server

```bash
uvicorn ranked_channel.api.app:app --reload
```

Open the UI at:

- http://127.0.0.1:8000

### 3) Run a session from CLI (optional)

```bash
python -m ranked_channel.cli run --seed-url "https://example.com/video/..." --n 20 --profile discovery
```

## Notes / customization

This repo ships with **default CSS selectors** for:
- `id_video` extraction (script regex)
- tags selector
- related cards selector

Different sites will need selector tweaks in `ranked_channel/crawl/selectors.py`.

The goal is to keep scraping ToS-compliant: no bypassing logins/paywalls/CAPTCHAs/DRM; throttle requests; cache; dedupe.

## Directory layout

- `ranked_channel/crawl/` Playwright + extraction
- `ranked_channel/store/` SQLite schema + persistence
- `ranked_channel/engine/` ranking + policy + session runner
- `ranked_channel/api/` FastAPI + static UI + feedback endpoints
- `web/` minimal HTML/JS UI
