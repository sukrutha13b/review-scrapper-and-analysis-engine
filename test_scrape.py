"""Scrape-only test: maximize review volume for Spotify."""
import json
from config import validate_config
from discovery.source_finder import discover_sources
from scraper.play_store import scrape_play_store
from scraper.app_store import scrape_app_store
from scraper.web_scraper import scrape_web_snippets, generate_extra_queries
from scraper.trustpilot import scrape_trustpilot

APP_NAME = "Spotify"
GOAL = "Increase meaningful music discovery and reduce repetitive listening behavior"

validate_config()

print("=" * 60)
print(f"SCRAPE TEST: {APP_NAME}")
print("=" * 60)

# Step 1: Get AI-generated queries + extra queries
print("\n--- Discovering sources ---")
sources = discover_sources(APP_NAME, GOAL)
ai_queries = sources.get("web_queries", [])
extra_queries = generate_extra_queries(APP_NAME, GOAL)
all_queries = ai_queries + [q for q in extra_queries if q not in ai_queries]
keywords = sources.get("keywords", [])
print(f"Total search queries: {len(all_queries)}")
print(f"Keywords: {len(keywords)}")

# Step 2: Scrape all sources
all_raw = []

print("\n--- Play Store ---")
play = scrape_play_store(APP_NAME)
all_raw.extend(play)
print(f"Play Store: {len(play)} reviews")

print("\n--- App Store ---")
apple = scrape_app_store(APP_NAME)
all_raw.extend(apple)
print(f"App Store: {len(apple)} reviews")

print("\n--- Trustpilot ---")
tp = scrape_trustpilot(APP_NAME)
all_raw.extend(tp)
print(f"Trustpilot: {len(tp)} reviews")

print("\n--- Web/Reddit (SerpAPI) ---")
web = scrape_web_snippets(APP_NAME, all_queries)
all_raw.extend(web)
print(f"Web/Reddit: {len(web)} snippets")

# Summary
print("\n" + "=" * 60)
print(f"TOTAL REVIEWS: {len(all_raw)}")
print("=" * 60)

source_counts = {}
for r in all_raw:
    src = r["source"]
    source_counts[src] = source_counts.get(src, 0) + 1
for src, count in sorted(source_counts.items(), key=lambda x: -x[1]):
    print(f"  {src}: {count}")

# Export
with open("scraped_reviews_all.json", "w", encoding="utf-8") as f:
    json.dump(all_raw, f, indent=2, default=str)
print(f"\nExported: scraped_reviews_all.json")
