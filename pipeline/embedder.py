from sentence_transformers import SentenceTransformer
from config import EMBEDDING_MODEL_NAME

_model = None


def _get_model():
    global _model
    if _model is None:
        print(f"[Embedder] Loading model: {EMBEDDING_MODEL_NAME}")
        _model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _model


def embed_reviews(filtered_reviews: list[dict]) -> tuple[list[dict], list[list[float]]]:
    """Embed all review texts using sentence-transformers (local, free)."""
    texts = [r["text"] for r in filtered_reviews]
    print(f"[Embedder] Embedding {len(texts)} texts locally")

    model = _get_model()
    embeddings = model.encode(texts, show_progress_bar=True, batch_size=32)
    embeddings_list = [e.tolist() for e in embeddings]

    print(f"[Embedder] Done — {len(embeddings_list)} embeddings generated")
    return filtered_reviews, embeddings_list
