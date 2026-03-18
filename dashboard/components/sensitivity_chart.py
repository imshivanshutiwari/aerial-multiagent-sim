"""Sensitivity chart — Sobol sensitivity heatmap and tactic comparison box plots."""

from __future__ import annotations

from typing import Dict, List

import plotly.graph_objects as go
import pandas as pd


_DARK_BG = "#080C14"
_PLOT_BG = "#0D1321"


def tactic_comparison_boxplot(tactic_results: Dict[str, pd.DataFrame]) -> go.Figure:
    """Side-by-side box plots of kill ratio for different Blue tactics.

    Parameters
    ----------
    tactic_results : dict[str, DataFrame]
        Key = tactic name, value = MC results DataFrame.
    """
    fig = go.Figure()
    colors = ["#00D4FF", "#FFB020", "#00FF88", "#FF3B3B", "#8855FF"]
    for i, (name, df) in enumerate(tactic_results.items()):
        fig.add_trace(go.Box(
            y=df["kill_ratio"],
            name=name,
            marker_color=colors[i % len(colors)],
            boxmean=True,
        ))
    fig.update_layout(
        title="Tactic Comparison — Kill Ratio by Formation",
        yaxis_title="Kill Ratio",
        template="plotly_dark",
        paper_bgcolor=_DARK_BG, plot_bgcolor=_PLOT_BG,
        font=dict(color="#EAF0FF"),
    )
    return fig


def p_win_vs_force_size(results: Dict[str, float]) -> go.Figure:
    """P(Blue wins) vs Blue force size bar chart.

    Parameters
    ----------
    results : dict[str, float]
        Key = scenario label (e.g. "2v4"), value = P(Blue wins).
    """
    labels = list(results.keys())
    values = list(results.values())

    colors = ["#FF3B3B" if v < 0.5 else "#FFB020" if v < 0.9 else "#00FF88"
              for v in values]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=labels, y=values,
        marker_color=colors,
        text=[f"{v:.2f}" for v in values],
        textposition="auto",
    ))
    fig.add_hline(y=0.9, line_dash="dash", line_color="#00FF88",
                  annotation_text="P(win) = 0.90 threshold")
    fig.add_hline(y=0.5, line_dash="dot", line_color="#FFB020",
                  annotation_text="P(win) = 0.50")
    fig.update_layout(
        title="P(Blue Wins) vs Blue Force Size (against 4 Red)",
        xaxis_title="Force Configuration",
        yaxis_title="P(Blue Wins)",
        yaxis_range=[0, 1.05],
        template="plotly_dark",
        paper_bgcolor=_DARK_BG, plot_bgcolor=_PLOT_BG,
        font=dict(color="#EAF0FF"),
    )
    return fig
