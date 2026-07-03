"""Reddit's public search JSON — free, no key, no SerpAPI quota."""
import requests

REDDIT_UA = "review-analysis-engine/1.0 (research project)"
REDDIT_SEARCH_URL = "https://www.reddit.com/search.json"


def search_reddit(query: str, app_name: str, limit: int = 25) -> list[dict]:
    """Query Reddit directly. Returns snippet-shaped dicts matching the SerpAPI
    output so callers don't have to branch. Empty list on any failure — the
    orchestrator handles under-delivery."""
    q = query.replace("site:reddit.com", "").strip()
    if not q:
        return []

    try:
        resp = requests.get(
            REDDIT_SEARCH_URL,
            params={"q": q, "limit": limit, "sort": "relevance", "t": "year"},
            headers={"User-Agent": REDDIT_UA},
            timeout=15,
        )
    except Exception as e:
        print(f"[Reddit] request failed on '{q[:60]}': {e}")
        return []

    if resp.status_code != 200:
        print(f"[Reddit] HTTP {resp.status_code} on '{q[:60]}'")
        return []

    try:
        data = resp.json()
    except Exception as e:
        print(f"[Reddit] bad JSON on '{q[:60]}': {e}")
        return []

    results: list[dict] = []
    for child in data.get("data", {}).get("children", []):
        d = child.get("data", {})
        title = (d.get("title") or "").strip()
        selftext = (d.get("selftext") or "").strip()
        if not title:
            continue
        # Cap selftext so one huge post doesn't dominate embeddings.
        text = title if not selftext else f"{title}. {selftext[:800]}"
        if len(text) < 30:
            continue
        permalink = d.get("permalink") or ""
        results.append({
            "source": "reddit",
            "app_name": app_name,
            "text": text,
            "rating": None,
            "review_date": "",
            "author": (d.get("author") or "").strip(),
            "url": f"https://www.reddit.com{permalink}" if permalink else "",
        })
    return results
