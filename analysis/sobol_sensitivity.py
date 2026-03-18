"""Sobol sensitivity analysis for simulation parameters.

Uses SALib to compute first-order and total-order Sobol indices.
"""

from __future__ import annotations

from typing import Dict, List

import numpy as np
import pandas as pd

try:
    from SALib.sample import saltelli
    from SALib.analyze import sobol as sobol_analyze
    HAS_SALIB = True
except ImportError:
    HAS_SALIB = False

from simulation.scenario import Scenario
from simulation.simulation_runner import SimulationRunner


def sobol_sensitivity(
    scenario_path: str,
    n_samples: int = 64,
) -> Dict:
    """Run Sobol sensitivity analysis on key BVR parameters.

    Parameters varied:
    - Blue radar R_max: [120, 180] km
    - Missile range: [60, 120] km (via chaff probability proxy)
    - Chaff success: [0.15, 0.50]

    Returns dict with 'S1' (first-order) and 'ST' (total) index arrays.
    """
    if not HAS_SALIB:
        return {"error": "SALib not installed. pip install SALib"}

    problem = {
        "num_vars": 3,
        "names": ["radar_rmax_km", "chaff_success", "blue_missile_count"],
        "bounds": [
            [120.0, 180.0],
            [0.15, 0.50],
            [2, 6],
        ],
    }

    param_values = saltelli.sample(problem, n_samples)
    Y = np.zeros(param_values.shape[0])

    for i, params in enumerate(param_values):
        scenario = Scenario(scenario_path)
        # Apply parameter perturbations
        for ac in scenario.blue_aircraft:
            ac.radar.r_max_km = float(params[0])
            ac.ecm.chaff_success_probability = float(params[1])
            ac.missiles_remaining = int(params[2])

        runner = SimulationRunner(dt=0.5, history_period=9999.0)
        res = runner.run(scenario, random_seed=i)
        Y[i] = res.kill_ratio

    Si = sobol_analyze.analyze(problem, Y)
    return {
        "S1": dict(zip(problem["names"], Si["S1"].tolist())),
        "ST": dict(zip(problem["names"], Si["ST"].tolist())),
        "S1_conf": dict(zip(problem["names"], Si["S1_conf"].tolist())),
        "ST_conf": dict(zip(problem["names"], Si["ST_conf"].tolist())),
    }
