"""Kill ratio analyser — summary statistics from Monte Carlo data."""

from __future__ import annotations

import pandas as pd


class KillRatioAnalyser:
    """Compute kill ratio statistics from a Monte Carlo DataFrame."""

    def __init__(self, df: pd.DataFrame) -> None:
        self.df = df

    def p_blue_wins(self) -> float:
        """Fraction of replications where kill ratio > 1.0."""
        return float((self.df["kill_ratio"] > 1.0).mean())

    def mean_kill_ratio(self) -> float:
        return float(self.df["kill_ratio"].mean())

    def std_kill_ratio(self) -> float:
        return float(self.df["kill_ratio"].std())

    def median_kill_ratio(self) -> float:
        return float(self.df["kill_ratio"].median())

    def summary(self) -> dict:
        return {
            "p_blue_wins": self.p_blue_wins(),
            "mean_kill_ratio": self.mean_kill_ratio(),
            "std_kill_ratio": self.std_kill_ratio(),
            "median_kill_ratio": self.median_kill_ratio(),
            "mean_blue_kills": float(self.df["blue_kills"].mean()),
            "mean_red_kills": float(self.df["red_kills"].mean()),
            "mean_blue_losses": float(self.df["blue_losses"].mean()),
            "mean_red_losses": float(self.df["red_losses"].mean()),
            "mean_duration_sec": float(self.df["duration_sec"].mean()),
        }
