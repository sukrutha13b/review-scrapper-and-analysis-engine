import requests
import json
import re
import time
from config import MAX_REVIEWS_PER_SOURCE


def _find_reviews_list(node) -> list | None:
    """Recursively search the __NEXT_DATA__ tree for the first list of
    review-shaped dicts. Trustpilot moves this path around between page
    variants (pageProps.reviews, pageProps.businessUnit.reviews, etc.),
    so we look for the shape instead of a fixed path."""
    if isinstance(node, list):
        if node and isinstance(node[0], dict) and (
            "text" in node[0] and ("rating" in node[0] or "stars" in node[0])
        ):
            return node
        for item in node:
            found = _find_reviews_list(item)
            if found:
                return found
    elif isinstance(node, dict):
        for v in node.values():
            found = _find_reviews_list(v)
            if found:
                return found
    return None

KNOWN_TRUSTPILOT_SLUGS = {
    "spotify": "www.spotify.com",
    "netflix": "www.netflix.com",
    "uber": "www.uber.com",
    "instagram": "www.instagram.com",
    "tiktok": "www.tiktok.com",
    "whatsapp": "www.whatsapp.com",
}


def scrape_trustpilot(app_name: str) -> list[dict]:
    """Scrape Trustpilot reviews via their internal JSON API."""
    slug = KNOWN_TRUSTPILOT_SLUGS.get(app_name.lower(), f"www.{app_name.lower()}.com")
    print(f"[Trustpilot] Scraping reviews for: {slug}")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }

    formatted = []
    for page in range(1, 6):
        try:
            url = f"https://www.trustpilot.com/review/{slug}?page={page}"
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code != 200:
                print(f"[Trustpilot] Page {page} returned {resp.status_code}")
                break

            html = resp.text
            match = re.search(
                r'<script[^>]+id="__NEXT_DATA__"[^>]*>(.*?)</script>',
                html, flags=re.DOTALL,
            )
            if not match:
                print(f"[Trustpilot] No __NEXT_DATA__ on page {page}")
                break

            try:
                data = json.loads(match.group(1))
            except json.JSONDecodeError as e:
                print(f"[Trustpilot] JSON parse failed on page {page}: {e}")
                break

            reviews_data = _find_reviews_list(data) or []
            if not reviews_data:
                print(f"[Trustpilot] No reviews found in NEXT_DATA on page {page}")
                break

            for r in reviews_data:
                text = (r.get("text") or "").strip()
                title = (r.get("title") or "").strip()
                if not text or len(text) < 20:
                    continue
                full_text = f"{title}. {text}" if title else text
                rating_raw = r.get("rating", r.get("stars", 0)) or 0
                try:
                    rating = float(rating_raw)
                except (TypeError, ValueError):
                    rating = 0.0
                dates = r.get("dates") or {}
                consumer = r.get("consumer") or {}
                formatted.append({
                    "source": "trustpilot",
                    "app_name": app_name,
                    "text": full_text,
                    "rating": rating,
                    "review_date": dates.get("publishedDate", "") if isinstance(dates, dict) else "",
                    "author": consumer.get("displayName", "") if isinstance(consumer, dict) else "",
                    "url": f"https://www.trustpilot.com/review/{slug}",
                })

            time.sleep(2)
        except Exception as e:
            print(f"[Trustpilot] Page {page} failed: {e}")
            break

    print(f"[Trustpilot] Scraped {len(formatted)} reviews")
    return formatted[:MAX_REVIEWS_PER_SOURCE]
