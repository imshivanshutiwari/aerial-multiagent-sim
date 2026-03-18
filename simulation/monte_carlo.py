"""Monte Carlo analyser — run N replications in parallel.

Uses Python multiprocessing.Pool for parallel execution.
Returns a Pandas DataFrame with per-replication metrics.
"""

from __future__ import annotations

import multiprocessing
from functools import partial
from typing import List, Optional

import pandas as pd

from simulation.scenario import Scenario
from simulation.simulation_runner import SimulationRunner


def _run_one(args):
    """Worker function for multiprocessing (must be top-level for pickling)."""
    scenario_path, seed, dt = args
    scenario = Scenario(scenario_path)
    runner = SimulationRunner(dt=dt, history_period=9999.0)
    res = runner.run(scenario, random_seed=seed)
    return {
        "seed": seed,
        "blue_kills": res.blue_kills,
        "red_kills": res.red_kills,
        "blue_losses": res.blue_losses,
        "red_losses": res.red_losses,
        "kill_ratio": res.kill_ratio,
        "duration_sec": res.duration_sec,
        "missiles_fired_blue": res.missiles_fired_blue,
        "missiles_fired_red": res.missiles_fired_red,
    }


class MonteCarloAnalyser:
    """Run N replications of a scenario and collect statistics.

    Parameters
    ----------
    dt : float
        Simulation time step.
    n_workers : int | None
        Number of parallel workers (None = all cores).
    """

    def __init__(self, dt: float = 0.5, n_workers: Optional[int] = None) -> None:
        self.dt = dt
        self.n_workers = n_workers

    def run(
        self,
        scenario_path: str,
        n_replications: int = 200,
        base_seed: int = 0,
    ) -> pd.DataFrame:
        """Run Monte Carlo replications.

        Parameters
        ----------
        scenario_path : str
            Path to YAML scenario file.
        n_replications : int
            Number of replications to run.
        base_seed : int
            Starting seed (each replication uses base_seed + i).

        Returns
        -------
        pd.DataFrame
            One row per replication with columns:
            seed, blue_kills, red_kills, blue_losses, red_losses,
            kill_ratio, duration_sec, missiles_fired_blue, missiles_fired_red.
        """
        args_list = [
            (scenario_path, base_seed + i, self.dt)
            for i in range(n_replications)
        ]

        workers = self.n_workers or max(1, multiprocessing.cpu_count() - 1)
        with multiprocessing.Pool(processes=workers) as pool:
            results = pool.map(_run_one, args_list)

        return pd.DataFrame(results)
