from llm import call_gemini


def discover_sources(app_name: str, strategic_goal: str) -> dict:
    """Use Gemini to generate targeted search queries and keywords."""
    print(f"[Discovery] Discovering sources for: {app_name} | Goal: {strategic_goal}")

    prompt = f"""You are a research assistant helping analyze user feedback for the app "{app_name}".
Strategic goal: "{strategic_goal}"

Generate structured discovery data to find user complaints, discussions, and feedback.

Return a JSON object with exactly these keys:
{{
  "web_queries": [list of 8-10 Google search queries to find Reddit posts, Quora threads, forum discussions, and user complaints about this app related to the strategic goal. Include at least 3 queries with 'site:reddit.com'],
  "keywords": [list of 25-30 keywords and phrases users would use when discussing this goal/problem with this app, include both positive and negative language]
}}

Return ONLY the JSON object, no other text."""

    data = call_gemini(prompt, expect_json=True)
    if data and "web_queries" in data and "keywords" in data:
        print(f"[Discovery] Found {len(data['web_queries'])} queries, {len(data['keywords'])} keywords")
        return data

    print("[Discovery] Using fallback queries")
    return {
        "web_queries": [
            f"{app_name} problems complaints site:reddit.com",
            f"{app_name} not working frustrating site:reddit.com",
            f"why I stopped using {app_name} site:reddit.com",
            f"{app_name} review complaints",
            f"{app_name} worst features forum",
            f"{app_name} vs competitors better alternative",
            f"{app_name} user experience issues",
            f"{app_name} needs improvement",
        ],
        "keywords": [
            "bug", "crash", "slow", "annoying", "frustrating", "broken",
            "hate", "love", "wish", "please fix", "update", "feature",
            "missing", "alternative", "switch", "better", "worse",
            "recommend", "problem", "issue", "complaint", "feedback",
            "improvement", "suggestion", "support", "help",
        ],
    }
