import os

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"

from dotenv import load_dotenv

load_dotenv()


def _get_secret(key: str) -> str | None:
    """Read a config value from env, falling back to st.secrets on Streamlit Cloud.
    Returns None for missing or blank values so validate_config() can flag them."""
    val = (os.getenv(key) or "").strip()
    if val:
        return val
    try:
        import streamlit as st
        val = str(st.secrets[key]).strip() if key in st.secrets else ""
    except Exception:
        val = ""
    return val or None


_raw_url = _get_secret("SUPABASE_URL") or ""
SUPABASE_URL = _raw_url.rstrip("/").removesuffix("/rest/v1").rstrip("/") if _raw_url else None
SUPABASE_KEY = _get_secret("SUPABASE_KEY")

GEMINI_API_KEY = _get_secret("GEMINI_API_KEY")
SERPAPI_KEY = _get_secret("SERPAPI_KEY")
BRAVE_API_KEY = _get_secret("BRAVE_API_KEY")  # preferred: 2000 free queries/mo vs SerpAPI's 250
GROK_API_KEY = _get_secret("GROK_API_KEY")  # optional fallback if Gemini exhausts

GROK_BASE_URL = "https://api.x.ai/v1"
GROK_MODEL_CASCADE = [
    "grok-4-fast",
    "grok-3-mini",
]

MAX_REVIEWS_PER_SOURCE = 200
MAX_REVIEWS_PER_SOURCE_TOPUP = 500
TARGET_SCRAPED_TOTAL = 400
TARGET_TOTAL_REVIEWS = 200  # post-filter cap — ~20 per cluster at 10 clusters

GEMINI_MODEL_CASCADE = [
    "gemini-2.5-flash",       # best quality, tightest free-tier RPM
    "gemini-2.0-flash",
    "gemini-1.5-flash",       # larger free-tier budget — long tail if 2.x exhaust
    "gemini-2.0-flash-lite",
    "gemini-1.5-flash-8b",    # smallest / cheapest, last resort
]

# Safety pacing for Gemini free tier (10 RPM on 2.5-flash → 6s min between calls).
LLM_MIN_INTERVAL_SEC = 6

# Target cluster count. Clusterer will aim for ~this many themes.
TARGET_CLUSTER_COUNT = 10

GEMINI_EMBEDDING_CASCADE = [
    "models/gemini-embedding-001",
    "models/text-embedding-004",
]
EMBEDDING_BATCH_SIZE = 100
EMBEDDING_TASK_TYPE = "clustering"


def validate_config():
    required = {
        "SUPABASE_URL": SUPABASE_URL,
        "SUPABASE_KEY": SUPABASE_KEY,
        "GEMINI_API_KEY": GEMINI_API_KEY,
    }
    missing = [k for k, v in required.items() if not v]
    if missing:
        raise ValueError(f"Missing environment variables: {', '.join(missing)}")
    if not (BRAVE_API_KEY or SERPAPI_KEY):
        raise ValueError("Missing web-search key: set BRAVE_API_KEY (preferred) or SERPAPI_KEY")
    return True
