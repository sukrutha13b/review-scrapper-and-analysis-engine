import re
from config import TARGET_TOTAL_REVIEWS

# Precompiled patterns for the quality gate.
_WORD_RE = re.compile(r"\b[A-Za-z]{2,}\b")
_REPEAT_RE = re.compile(r"(.)\1{6,}")           # aaaaaaa, !!!!!!! etc
_URL_RE = re.compile(r"https?://\S+")


def score_relevance(text: str, keywords: list[str]) -> tuple[int, str]:
    text_lower = text.lower()
    matched = [kw for kw in keywords if kw.lower() in text_lower]
    return len(matched), ", ".join(matched)


def _is_quality_text(text: str) -> tuple[bool, str]:
    """Reject scraped junk. Returns (is_good, reject_reason)."""
    if not text or len(text) < 20:
        return False, "too_short"

    # Strip URLs before ratio/word checks — URL-only snippets shouldn't count as content.
    stripped = _URL_RE.sub("", text).strip()
    if len(stripped) < 20:
        return False, "url_only"

    # Alphanumeric/space ratio — reject text that's mostly emoji, symbols, ASCII art.
    alnum_or_space = sum(1 for c in stripped if c.isalnum() or c.isspace())
    if alnum_or_space / len(stripped) < 0.6:
        return False, "non_alnum_heavy"

    # Real word count — need actual prose, not "★★★★☆ 5/5 !!" style noise.
    words = _WORD_RE.findall(stripped)
    if len(words) < 5:
        return False, "too_few_words"

    # Excessive character repetition ("aaaaaaaaaaaa", "!!!!!!!!!!").
    if _REPEAT_RE.search(stripped):
        return False, "repeated_chars"

    return True, ""


def filter_reviews(raw_reviews: list[dict], keywords: list[str], min_score: int = 1) -> list[dict]:
    """Filter raw reviews for quality then relevance. Keeps all if too few pass the keyword filter."""
    print(f"[Filter] Filtering {len(raw_reviews)} reviews with {len(keywords)} keywords")

    reject_counts: dict[str, int] = {}
    scored = []
    for review in raw_reviews:
        text = review.get("text", "")
        ok, reason = _is_quality_text(text)
        if not ok:
            reject_counts[reason] = reject_counts.get(reason, 0) + 1
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
        if raw_id is not None:
            entry["raw_id"] = raw_id
        scored.append(entry)

    if reject_counts:
        breakdown = ", ".join(f"{k}={v}" for k, v in reject_counts.items())
        print(f"[Filter] Rejected {sum(reject_counts.values())} low-quality reviews ({breakdown})")

    filtered = [s for s in scored if s["relevance_score"] >= min_score]

    if len(filtered) < 30 and len(scored) > len(filtered):
        print(f"[Filter] Only {len(filtered)} matched keywords — keeping all {len(scored)} quality reviews")
        filtered = scored

    filtered.sort(key=lambda x: x["relevance_score"], reverse=True)
    filtered = filtered[:TARGET_TOTAL_REVIEWS]

    print(f"[Filter] {len(filtered)} reviews after filtering")
    return filtered
