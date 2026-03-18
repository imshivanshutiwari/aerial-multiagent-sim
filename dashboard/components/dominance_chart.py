"""Charts for Monte Carlo dominance metrics."""

from __future__ import annotations

import pandas as pd
import plotly.express as px


def dominance_hist(df: pd.DataFrame) -> "px.Figure":
    fig = px.histogram(
        df,
        x="dominance_ratio",
        nbins=30,
        title="Dominance ratio distribution (Blue / Red)",
        template="plotly_dark",
        height=450,
    )
    return fig


def dominance_vs_duration(df: pd.DataFrame) -> "px.Figure":
    fig = px.scatter(
        df,
        x="duration_sec",
        y="dominance_ratio",
        title="Dominance ratio vs duration",
        template="plotly_dark",
        height=450,
    )
    return fig

