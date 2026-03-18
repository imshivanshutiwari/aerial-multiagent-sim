"""Analysis metrics for non-weapon simulation outcomes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import pandas as pd


@dataclass(frozen=True)
class WinMetrics:
    """Win-rate style metrics using dominance ratio."""

    p_blue_dominant: float
    dominance_mean: float
    dominance_median: float


def compute_win_metrics(df: pd.DataFrame) -> WinMetrics:
    """Compute key metrics from Monte Carlo results."""
    if df.empty:
        return WinMetrics(p_blue_dominant=0.0, dominance_mean=0.0, dominance_median=0.0)
    dom = df["dominance_ratio"].astype(float)
    return WinMetrics(
        p_blue_dominant=float((dom > 1.0).mean()),
        dominance_mean=float(dom.mean()),
        dominance_median=float(dom.median()),
    )


def summarise(df: pd.DataFrame) -> Dict[str, float]:
    wm = compute_win_metrics(df)
    return {
        "p_blue_dominant": wm.p_blue_dominant,
        "dominance_mean": wm.dominance_mean,
        "dominance_median": wm.dominance_median,
        "n": float(len(df)),
    }

