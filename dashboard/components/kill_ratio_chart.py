"""Kill ratio charts — histogram, box plots, scatter for Monte Carlo results."""

from __future__ import annotations

import plotly.graph_objects as go
import pandas as pd


_DARK_BG = "#080C14"
_PLOT_BG = "#0D1321"
_BLUE = "#00D4FF"
_RED = "#FF3B3B"
_GREEN = "#00FF88"


def kill_ratio_histogram(df: pd.DataFrame) -> go.Figure:
    """Histogram of kill ratios across Monte Carlo replications."""
    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=df["kill_ratio"], nbinsx=30,
        marker_color=_BLUE, opacity=0.8,
        name="Kill Ratio",
    ))
    fig.add_vline(x=1.0, line_dash="dash", line_color=_RED,
                  annotation_text="Break-even", annotation_position="top right")
    fig.update_layout(
        title="Kill Ratio Distribution",
        xaxis_title="Kill Ratio (Blue kills / Red losses)",
        yaxis_title="Frequency",
        template="plotly_dark",
        paper_bgcolor=_DARK_BG, plot_bgcolor=_PLOT_BG,
        font=dict(color="#EAF0FF"),
    )
    return fig


def losses_boxplot(df: pd.DataFrame) -> go.Figure:
    """Box plots of Blue and Red losses."""
    fig = go.Figure()
    fig.add_trace(go.Box(
        y=df["blue_losses"], name="Blue Losses",
        marker_color=_BLUE, boxmean=True,
    ))
    fig.add_trace(go.Box(
        y=df["red_losses"], name="Red Losses",
        marker_color=_RED, boxmean=True,
    ))
    fig.update_layout(
        title="Losses Distribution",
        yaxis_title="Losses",
        template="plotly_dark",
        paper_bgcolor=_DARK_BG, plot_bgcolor=_PLOT_BG,
        font=dict(color="#EAF0FF"),
    )
    return fig


def kill_ratio_vs_duration(df: pd.DataFrame) -> go.Figure:
    """Scatter: kill ratio vs engagement duration."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["duration_sec"], y=df["kill_ratio"],
        mode="markers",
        marker=dict(size=6, color=_GREEN, opacity=0.6),
        name="Replications",
    ))
    fig.add_hline(y=1.0, line_dash="dash", line_color=_RED)
    fig.update_layout(
        title="Kill Ratio vs Engagement Duration",
        xaxis_title="Duration (s)",
        yaxis_title="Kill Ratio",
        template="plotly_dark",
        paper_bgcolor=_DARK_BG, plot_bgcolor=_PLOT_BG,
        font=dict(color="#EAF0FF"),
    )
    return fig
