from config import TARGET_TOTAL_REVIEWS


def score_relevance(text: str, keywords: list[str]) -> tuple[int, str]:
    text_lower = text.lower()
    matched = [kw for kw in keywords if kw.lower() in text_lower]
    return len(matched), ", ".join(matched)


def filter_reviews(raw_reviews: list[dict], keywords: list[str], min_score: int = 1) -> list[dict]:
    """Filter raw reviews for relevance. Keeps all if too few pass the filter."""
    print(f"[Filter] Filtering {len(raw_reviews)} reviews with {len(keywords)} keywords")

    scored = []
    for review in raw_reviews:
        text = review.get("text", "")
        if not text or len(text) < 20:
            continue
        score, matched_kws = score_relevance(text, keywords)
        raw_id = review.get("id")
        entry = {
            "text": text,
            "source": review.get("source"),
            "app_name": review.get("app_name"),
            "relevance_score": score,
            "keywords_matched": matched_kws,
        }
        # Only include raw_id when we actually have one — otherwise Supabase would
        # reject the row if the column is typed (e.g. bigint) and receives null-shaped data.
        if raw_id is not None:
            entry["raw_id"] = raw_id
        scored.append(entry)

    filtered = [s for s in scored if s["relevance_score"] >= min_score]

    if len(filtered) < 30 and len(scored) > len(filtered):
        print(f"[Filter] Only {len(filtered)} matched keywords — keeping all {len(scored)} reviews")
        filtered = scored

    filtered.sort(key=lambda x: x["relevance_score"], reverse=True)
    filtered = filtered[:TARGET_TOTAL_REVIEWS]

    print(f"[Filter] {len(filtered)} reviews after filtering")
    return filtered
