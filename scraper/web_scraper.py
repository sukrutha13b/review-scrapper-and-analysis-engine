"""Routes web/reddit queries to the cheapest working backend:
  - `site:reddit.com` queries → Reddit's public JSON (free, no key)
  - general web queries → Brave Search (2000/mo free), SerpAPI fallback

Keeps `scrape_web_snippets` and `generate_extra_queries` as the public API so
orchestrator.py doesn't have to know which backend served each query."""
import time

from serpapi import GoogleSearch

from config import SERPAPI_KEY, MAX_REVIEWS_PER_SOURCE
from scraper.brave_search import search_brave
from scraper.reddit_search import search_reddit

# Be polite to Reddit's public JSON — one call/sec avoids their soft rate limit.
REDDIT_DELAY_SEC = 1.0


def _serpapi_search(query: str, app_name: str) -> list[dict]:
    if not SERPAPI_KEY:
        return []
    try:
        data = GoogleSearch({
            "q": query,
            "api_key": SERPAPI_KEY,
            "num": 10,
            "hl": "en",
            "gl": "us",
        }).get_dict()
    except Exception as e:
        print(f"[SerpAPI] failed on '{query[:60]}': {e}")
        return []

    results: list[dict] = []
    for item in data.get("organic_results", []):
        snippet = (item.get("snippet") or "").strip()
        title = item.get("title", "")
        link = item.get("link", "")
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


def scrape_web_snippets(app_name: str, search_queries: list[str], max_reviews: int | None = None) -> list[dict]:
    """Run search queries via the cheapest backend that works for each."""
    limit = max_reviews or MAX_REVIEWS_PER_SOURCE
    reddit_qs = [q for q in search_queries if "site:reddit.com" in q]
    web_qs = [q for q in search_queries if "site:reddit.com" not in q]
    print(f"[Web] {len(reddit_qs)} reddit-direct + {len(web_qs)} general-web queries (target: {limit})")

    results: list[dict] = []
    seen: set[str] = set()

    def _add(items: list[dict]) -> None:
        for r in items:
            text = r.get("text", "")
            if not text or text in seen:
                continue
            seen.add(text)
            results.append(r)

    # 1. Reddit queries — free direct API
    for q in reddit_qs:
        _add(search_reddit(q, app_name))
        time.sleep(REDDIT_DELAY_SEC)

    # 2. General web queries — Brave first, SerpAPI as last resort
    serpapi_calls = 0
    brave_calls = 0
    for q in web_qs:
        items = search_brave(q, app_name)
        if items is None:
            items = _serpapi_search(q, app_name)
            serpapi_calls += 1
        else:
            brave_calls += 1
        _add(items)

    print(
        f"[Web] Collected {len(results)} snippets "
        f"(reddit-direct: {len(reddit_qs)}, brave: {brave_calls}, serpapi: {serpapi_calls})"
    )
    return results[:limit]


def generate_extra_queries(app_name: str, strategic_goal: str) -> list[str]:
    """Additional search queries for broader coverage when the main pass under-delivers."""
    return [
        f"{app_name} review complaints site:reddit.com",
        f"{app_name} problems frustrating site:reddit.com",
        f"why I hate {app_name} site:reddit.com",
        f"{app_name} worst features site:reddit.com",
        f"{app_name} vs competitors better site:reddit.com",
        f"{app_name} needs improvement site:reddit.com",
        f"{app_name} user complaints forum",
        f"{app_name} app issues 2024 2025",
        f"{app_name} {strategic_goal} site:reddit.com",
        f"{app_name} feedback complaints quora",
        f"{app_name} not working properly",
        f"{app_name} worst update ever",
        f"{app_name} losing users why",
        f"{app_name} review trustpilot",
        f"{app_name} app review site:quora.com",
    ]
