from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY
import uuid

_client: Client | None = None


def _sb() -> Client:
    """Lazy Supabase client so importing this module doesn't crash when env vars are missing."""
    global _client
    if _client is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set before calling storage functions.")
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client


def _write_back_ids(reviews: list[dict], returned: list[dict]) -> None:
    """Copy the DB-generated ids into the in-memory dicts, positionally.
    Supabase returns rows in insertion order, so a positional map is safe."""
    for original, saved in zip(reviews, returned):
        if isinstance(saved, dict) and "id" in saved:
            original["id"] = saved["id"]


def save_raw_reviews(reviews: list[dict], run_id: str) -> int:
    if not reviews:
        return 0
    for r in reviews:
        r["run_id"] = run_id
    result = _sb().table("reviews_raw").insert(reviews).execute()
    _write_back_ids(reviews, result.data or [])
    return len(result.data)


def save_filtered_reviews(reviews: list[dict], run_id: str) -> int:
    if not reviews:
        return 0
    for r in reviews:
        r["run_id"] = run_id
    result = _sb().table("reviews_filtered").insert(reviews).execute()
    _write_back_ids(reviews, result.data or [])
    return len(result.data)


def save_clustered_reviews(reviews: list[dict], run_id: str) -> int:
    if not reviews:
        return 0
    for r in reviews:
        r["run_id"] = run_id
    result = _sb().table("reviews_clustered").insert(reviews).execute()
    _write_back_ids(reviews, result.data or [])
    return len(result.data)


def save_cluster_analysis(analyses: list[dict], run_id: str) -> int:
    if not analyses:
        return 0
    for a in analyses:
        a["run_id"] = run_id
    result = _sb().table("cluster_analysis").insert(analyses).execute()
    return len(result.data)


def get_raw_reviews(run_id: str) -> list[dict]:
    return _sb().table("reviews_raw").select("*").eq("run_id", run_id).execute().data


def get_filtered_reviews(run_id: str) -> list[dict]:
    return _sb().table("reviews_filtered").select("*").eq("run_id", run_id).execute().data


def get_clustered_reviews(run_id: str) -> list[dict]:
    return _sb().table("reviews_clustered").select("*").eq("run_id", run_id).execute().data


def get_cluster_analyses(run_id: str) -> list[dict]:
    return _sb().table("cluster_analysis").select("*").eq("run_id", run_id).execute().data


def generate_run_id() -> str:
    return str(uuid.uuid4())[:8]
