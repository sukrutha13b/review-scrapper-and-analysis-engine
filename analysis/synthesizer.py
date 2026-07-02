from llm import call_gemini


def synthesize(app_name: str, strategic_goal: str, cluster_analyses: list[dict]) -> dict:
    """Cross-cluster strategic synthesis."""
    print(f"[Synthesizer] Synthesizing across {len(cluster_analyses)} themes")

    cluster_summaries = []
    for a in cluster_analyses:
        cluster_summaries.append(
            f"Theme: {a.get('label')}\n"
            f"Frustration: {a.get('frustration')}\n"
            f"Unmet Need: {a.get('unmet_need')}\n"
            f"Intensity: {a.get('intensity_score')}/1.0"
        )

    summaries_text = "\n\n".join(cluster_summaries)

    prompt = f"""You are a senior product strategist analyzing user feedback for "{app_name}".
Strategic goal: "{strategic_goal}"

Below are summaries of {len(cluster_analyses)} feedback themes from user reviews:

{summaries_text}

Synthesize and return a JSON object with exactly these keys:

{{
  "executive_summary": "3-4 sentence summary of overall user sentiment around the strategic goal",
  "top_3_findings": ["finding 1", "finding 2", "finding 3"],
  "cross_cutting_patterns": "Patterns appearing across multiple themes (3-4 sentences)",
  "conflicting_needs": "Where do different user segments have contradictory needs? (2-3 sentences)",
  "behavioral_goals": ["What users are trying to do 1", "goal 2", "up to 5"],
  "app_friction_points": ["Where the app blocks users 1", "point 2", "up to 5"],
  "opportunity_gaps": [
    {{"gap": "opportunity description", "strategic_fit": 0.9, "user_frequency": 0.8, "effort": "low"}},
    {{"gap": "opportunity 2", "strategic_fit": 0.7, "user_frequency": 0.6, "effort": "medium"}}
  ],
  "quick_wins": ["actionable recommendation 1", "recommendation 2", "recommendation 3"],
  "strategic_recommendations": ["deeper recommendation 1", "recommendation 2", "recommendation 3"]
}}

Return ONLY the JSON object."""

    data = call_gemini(prompt, expect_json=True)
    if isinstance(data, dict):
        for key in ("top_3_findings", "behavioral_goals", "app_friction_points",
                    "opportunity_gaps", "quick_wins", "strategic_recommendations"):
            if not isinstance(data.get(key), list):
                data[key] = []
        for key in ("executive_summary", "cross_cutting_patterns", "conflicting_needs"):
            if not isinstance(data.get(key), str):
                data[key] = ""
        return data

    return {
        "executive_summary": "Synthesis could not be completed due to API limitations.",
        "top_3_findings": ["Analysis data was collected but synthesis failed"],
        "cross_cutting_patterns": "",
        "conflicting_needs": "",
        "behavioral_goals": [],
        "app_friction_points": [],
        "opportunity_gaps": [],
        "quick_wins": [],
        "strategic_recommendations": [],
    }
