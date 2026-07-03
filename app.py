import streamlit as st
import json
import copy
import gc
import io
import pandas as pd

st.set_page_config(page_title="Review Discovery Engine", page_icon="🔍", layout="centered")

st.title("🔍 AI-Powered Review Discovery Engine")
st.markdown("Analyze user feedback at scale. Discover themes, frustrations, and opportunities.")
st.divider()

app_name = st.text_input(
    "App Name",
    placeholder="e.g. Spotify, Gaana, Apple Music",
    help="The app you want to analyze",
)

strategic_goal = st.text_area(
    "Strategic Goal",
    placeholder="e.g. Increase meaningful music discovery and reduce repetitive listening behavior",
    help="What problem are you trying to solve or improve?",
    height=100,
)

run_button = st.button("🚀 Run Analysis", type="primary", use_container_width=True)
st.divider()

if run_button:
    if not app_name.strip() or not strategic_goal.strip():
        st.error("Please fill in both the app name and strategic goal.")
        st.stop()

    import re
    from config import validate_config, TARGET_TOTAL_REVIEWS

    try:
        validate_config()
    except ValueError as e:
        st.error(f"Configuration error: {e}")
        st.stop()

    from pipeline.storage import generate_run_id, save_raw_reviews, save_filtered_reviews, save_clustered_reviews, save_cluster_analysis
    from discovery.source_finder import discover_sources
    from scraper.orchestrator import scrape_all_sources
    from pipeline.filter import filter_reviews
    from pipeline.embedder import embed_reviews
    from pipeline.clusterer import assign_clusters
    from analysis.cluster_analyzer import analyze_all_clusters
    from analysis.synthesizer import synthesize
    from report.generator import generate_report

    run_id = generate_run_id()
    st.info(f"Run ID: `{run_id}`")

    all_raw = []
    progress = st.progress(0)
    status = st.empty()

    # --- Step 1: Discover sources ---
    status.text("🔭 Step 1/7 — Discovering sources and keywords...")
    sources = discover_sources(app_name, strategic_goal)
    web_queries = sources.get("web_queries", [])
    keywords = sources.get("keywords", [])
    st.success(f"✅ Found {len(web_queries)} search queries, {len(keywords)} keywords")
    progress.progress(10)

    # --- Step 2: Scrape all sources (balances automatically if any fail) ---
    status.text("📦 Step 2/7 — Scraping all sources...")
    all_raw, source_counts = scrape_all_sources(
        app_name, web_queries, strategic_goal,
        on_status=lambda m: st.write(f"  ▸ {m}"),
    )
    for src, n in source_counts.items():
        if n > 0:
            st.write(f"  ▸ {src}: {n} reviews")
    progress.progress(45)

    if not all_raw:
        st.error("❌ No reviews could be retrieved from any source. Check the app name and API keys.")
        st.stop()

    saved = save_raw_reviews(all_raw, run_id)
    st.success(f"✅ Total: {saved} raw reviews saved")

    # Offer the scraped data as a download BEFORE any downstream step can fail —
    # so if analysis/report generation breaks, the user still walks away with usable data.
    csv_buf = io.StringIO()
    pd.DataFrame(all_raw).to_csv(csv_buf, index=False)
    st.download_button(
        label="📥 Download scraped reviews (CSV)",
        data=csv_buf.getvalue().encode("utf-8"),
        file_name=f"{run_id}_raw_reviews.csv",
        mime="text/csv",
        use_container_width=True,
        key="download_raw",
    )
    st.caption("Save this now — if any later step fails you can still analyze this data yourself.")

    # --- Step 3: Filter ---
    status.text("🔍 Step 3/7 — Filtering for relevant reviews...")
    filtered = filter_reviews(all_raw, keywords)

    if not filtered:
        st.warning("No reviews passed keyword filter — using all reviews instead.")
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
    st.success(f"✅ {len(filtered)} relevant reviews after filtering")
    progress.progress(55)

    del all_raw
    gc.collect()

    # --- Step 4: Embed ---
    status.text("🧠 Step 4/7 — Generating embeddings (local model, no API cost)...")
    reviews_with_data, embeddings = embed_reviews(filtered)
    st.success(f"✅ Generated {len(embeddings)} embeddings")
    progress.progress(65)

    # --- Step 5: Cluster ---
    status.text("🗂️ Step 5/7 — Clustering into themes...")
    clustered = assign_clusters(reviews_with_data, embeddings)
    save_clustered_reviews(clustered, run_id)
    n_themes = len(set(r["cluster_id"] for r in clustered if r["cluster_id"] != -1))
    st.success(f"✅ Discovered {n_themes} themes")
    progress.progress(75)

    del reviews_with_data, embeddings, filtered
    gc.collect()

    # --- Step 6: Analyze clusters ---
    status.text("📊 Step 6/7 — Analyzing each theme with Gemini...")
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
    st.success(f"✅ Analyzed {len(analyses)} themes")
    progress.progress(85)

    # --- Step 7: Synthesize ---
    status.text("🔮 Step 7/7 — Generating strategic synthesis...")
    synthesis_result = synthesize(app_name, strategic_goal, analyses)
    st.success("✅ Strategic synthesis complete")
    progress.progress(95)

    # --- Generate Report ---
    status.text("📄 Generating HTML report...")
    from pipeline.storage import get_raw_reviews
    raw_for_report = get_raw_reviews(run_id)
    safe_name = re.sub(r"[^a-z0-9_-]+", "_", app_name.lower().replace(" ", "_")).strip("_") or "app"
    report_path = f"{safe_name}_report_{run_id}.html"
    generate_report(
        app_name, strategic_goal, synthesis_result, analyses,
        run_id, raw_for_report, clustered, report_path,
    )
    progress.progress(100)
    status.text("")

    st.balloons()
    st.success("🎉 Analysis complete! Your report is ready.")

    with open(report_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    st.download_button(
        label="📥 Download HTML Report",
        data=html_content,
        file_name=report_path,
        mime="text/html",
        use_container_width=True,
    )
