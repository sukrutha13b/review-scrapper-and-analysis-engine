import google.generativeai as genai
from config import GEMINI_API_KEY, GEMINI_MODEL_CASCADE
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
    # Prefer a full JSON object/array if the model wrapped it in prose.
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


def call_gemini(prompt: str, expect_json: bool = True, max_retries: int = 2) -> dict | list | str | None:
    """Call Gemini with cascade fallback across models.
    If expect_json, parses response as JSON.
    Returns None only if every model and retry fails."""
    for model_name in GEMINI_MODEL_CASCADE:
        for attempt in range(max_retries):
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt)
                raw = _extract_text(response)
                if raw is None:
                    # Safety block or empty candidate — try next model.
                    break
                if not expect_json:
                    return raw
                try:
                    return json.loads(_extract_json_block(raw))
                except json.JSONDecodeError as je:
                    print(f"[LLM] JSON parse failed on {model_name} attempt {attempt + 1}: {je}")
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
    print("[LLM] All models failed")
    return None
