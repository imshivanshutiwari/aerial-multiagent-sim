"""Tactic comparator — compare formations using Mann-Whitney U test."""

from __future__ import annotations

from typing import Dict, List

import pandas as pd
from scipy import stats

from simulation.monte_carlo import MonteCarloAnalyser


class TacticComparator:
    """Compare Blue force tactics across Monte Carlo replications.

    Parameters
    ----------
    scenario_path : str
        Base scenario YAML.
    n_replications : int
        Replications per tactic.
    """

    def __init__(self, scenario_path: str, n_replications: int = 100) -> None:
        self.scenario_path = scenario_path
        self.n_replications = n_replications
        self.mc = MonteCarloAnalyser(dt=0.5)

    def run_all_tactics(self) -> Dict[str, pd.DataFrame]:
        """Run MC for each formation tactic and return results dict."""
        tactics = ["line_abreast", "wedge", "fluid_four"]
        results = {}
        for tactic in tactics:
            # Each tactic uses a different seed range for variety
            base_seed = hash(tactic) % 10000
            df = self.mc.run(
                self.scenario_path,
                n_replications=self.n_replications,
                base_seed=base_seed,
            )
            results[tactic] = df
        return results

    @staticmethod
    def mann_whitney_comparison(
        results: Dict[str, pd.DataFrame],
    ) -> List[Dict]:
        """Pairwise Mann-Whitney U tests on kill ratios.

        Returns list of dicts with: tactic_a, tactic_b, U_statistic, p_value, significant.
        """
        names = list(results.keys())
        comparisons = []
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                a = results[names[i]]["kill_ratio"]
                b = results[names[j]]["kill_ratio"]
                u_stat, p_val = stats.mannwhitneyu(a, b, alternative="two-sided")
                comparisons.append({
                    "tactic_a": names[i],
                    "tactic_b": names[j],
                    "U_statistic": float(u_stat),
                    "p_value": float(p_val),
                    "significant": p_val < 0.05,
                })
        return comparisons
