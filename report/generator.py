from jinja2 import Environment, FileSystemLoader
from report.charts import (
    chart_source_volume,
    chart_sentiment_donut,
    chart_theme_treemap,
    chart_sentiment_per_cluster,
    chart_opportunity_scatter,
)
import json
import os
from datetime import datetime


def generate_report(
    app_name: str,
    strategic_goal: str,
    synthesis: dict,
    cluster_analyses: list[dict],
    run_id: str,
    raw_reviews: list[dict],
    clustered_reviews: list[dict],
    output_path: str = "report_output.html",
) -> str:
    """Generate the full self-contained HTML report."""
    print(f"[ReportGenerator] Building HTML report for run {run_id}")

    for a in cluster_analyses:
        if isinstance(a.get("sentiment_json"), str):
            try:
                a["sentiment_json"] = json.loads(a["sentiment_json"])
            except Exception:
                a["sentiment_json"] = {"positive": 0, "neutral": 0, "negative": 0}

    charts = {
        "source_volume": chart_source_volume(raw_reviews),
        "sentiment_donut": chart_sentiment_donut(cluster_analyses),
        "theme_treemap": chart_theme_treemap(cluster_analyses),
        "sentiment_per_cluster": chart_sentiment_per_cluster(cluster_analyses),
        "opportunity_scatter": chart_opportunity_scatter(synthesis),
    }

    template_data = {
        "app_name": app_name,
        "strategic_goal": strategic_goal,
        "run_id": run_id,
        "generated_at": datetime.now().strftime("%B %d, %Y at %H:%M"),
        "total_raw": len(raw_reviews),
        "total_analyzed": len(clustered_reviews),
        "total_clusters": len(cluster_analyses),
        "sources": list(set(r.get("source") for r in raw_reviews)),
        "synthesis": synthesis,
        "cluster_analyses": cluster_analyses,
        "all_reviews": clustered_reviews[:300],
        "charts": charts,
    }

    template_dir = os.path.dirname(os.path.abspath(__file__))
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("template.html")
    html = template.render(**template_data)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[ReportGenerator] Report saved to: {output_path}")
    return output_path
