from serpapi import GoogleSearch
from config import SERPAPI_KEY, MAX_REVIEWS_PER_SOURCE


def scrape_web_snippets(app_name: str, search_queries: list[str], max_reviews: int | None = None) -> list[dict]:
    """Run SerpAPI Google searches and collect result snippets."""
    limit = max_reviews or MAX_REVIEWS_PER_SOURCE
    print(f"[Web] Running {len(search_queries)} queries via SerpAPI (target: {limit})")
    results = []
    seen = set()

    for query in search_queries:
        try:
            search = GoogleSearch({
                "q": query,
                "api_key": SERPAPI_KEY,
                "num": 10,
                "hl": "en",
                "gl": "us",
            })
            data = search.get_dict()

            for item in data.get("organic_results", []):
                snippet = item.get("snippet", "").strip()
                title = item.get("title", "")
                link = item.get("link", "")

                if len(snippet) < 30 or snippet in seen:
                    continue
                seen.add(snippet)

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

        except Exception as e:
            print(f"[Web] Query failed: {e}")
            continue

    print(f"[Web] Collected {len(results)} web snippets")
    return results[:limit]


def generate_extra_queries(app_name: str, strategic_goal: str) -> list[str]:
    """Generate additional search queries for broader coverage."""
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
