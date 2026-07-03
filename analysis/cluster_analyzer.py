from llm import call_gemini
from config import LLM_MIN_INTERVAL_SEC
import time


def analyze_cluster(cluster_id: int, cluster_label: str, reviews: list[str]) -> dict:
    """Analyze a single cluster with Gemini. Returns structured analysis."""
    reviews_text = "\n---\n".join(reviews[:30])

    prompt = f"""You are a UX researcher analyzing user feedback. Below are {min(len(reviews), 30)} real user reviews/comments belonging to the theme: "{cluster_label}".

REVIEWS:
{reviews_text}

Analyze these reviews and return a JSON object with exactly these fields:

{{
  "cluster_id": {cluster_id},
  "label": "{cluster_label}",
  "frustration": "2-3 sentence description of the core frustration",
  "quotes": ["exact quote 1", "exact quote 2", "exact quote 3"],
  "workarounds": "What workarounds or alternatives do users mention? (2-3 sentences)",
  "unmet_need": "What underlying need is not being met? (2-3 sentences)",
  "sentiment_json": {{"positive": 0, "neutral": 0, "negative": 0}},
  "frequency_score": 0.0,
  "intensity_score": 0.0
}}

For sentiment_json: count how many reviews are positive, neutral, negative. Must add up to {min(len(reviews), 30)}.
For frequency_score: 0.0 to 1.0, how common is this theme.
For intensity_score: 0.0 to 1.0, how strongly do users feel (1.0 = very angry).

Return ONLY the JSON object."""

    cap = min(len(reviews), 30)
    data = call_gemini(prompt, expect_json=True)
    if isinstance(data, dict):
        data.setdefault("cluster_id", cluster_id)
        data.setdefault("label", cluster_label)
        data["frequency_score"] = _coerce_float(data.get("frequency_score"), default=0.5)
        data["intensity_score"] = _coerce_float(data.get("intensity_score"), default=0.5)
        data["sentiment_json"] = _coerce_sentiment(data.get("sentiment_json"), cap)
        if not isinstance(data.get("quotes"), list):
            data["quotes"] = []
        return data

    return {
        "cluster_id": cluster_id,
        "label": cluster_label,
        "frustration": "Analysis could not be completed.",
        "quotes": [],
        "workarounds": "",
        "unmet_need": "",
        "sentiment_json": {"positive": 0, "neutral": 0, "negative": cap},
        "frequency_score": 0.5,
        "intensity_score": 0.5,
    }


def _coerce_float(value, default: float) -> float:
    try:
        result = float(value)
        if result != result:  # NaN check
            return default
        return max(0.0, min(1.0, result))
    except (TypeError, ValueError):
        return default


def _coerce_sentiment(value, cap: int) -> dict:
    if not isinstance(value, dict):
        return {"positive": 0, "neutral": 0, "negative": cap}
    result = {}
    for k in ("positive", "neutral", "negative"):
        try:
            result[k] = max(0, int(value.get(k, 0) or 0))
        except (TypeError, ValueError):
            result[k] = 0
    return result


def analyze_all_clusters(clustered_reviews: list[dict]) -> list[dict]:
    """Group reviews by cluster and analyze each."""
    clusters = {}
    for r in clustered_reviews:
        cid = r["cluster_id"]
        if cid == -1:
            continue
        if cid not in clusters:
            clusters[cid] = {"label": r["cluster_label"], "reviews": []}
        clusters[cid]["reviews"].append(r["text"])

    print(f"[ClusterAnalyzer] Analyzing {len(clusters)} clusters")
    analyses = []

    for cluster_id, data in clusters.items():
        print(f"[ClusterAnalyzer] Cluster {cluster_id}: {data['label']} ({len(data['reviews'])} reviews)")
        analysis = analyze_cluster(cluster_id, data["label"], data["reviews"])
        analyses.append(analysis)
        time.sleep(LLM_MIN_INTERVAL_SEC)

    return analyses
