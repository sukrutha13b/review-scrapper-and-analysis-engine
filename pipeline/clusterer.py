import time
import numpy as np
from sklearn.cluster import HDBSCAN, KMeans
from llm import call_gemini
from config import LLM_MIN_INTERVAL_SEC, TARGET_CLUSTER_COUNT


def cluster_embeddings(embeddings: list[list[float]]) -> list[int]:
    n = len(embeddings)
    print(f"[Clusterer] Clustering {n} embeddings")
    if n == 0:
        return []
    if n < 6:
        # Too few points to cluster meaningfully — put everything in one group.
        return [0] * n
    X = np.array(embeddings)

    # Try HDBSCAN first with params scaled to dataset size, aiming for ~TARGET_CLUSTER_COUNT.
    min_size = max(5, n // TARGET_CLUSTER_COUNT)
    clusterer = HDBSCAN(min_cluster_size=min_size, min_samples=3, metric="euclidean")
    labels = clusterer.fit_predict(X)
    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    n_noise = list(labels).count(-1)
    print(f"[Clusterer] HDBSCAN: {n_clusters} clusters, {n_noise} noise points")

    # If too many clusters, tighten iteratively until at or under target.
    tighten_bump = 5
    while n_clusters > TARGET_CLUSTER_COUNT and tighten_bump <= 30:
        clusterer = HDBSCAN(
            min_cluster_size=min_size + tighten_bump,
            min_samples=5,
            metric="euclidean",
        )
        labels = clusterer.fit_predict(X)
        n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
        print(f"[Clusterer] Tightened (bump={tighten_bump}) to {n_clusters} clusters")
        tighten_bump += 5

    # If HDBSCAN fails (0-2 clusters or too much noise), fall back to KMeans.
    if n_clusters < 3 or n_noise > n * 0.4:
        k = min(TARGET_CLUSTER_COUNT, max(3, n // 10))
        print(f"[Clusterer] HDBSCAN insufficient — falling back to KMeans (k={k})")
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = km.fit_predict(X)
        n_clusters = k
        print(f"[Clusterer] KMeans: {n_clusters} clusters")

    return labels.tolist()


def name_clusters(reviews_by_cluster: dict[int, list[str]]) -> dict[int, str]:
    """Use Gemini to generate a short label for each cluster."""
    print(f"[Clusterer] Naming {len(reviews_by_cluster)} clusters")
    cluster_labels = {}

    real_clusters = [(cid, texts) for cid, texts in reviews_by_cluster.items() if cid != -1]
    if -1 in reviews_by_cluster:
        cluster_labels[-1] = "Uncategorized"

    for idx, (cluster_id, texts) in enumerate(real_clusters):
        sample = texts[:15]
        sample_text = "\n---\n".join(sample)
        prompt = f"""Here are {len(sample)} user reviews from the same cluster:

{sample_text}

Provide a SHORT descriptive label (3-6 words) for what this cluster is about.
Focus on the core user problem or theme.
Return ONLY the label text, nothing else."""

        label = call_gemini(prompt, expect_json=False)
        if label:
            cluster_labels[cluster_id] = label.strip().strip('"').strip("'")
        else:
            cluster_labels[cluster_id] = f"Theme {cluster_id}"

        # Pace calls to stay under the free-tier RPM cap (skip after the last one).
        if idx < len(real_clusters) - 1:
            time.sleep(LLM_MIN_INTERVAL_SEC)

    return cluster_labels


def assign_clusters(filtered_reviews: list[dict], embeddings: list[list[float]]) -> list[dict]:
    """Full clustering pipeline: cluster -> name -> assign labels."""
    labels = cluster_embeddings(embeddings)

    reviews_by_cluster = {}
    for i, label in enumerate(labels):
        if label not in reviews_by_cluster:
            reviews_by_cluster[label] = []
        reviews_by_cluster[label].append(filtered_reviews[i]["text"])

    cluster_names = name_clusters(reviews_by_cluster)

    clustered = []
    for i, review in enumerate(filtered_reviews):
        cluster_id = labels[i]
        entry = {
            "text": review["text"],
            "cluster_id": cluster_id,
            "cluster_label": cluster_names.get(cluster_id, f"Theme {cluster_id}"),
            "source": review["source"],
            "app_name": review["app_name"],
        }
        filtered_id = review.get("id")
        if filtered_id is not None:
            entry["filtered_id"] = filtered_id
        clustered.append(entry)

    return clustered
