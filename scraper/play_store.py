from google_play_scraper import reviews, search, Sort
from config import MAX_REVIEWS_PER_SOURCE

KNOWN_APP_IDS = {
    "spotify": "com.spotify.music",
    "instagram": "com.instagram.android",
    "whatsapp": "com.whatsapp",
    "youtube": "com.google.android.youtube",
    "tiktok": "com.zhiliaoapp.musically",
    "snapchat": "com.snapchat.android",
    "twitter": "com.twitter.android",
    "facebook": "com.facebook.katana",
    "netflix": "com.netflix.mediaclient",
    "uber": "com.ubercab",
}


def find_app_id(app_name: str) -> str | None:
    known = KNOWN_APP_IDS.get(app_name.lower())
    if known:
        return known
    try:
        results = search(app_name, lang="en", country="us", n_hits=10)
        for r in results:
            if r.get("appId"):
                return r["appId"]
    except Exception as e:
        print(f"[PlayStore] App search failed: {e}")
    return None


def scrape_play_store(app_name: str, max_reviews: int | None = None) -> list[dict]:
    limit = max_reviews or MAX_REVIEWS_PER_SOURCE
    print(f"[PlayStore] Searching for: {app_name}")
    app_id = find_app_id(app_name)
    if not app_id:
        print("[PlayStore] Could not find app ID")
        return []

    print(f"[PlayStore] Found app ID: {app_id}, fetching up to {limit} reviews")
    formatted = []
    seen_texts = set()
    token = None

    for sort_order in [Sort.NEWEST, Sort.MOST_RELEVANT]:
        try:
            batch_count = 0
            max_batches = max(5, (limit // 100) + 2)
            while len(formatted) < limit and batch_count < max_batches:
                result, token = reviews(
                    app_id,
                    lang="en",
                    country="us",
                    sort=sort_order,
                    count=min(100, limit - len(formatted)),
                    continuation_token=token if batch_count > 0 else None,
                    filter_score_with=None,
                )
                if not result:
                    break

                for r in result:
                    text = r.get("content", "").strip()
                    if len(text) < 20 or text in seen_texts:
                        continue
                    seen_texts.add(text)
                    formatted.append({
                        "source": "play_store",
                        "app_name": app_name,
                        "text": text,
                        "rating": float(r.get("score", 0)),
                        "review_date": str(r.get("at", "")),
                        "author": r.get("userName", ""),
                        "url": f"https://play.google.com/store/apps/details?id={app_id}",
                    })
                batch_count += 1
                if not token:
                    break
        except Exception as e:
            print(f"[PlayStore] Batch failed ({sort_order}): {e}")
            continue

    print(f"[PlayStore] Scraped {len(formatted)} reviews")
    return formatted[:limit]
