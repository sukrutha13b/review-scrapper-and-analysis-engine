import google.generativeai as genai
import requests
from config import (
    GEMINI_API_KEY,
    GEMINI_MODEL_CASCADE,
    GROK_API_KEY,
    GROK_BASE_URL,
    GROK_MODEL_CASCADE,
)
import json
import re
import time

genai.configure(api_key=GEMINI_API_KEY)


def _extract_text(response) -> str | None:
    """Safely extract text from a Gemini response, handling safety blocks
    and empty-candidate responses without raising."""
    try:
        candidates = getattr(response, "candidates", None) or []
        if not candidates:
            feedback = getattr(response, "prompt_feedback", None)
            print(f"[LLM] No candidates returned (prompt_feedback={feedback})")
            return None
        parts = getattr(candidates[0].content, "parts", None) or []
        text = "".join(getattr(p, "text", "") for p in parts).strip()
        if not text:
            finish = getattr(candidates[0], "finish_reason", None)
            print(f"[LLM] Empty text in candidate (finish_reason={finish})")
            return None
        return text
    except Exception as e:
        print(f"[LLM] Failed to extract text: {e}")
        return None


def _extract_json_block(raw: str) -> str:
    """Strip code fences and isolate the first {...} or [...] JSON block."""
    stripped = re.sub(r"```(?:json)?\s*|```", "", raw).strip()
    for open_ch, close_ch in (("{", "}"), ("[", "]")):
        start = stripped.find(open_ch)
        if start == -1:
            continue
        depth = 0
        for i in range(start, len(stripped)):
            c = stripped[i]
            if c == open_ch:
                depth += 1
            elif c == close_ch:
                depth -= 1
                if depth == 0:
                    return stripped[start : i + 1]
    return stripped


def _parse_or_return(raw: str, expect_json: bool):
    if not expect_json:
        return raw
    try:
        return json.loads(_extract_json_block(raw))
    except json.JSONDecodeError:
        return None


def _try_gemini(prompt: str, expect_json: bool, max_retries: int):
    """Cascade through Gemini models. Returns parsed value or None."""
    for model_name in GEMINI_MODEL_CASCADE:
        for attempt in range(max_retries):
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt)
                raw = _extract_text(response)
                if raw is None:
                    break  # safety block or empty — try next model
                parsed = _parse_or_return(raw, expect_json)
                if parsed is not None:
                    return parsed
                # JSON parse failed — retry same model once, then move on.
                print(f"[LLM] JSON parse failed on {model_name} attempt {attempt + 1}")
                continue
            except Exception as e:
                err = str(e).lower()
                if "404" in err or "not found" in err:
                    print(f"[LLM] {model_name} not available, skipping")
                    break
                if "429" in err or "quota" in err or "rate" in err or "resource_exhausted" in err:
                    wait = 15 * (attempt + 1)
                    print(f"[LLM] Rate limited on {model_name}, waiting {wait}s...")
                    time.sleep(wait)
                    continue
                print(f"[LLM] {model_name} error: {e}")
                break
    return None


def _try_grok(prompt: str, expect_json: bool, max_retries: int):
    """Fallback cascade through Grok (xAI) models. Returns parsed value or None."""
    if not GROK_API_KEY:
        return None

    headers = {
        "Authorization": f"Bearer {GROK_API_KEY}",
        "Content-Type": "application/json",
    }
    for model_name in GROK_MODEL_CASCADE:
        for attempt in range(max_retries):
            try:
                payload = {
                    "model": model_name,
                    "messages": [{"role": "user", "content": prompt}],
                }
                if expect_json:
                    payload["response_format"] = {"type": "json_object"}
                r = requests.post(
                    f"{GROK_BASE_URL}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=90,
                )
                if r.status_code == 429:
                    wait = 15 * (attempt + 1)
                    print(f"[LLM] Grok rate limited on {model_name}, waiting {wait}s...")
                    time.sleep(wait)
                    continue
                if r.status_code == 404 or r.status_code == 400:
                    print(f"[LLM] Grok {model_name} unavailable ({r.status_code}), skipping")
                    break
                r.raise_for_status()
                raw = r.json()["choices"][0]["message"]["content"].strip()
                if not raw:
                    break
                parsed = _parse_or_return(raw, expect_json)
                if parsed is not None:
                    return parsed
                print(f"[LLM] Grok JSON parse failed on {model_name} attempt {attempt + 1}")
                continue
            except requests.RequestException as e:
                print(f"[LLM] Grok {model_name} network error: {e}")
                break
            except Exception as e:
                print(f"[LLM] Grok {model_name} error: {e}")
                break
    return None


def call_gemini(prompt: str, expect_json: bool = True, max_retries: int = 2) -> dict | list | str | None:
    """Kept for backward compat. Tries Gemini cascade, then Grok if configured."""
    result = _try_gemini(prompt, expect_json, max_retries)
    if result is not None:
        return result

    if GROK_API_KEY:
        print("[LLM] Gemini cascade exhausted — falling back to Grok")
        result = _try_grok(prompt, expect_json, max_retries)
        if result is not None:
            return result

    print("[LLM] All models failed")
    return None
