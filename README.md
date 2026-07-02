# AI-Powered Review Discovery Engine

Streamlit app that scrapes user reviews for any app (Play Store, App Store, Reddit/web), clusters them by theme, and generates a strategic UX-research report powered by Gemini.

## Pipeline

1. **Discover** — Gemini generates targeted search queries and keywords for the app + strategic goal.
2. **Scrape** — Play Store (google-play-scraper), App Store (app-store-scraper), Reddit + web via SerpAPI. Auto-balances when one source under-delivers.
3. **Filter** — keyword-relevance scoring, caps to `TARGET_TOTAL_REVIEWS`.
4. **Embed** — local `sentence-transformers/all-MiniLM-L6-v2` (no API cost).
5. **Cluster** — HDBSCAN with KMeans fallback; Gemini names each cluster.
6. **Analyze** — per-cluster Gemini analysis (frustration, quotes, unmet need, sentiment, intensity).
7. **Synthesize** — cross-cluster strategic synthesis (findings, opportunity gaps, quick wins).
8. **Report** — self-contained HTML with Plotly charts.

## Local setup

```bash
python -m venv venv
venv/Scripts/activate      # Windows
# source venv/bin/activate   # macOS / Linux
pip install -r requirements.txt
cp .env.example .env       # fill in your keys
streamlit run app.py
```

You need API keys for:
- **Supabase** — free tier, stores raw/filtered/clustered reviews.
- **Google Generative AI** (Gemini) — free tier works.
- **SerpAPI** — free tier, ~100 searches/month.

## Deploy on Streamlit Community Cloud

1. Push this repo to GitHub.
2. On [share.streamlit.io](https://share.streamlit.io), create a new app pointing at `app.py`.
3. Under **Settings → Secrets**, paste:

```toml
SUPABASE_URL = "https://your-ref.supabase.co"
SUPABASE_KEY = "your-anon-key"
GEMINI_API_KEY = "your-gemini-key"
SERPAPI_KEY = "your-serpapi-key"
```

`config.py` automatically reads either environment variables or `st.secrets`.

## Supabase schema

Create these tables in your Supabase project (all `id` columns are `bigint` identity, all `run_id` are `text`):

- `reviews_raw` — `source, app_name, text, rating, review_date, author, url, run_id`
- `reviews_filtered` — `raw_id, text, source, app_name, relevance_score, keywords_matched, run_id`
- `reviews_clustered` — `filtered_id, text, cluster_id, cluster_label, source, app_name, run_id`
- `cluster_analysis` — `cluster_id, label, frustration, quotes, workarounds, unmet_need, sentiment_json, frequency_score, intensity_score, run_id`

## Running the CLI test

```bash
python test_run.py
```

Runs the full pipeline end-to-end for Spotify + "music discovery" goal and writes `spotify_report_<runid>.html`.
