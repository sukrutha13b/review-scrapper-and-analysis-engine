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

MAX_REVIEWS_PER_SOURCE = 200
MAX_REVIEWS_PER_SOURCE_TOPUP = 500
TARGET_SCRAPED_TOTAL = 400
TARGET_TOTAL_REVIEWS = 1000

GEMINI_MODEL_CASCADE = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
]

EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"


def validate_config():
    required = {
        "SUPABASE_URL": SUPABASE_URL,
        "SUPABASE_KEY": SUPABASE_KEY,
        "GEMINI_API_KEY": GEMINI_API_KEY,
        "SERPAPI_KEY": SERPAPI_KEY,
    }
    missing = [k for k, v in required.items() if not v]
    if missing:
        raise ValueError(f"Missing environment variables: {', '.join(missing)}")
    return True
