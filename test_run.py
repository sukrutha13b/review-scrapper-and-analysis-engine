"""End-to-end test run: Spotify + music discovery goal"""
import json
import copy
import gc

from config import validate_config, TARGET_TOTAL_REVIEWS
from pipeline.storage import (
    generate_run_id, save_raw_reviews, save_filtered_reviews,
    save_clustered_reviews, save_cluster_analysis,  get_raw_reviews,
)
from discovery.source_finder import discover_sources
from scraper.orchestrator import scrape_all_sources
from pipeline.filter import filter_reviews
from pipeline.embedder import embed_reviews
from pipeline.clusterer import assign_clusters
from analysis.cluster_analyzer import analyze_all_clusters
from analysis.synthesizer import synthesize
from report.generator import generate_report

APP_NAME = "Spotify"
GOAL = "Increase meaningful music discovery and reduce repetitive listening behavior"

print("=" * 60)
print(f"TEST RUN: {APP_NAME}")
print(f"GOAL: {GOAL}")
print("=" * 60)

validate_config()
run_id = generate_run_id()
print(f"\nRun ID: {run_id}\n")

# Step 1
print("\n--- STEP 1: Discover sources ---")
sources = discover_sources(APP_NAME, GOAL)
web_queries = sources.get("web_queries", [])
keywords = sources.get("keywords", [])
print(f"Queries: {len(web_queries)}, Keywords: {len(keywords)}")

# Step 2
print("\n--- STEP 2: Scrape ---")
all_raw, source_counts = scrape_all_sources(APP_NAME, web_queries, GOAL)
for src, n in source_counts.items():
    print(f"{src}: {n}")

print(f"\nTOTAL RAW: {len(all_raw)}")
if not all_raw:
    print("ERROR: No reviews collected!")
    exit(1)

saved = save_raw_reviews(all_raw, run_id)
print(f"Saved to Supabase: {saved}")

# Step 3
print("\n--- STEP 3: Filter ---")
filtered = filter_reviews(all_raw, keywords)
if not filtered:
    print("WARNING: No reviews passed filter, using all")
    fallback = []
    for r in all_raw:
        if len(r.get("text", "")) < 20:
            continue
        entry = {
            "text": r["text"], "source": r["source"], "app_name": r["app_name"],
            "relevance_score": 0, "keywords_matched": "",
        }
        if r.get("id") is not None:
            entry["raw_id"] = r["id"]
        fallback.append(entry)
    filtered = fallback[:TARGET_TOTAL_REVIEWS]
save_filtered_reviews(filtered, run_id)
print(f"Filtered: {len(filtered)}")

del all_raw
gc.collect()

# Step 4
print("\n--- STEP 4: Embed (local, free) ---")
reviews_with_data, embeddings = embed_reviews(filtered)
print(f"Embeddings: {len(embeddings)} x {len(embeddings[0])}")

# Step 5
print("\n--- STEP 5: Cluster ---")
clustered = assign_clusters(reviews_with_data, embeddings)
save_clustered_reviews(clustered, run_id)
cluster_ids = set(r["cluster_id"] for r in clustered if r["cluster_id"] != -1)
noise_count = sum(1 for r in clustered if r["cluster_id"] == -1)
print(f"Clusters: {len(cluster_ids)}, Noise: {noise_count}")
for cid in sorted(cluster_ids):
    label = next(r["cluster_label"] for r in clustered if r["cluster_id"] == cid)
    count = sum(1 for r in clustered if r["cluster_id"] == cid)
    print(f"  Cluster {cid}: {label} ({count} reviews)")

del reviews_with_data, embeddings, filtered
gc.collect()

# Step 6
print("\n--- STEP 6: Analyze clusters ---")
analyses = analyze_all_clusters(clustered)
analyses_for_storage = []
for a in analyses:
    a_copy = copy.deepcopy(a)
    if isinstance(a_copy.get("sentiment_json"), dict):
        a_copy["sentiment_json"] = json.dumps(a_copy["sentiment_json"])
    if isinstance(a_copy.get("quotes"), list):
        a_copy["quotes"] = json.dumps(a_copy["quotes"])
    analyses_for_storage.append(a_copy)
save_cluster_analysis(analyses_for_storage, run_id)
print(f"Analyzed: {len(analyses)} clusters")

# Step 7
print("\n--- STEP 7: Synthesize ---")
synthesis_result = synthesize(APP_NAME, GOAL, analyses)
print(f"Executive summary: {synthesis_result.get('executive_summary', 'N/A')[:100]}...")

# Generate report
print("\n--- GENERATING REPORT ---")
raw_for_report = get_raw_reviews(run_id)
report_path = f"spotify_report_{run_id}.html"
generate_report(APP_NAME, GOAL, synthesis_result, analyses, run_id, raw_for_report, clustered, report_path)

print(f"\n{'=' * 60}")
print(f"DONE! Report: {report_path}")
print(f"{'=' * 60}")
