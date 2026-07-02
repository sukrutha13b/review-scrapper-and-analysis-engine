"""Coordinates scraping across all sources and compensates when one comes up short."""
from config import (
    MAX_REVIEWS_PER_SOURCE,
    MAX_REVIEWS_PER_SOURCE_TOPUP,
    TARGET_SCRAPED_TOTAL,
)
from scraper.play_store import scrape_play_store
from scraper.app_store import scrape_app_store
from scraper.web_scraper import scrape_web_snippets, generate_extra_queries


def _dedupe(reviews: list[dict], seen_texts: set) -> list[dict]:
    out = []
    for r in reviews:
        text = (r.get("text") or "").strip()
        if not text or text in seen_texts:
            continue
        seen_texts.add(text)
        out.append(r)
    return out


def scrape_all_sources(
    app_name: str,
    web_queries: list[str],
    strategic_goal: str = "",
    on_status=None,
) -> tuple[list[dict], dict]:
    """Scrape every source. If a source under-delivers (e.g. Apple App Store
    fails), top up from working sources so the total remains balanced.

    Returns (all_reviews, per_source_counts)."""
    def _say(msg: str) -> None:
        if on_status:
            on_status(msg)
        else:
            print(msg)

    all_raw: list[dict] = []
    seen_texts: set = set()
    counts: dict[str, int] = {"play_store": 0, "app_store": 0, "web": 0, "reddit": 0}

    # --- Play Store ---
    _say("Scraping Play Store...")
    try:
        play = scrape_play_store(app_name)
        play = _dedupe(play, seen_texts)
        all_raw.extend(play)
        counts["play_store"] = len(play)
    except Exception as e:
        _say(f"Play Store failed: {e}")

    # --- App Store ---
    _say("Scraping App Store...")
    try:
        apple = scrape_app_store(app_name)
        apple = _dedupe(apple, seen_texts)
        all_raw.extend(apple)
        counts["app_store"] = len(apple)
    except Exception as e:
        _say(f"App Store failed: {e}")

    # --- Web / Reddit via SerpAPI ---
    _say("Scraping web & Reddit snippets...")
    try:
        web = scrape_web_snippets(app_name, web_queries)
        web = _dedupe(web, seen_texts)
        all_raw.extend(web)
        for r in web:
            counts[r["source"]] = counts.get(r["source"], 0) + 1
    except Exception as e:
        _say(f"Web scraping failed: {e}")

    # --- Balance: compensate for any weak source by pulling more from working ones ---
    total = len(all_raw)
    deficit = TARGET_SCRAPED_TOTAL - total
    if deficit > 0:
        _say(f"Balancing: {total} reviews collected, targeting {TARGET_SCRAPED_TOTAL} — topping up (deficit {deficit})")

        # 1. Top up Play Store first (fast, high-quality)
        if counts["play_store"] > 0 and deficit > 0:
            want = counts["play_store"] + deficit
            try:
                extra_play = scrape_play_store(app_name, max_reviews=min(want, MAX_REVIEWS_PER_SOURCE_TOPUP))
                new_play = _dedupe(extra_play, seen_texts)
                added = len(new_play) - counts["play_store"]
                if added > 0:
                    all_raw.extend(new_play[counts["play_store"]:])
                    counts["play_store"] += added
                    deficit -= added
                    _say(f"  ▸ Play Store top-up: +{added}")
            except Exception as e:
                _say(f"  ▸ Play Store top-up failed: {e}")

        # 2. Top up Web/Reddit with expanded query set
        if deficit > 0:
            extra_queries = [q for q in generate_extra_queries(app_name, strategic_goal) if q not in web_queries]
            try:
                extra_web = scrape_web_snippets(
                    app_name, extra_queries,
                    max_reviews=min(deficit + 50, MAX_REVIEWS_PER_SOURCE_TOPUP),
                )
                new_web = _dedupe(extra_web, seen_texts)
                for r in new_web:
                    counts[r["source"]] = counts.get(r["source"], 0) + 1
                all_raw.extend(new_web)
                deficit -= len(new_web)
                _say(f"  ▸ Web/Reddit top-up: +{len(new_web)}")
            except Exception as e:
                _say(f"  ▸ Web top-up failed: {e}")

    _say(f"Total after balancing: {len(all_raw)} raw reviews")
    return all_raw, counts
