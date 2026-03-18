"""Timeline chart — swim-lane chart of engagement events."""

from __future__ import annotations

from typing import Dict, List

import plotly.graph_objects as go


_DARK_BG = "#080C14"
_PLOT_BG = "#0D1321"

_EVENT_COLORS = {
    "MISSILE_FIRE": "#FFB020",
    "KILL": "#FF3B3B",
    "MISSILE_MISS": "#666666",
    "CHAFF_SUCCESS": "#00FF88",
    "DEFENSIVE_NOTCH": "#00D4FF",
    "FORMATION_REJOIN": "#8855FF",
}


def make_timeline(event_log: List[Dict]) -> go.Figure:
    """Create a swim-lane timeline of engagement events.

    X-axis: time (seconds).
    Each row: one entity (aircraft or missile).
    Colour: event type.
    """
    fig = go.Figure()

    actors = sorted(set(e.get("actor", "") for e in event_log))
    actor_idx = {a: i for i, a in enumerate(actors)}

    for etype, color in _EVENT_COLORS.items():
        subset = [e for e in event_log if e.get("type") == etype]
        if not subset:
            continue
        ts = [e["t"] for e in subset]
        ys = [actor_idx.get(e.get("actor", ""), 0) for e in subset]
        texts = [e.get("detail", "") for e in subset]
        fig.add_trace(go.Scatter(
            x=ts, y=ys, mode="markers",
            marker=dict(size=10, color=color, symbol="diamond"),
            text=texts,
            hovertemplate="%{text}<br>t=%{x:.1f}s",
            name=etype.replace("_", " ").title(),
        ))

    fig.update_layout(
        title="Engagement Timeline (Swim Lane)",
        xaxis_title="Time (s)",
        yaxis=dict(
            tickvals=list(range(len(actors))),
            ticktext=actors,
            title="Entity",
        ),
        template="plotly_dark",
        paper_bgcolor=_DARK_BG, plot_bgcolor=_PLOT_BG,
        height=max(400, 50 * len(actors)),
        font=dict(color="#EAF0FF"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    return fig
