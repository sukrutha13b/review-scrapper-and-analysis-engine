import time
import google.generativeai as genai
from config import (
    GEMINI_API_KEY,
    GEMINI_EMBEDDING_CASCADE,
    EMBEDDING_BATCH_SIZE,
    EMBEDDING_TASK_TYPE,
)

genai.configure(api_key=GEMINI_API_KEY)


def _embed_batch(texts: list[str], model_name: str) -> list[list[float]]:
    """Call Gemini embed_content on a batch. Returns one vector per input text."""
    result = genai.embed_content(
        model=model_name,
        content=texts,
        task_type=EMBEDDING_TASK_TYPE,
    )
    emb = result["embedding"]
    # Batch input always returns list-of-lists; guard against SDK returning
    # a flat list when a single-item batch slips through.
    if emb and not isinstance(emb[0], list):
        return [emb]
    return emb


def _embed_with_cascade(batch: list[str], max_retries: int = 3) -> list[list[float]]:
    """Try each model in cascade. Retry with backoff on rate limits; move
    to next model on 404/permanent errors so the pipeline never stalls."""
    last_error: Exception | None = None
    for model_name in GEMINI_EMBEDDING_CASCADE:
        for attempt in range(max_retries):
            try:
                return _embed_batch(batch, model_name)
            except Exception as e:
                last_error = e
                err = str(e).lower()
                if "404" in err or "not found" in err or "permission" in err:
                    print(f"[Embedder] {model_name} unavailable, cascading")
                    break
                if "429" in err or "quota" in err or "rate" in err or "resource_exhausted" in err:
                    wait = 15 * (attempt + 1)
                    print(f"[Embedder] Rate limited on {model_name}, waiting {wait}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(wait)
                    if attempt == max_retries - 1:
                        # Exhausted retries on this model — try next one instead of failing.
                        print(f"[Embedder] {model_name} still rate-limited, cascading")
                    continue
                print(f"[Embedder] {model_name} error: {e}")
                break
    raise RuntimeError(f"All embedding models failed. Last error: {last_error}")


def embed_reviews(filtered_reviews: list[dict]) -> tuple[list[dict], list[list[float]]]:
    """Embed all review texts via Gemini embeddings API."""
    texts = [r["text"] for r in filtered_reviews]
    print(f"[Embedder] Embedding {len(texts)} texts via Gemini")

    embeddings: list[list[float]] = []
    for i in range(0, len(texts), EMBEDDING_BATCH_SIZE):
        batch = texts[i : i + EMBEDDING_BATCH_SIZE]
        batch_emb = _embed_with_cascade(batch)
        embeddings.extend(batch_emb)
        print(f"[Embedder] {min(i + EMBEDDING_BATCH_SIZE, len(texts))}/{len(texts)}")

    if len(embeddings) != len(texts):
        raise RuntimeError(
            f"Embedding count mismatch: expected {len(texts)}, got {len(embeddings)}"
        )

    print(f"[Embedder] Done — {len(embeddings)} embeddings generated")
    return filtered_reviews, embeddings
