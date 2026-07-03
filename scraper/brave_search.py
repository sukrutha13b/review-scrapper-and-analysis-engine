"""Brave Search API — 2000 free queries/month, drop-in replacement for SerpAPI's
general-web queries. Returns None when it can't serve the query so the caller
can decide whether to fall back to SerpAPI."""
import requests
from config import BRAVE_API_KEY

BRAVE_URL = "https://api.search.brave.com/res/v1/web/search"


def search_brave(query: str, app_name: str, count: int = 10) -> list[dict] | None:
    """Returns list of snippets on success, None on unavailability (no key,
    rate limit, or transport error) so the caller knows to try a fallback.
    Returns [] only when Brave successfully returned zero results."""
    if not BRAVE_API_KEY:
        return None

    try:
        resp = requests.get(
            BRAVE_URL,
            params={"q": query, "count": count},
            headers={
                "Accept": "application/json",
                "X-Subscription-Token": BRAVE_API_KEY,
            },
            timeout=15,
        )
    except Exception as e:
        print(f"[Brave] request failed on '{query[:60]}': {e}")
        return None

    if resp.status_code == 429:
        print(f"[Brave] rate limited on '{query[:60]}'")
        return None
    if resp.status_code != 200:
        print(f"[Brave] HTTP {resp.status_code} on '{query[:60]}'")
        return None

    try:
        data = resp.json()
    except Exception as e:
        print(f"[Brave] bad JSON on '{query[:60]}': {e}")
        return None

    results: list[dict] = []
    for item in data.get("web", {}).get("results", []):
        title = (item.get("title") or "").strip()
        snippet = (item.get("description") or "").strip()
        link = item.get("url") or ""
        if len(snippet) < 30:
            continue
        source = "reddit" if "reddit.com" in link else "web"
        full_text = f"{title}. {snippet}" if title else snippet
        results.append({
            "source": source,
            "app_name": app_name,
            "text": full_text,
            "rating": None,
            "review_date": "",
            "author": "",
            "url": link,
        })
    return results
