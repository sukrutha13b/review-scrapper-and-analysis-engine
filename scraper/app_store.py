from config import MAX_REVIEWS_PER_SOURCE
import time

KNOWN_APP_STORE = {
    "spotify": ("spotify-music-and-podcasts", 324684580),
    "instagram": ("instagram", 389801252),
    "whatsapp": ("whatsapp-messenger", 310633997),
    "youtube": ("youtube-watch-listen-stream", 544007664),
    "tiktok": ("tiktok", 835599320),
    "snapchat": ("snapchat", 447188370),
    "netflix": ("netflix", 363590051),
    "uber": ("uber-request-a-ride", 368677368),
}


def scrape_app_store(app_name: str) -> list[dict]:
    print(f"[AppStore] Scraping reviews for: {app_name}")
    try:
        from app_store_scraper import AppStore

        known = KNOWN_APP_STORE.get(app_name.lower())
        if known:
            slug, app_id = known
            app = AppStore(country="us", app_name=slug, app_id=app_id)
        else:
            slug = app_name.lower().replace(" ", "-")
            app = AppStore(country="us", app_name=slug)

        app.review(how_many=MAX_REVIEWS_PER_SOURCE)
        time.sleep(2)

        formatted = []
        for r in app.reviews:
            text = r.get("review", "").strip()
            if len(text) < 20:
                continue
            formatted.append({
                "source": "app_store",
                "app_name": app_name,
                "text": text,
                "rating": float(r.get("rating", 0)),
                "review_date": str(r.get("date", "")),
                "author": r.get("userName", ""),
                "url": f"https://apps.apple.com/us/app/{slug}",
            })
        print(f"[AppStore] Scraped {len(formatted)} reviews")
        return formatted[:MAX_REVIEWS_PER_SOURCE]
    except ImportError:
        print("[AppStore] app-store-scraper not installed, skipping")
        return []
    except Exception as e:
        print(f"[AppStore] Scraping failed: {e}")
        return []
