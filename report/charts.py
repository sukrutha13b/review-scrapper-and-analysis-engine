import plotly.graph_objects as go
import plotly.express as px
import json


def _parse_sentiment(raw):
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except Exception:
            return {"positive": 0, "neutral": 0, "negative": 0}
    return raw if isinstance(raw, dict) else {"positive": 0, "neutral": 0, "negative": 0}


def chart_source_volume(raw_reviews: list[dict]) -> str:
    counts = {}
    for r in raw_reviews:
        src = r.get("source", "unknown")
        counts[src] = counts.get(src, 0) + 1

    fig = px.bar(
        x=list(counts.keys()),
        y=list(counts.values()),
        title="Reviews Collected by Source",
        labels={"x": "Source", "y": "Count"},
        color=list(counts.values()),
        color_continuous_scale="Blues",
    )
    fig.update_layout(showlegend=False)
    return fig.to_json()


def chart_sentiment_donut(cluster_analyses: list[dict]) -> str:
    total_pos = total_neu = total_neg = 0
    for a in cluster_analyses:
        s = _parse_sentiment(a.get("sentiment_json"))
        total_pos += s.get("positive", 0)
        total_neu += s.get("neutral", 0)
        total_neg += s.get("negative", 0)

    fig = go.Figure(go.Pie(
        labels=["Positive", "Neutral", "Negative"],
        values=[total_pos, total_neu, total_neg],
        hole=0.5,
        marker_colors=["#2ecc71", "#95a5a6", "#e74c3c"],
    ))
    fig.update_layout(title="Overall Sentiment Distribution")
    return fig.to_json()


def _safe_float(v, default: float) -> float:
    try:
        f = float(v)
        return f if f == f else default
    except (TypeError, ValueError):
        return default


def chart_theme_treemap(cluster_analyses: list[dict]) -> str:
    labels = [a.get("label") or f"Theme {a.get('cluster_id')}" for a in cluster_analyses]
    frequency = [max(_safe_float(a.get("frequency_score"), 0.1), 0.05) * 100 for a in cluster_analyses]
    intensity = [_safe_float(a.get("intensity_score"), 0.5) for a in cluster_analyses]

    fig = px.treemap(
        names=labels,
        parents=[""] * len(labels),
        values=frequency,
        color=intensity,
        color_continuous_scale="RdYlGn_r",
        title="Theme Landscape (Size: Frequency | Color: Intensity)",
    )
    return fig.to_json()


def chart_sentiment_per_cluster(cluster_analyses: list[dict]) -> str:
    labels = [a.get("label", "")[:30] for a in cluster_analyses]
    pos, neu, neg = [], [], []
    for a in cluster_analyses:
        s = _parse_sentiment(a.get("sentiment_json"))
        pos.append(s.get("positive", 0))
        neu.append(s.get("neutral", 0))
        neg.append(s.get("negative", 0))

    fig = go.Figure()
    fig.add_trace(go.Bar(name="Positive", x=labels, y=pos, marker_color="#2ecc71"))
    fig.add_trace(go.Bar(name="Neutral", x=labels, y=neu, marker_color="#95a5a6"))
    fig.add_trace(go.Bar(name="Negative", x=labels, y=neg, marker_color="#e74c3c"))
    fig.update_layout(barmode="stack", title="Sentiment per Theme", xaxis_tickangle=-30)
    return fig.to_json()


def _empty_figure(title: str) -> str:
    fig = go.Figure()
    fig.update_layout(
        title=title,
        annotations=[dict(text="No data available", showarrow=False, xref="paper", yref="paper", x=0.5, y=0.5)],
    )
    return fig.to_json()


def chart_opportunity_scatter(synthesis: dict) -> str:
    gaps = synthesis.get("opportunity_gaps") or []
    gaps = [g for g in gaps if isinstance(g, dict)]
    if not gaps:
        return _empty_figure("Opportunity Map")

    labels = [(g.get("gap") or "")[:40] for g in gaps]
    x = [_safe_float(g.get("user_frequency"), 0.5) for g in gaps]
    y = [_safe_float(g.get("strategic_fit"), 0.5) for g in gaps]
    effort = [g.get("effort", "medium") for g in gaps]
    colors = {"low": "#2ecc71", "medium": "#f39c12", "high": "#e74c3c"}
    marker_colors = [colors.get(e, "#3498db") for e in effort]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x, y=y, mode="markers+text",
        text=labels, textposition="top center",
        marker=dict(size=16, color=marker_colors, opacity=0.8),
        hovertext=[f"{l}<br>Effort: {e}" for l, e in zip(labels, effort)],
    ))
    fig.update_layout(
        title="Opportunity Map (X: Frequency | Y: Strategic Fit | Color: Effort)",
        xaxis_title="User Frequency",
        yaxis_title="Strategic Fit",
        xaxis=dict(range=[0, 1.1]),
        yaxis=dict(range=[0, 1.1]),
    )
    return fig.to_json()
