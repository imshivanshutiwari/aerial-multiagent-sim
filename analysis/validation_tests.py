"""Validation tests for key model components (non-weapon)."""

from __future__ import annotations

import math

import numpy as np

from engine.physics import compute_turn_rate, KM_TO_M, RAD_TO_DEG
from engine.sensors import SensorModel
from engine.physics import Vec2


def test_sensor_equation() -> bool:
    """Verify P_detect at R = R_max equals 1 - exp(-1)."""
    rng = np.random.default_rng(0)
    sensor = SensorModel(r_max_km=150.0)
    own = Vec2(0.0, 0.0)
    tgt = Vec2(150.0, 0.0)  # exactly R_max away
    p = sensor.detection_probability(own, tgt, target_degradation_factor=1.0)
    expected = 1.0 - math.exp(-1.0)
    return abs(p - expected) < 1e-3


def test_turn_radius() -> bool:
    """Verify turning circle radius matches analytical formula within 1%.

    For small-angle approximation, turn rate w = (g_limit*g0)/v rad/s.
    Radius r = v / w = v^2/(g_limit*g0).
    """
    v = 550.0
    g_limit = 9.0
    g0 = 9.81
    w_deg = compute_turn_rate(v, g_limit)
    w_rad = w_deg / RAD_TO_DEG
    r_from_w = v / w_rad
    r_analytic = (v * v) / (g_limit * g0)
    return abs(r_from_w - r_analytic) / r_analytic < 0.01


def test_rng_reproducibility() -> bool:
    """Verify seeded RNG yields deterministic detection outcomes."""
    sensor = SensorModel(r_max_km=120.0)
    own = Vec2(0.0, 0.0)
    tgt = Vec2(80.0, 0.0)
    out = []
    for _ in range(2):
        rng = np.random.default_rng(123)
        out.append([sensor.detect(rng, own, tgt, 1.0) for _ in range(50)])
    return out[0] == out[1]


def run_all() -> None:
    tests = [
        ("Sensor equation at R=Rmax", test_sensor_equation),
        ("Turn radius identity", test_turn_radius),
        ("Seeded RNG reproducibility", test_rng_reproducibility),
    ]
    ok_all = True
    for name, fn in tests:
        ok = False
        try:
            ok = bool(fn())
        except Exception:
            ok = False
        print(f"{name}: {'PASS' if ok else 'FAIL'}")
        ok_all = ok_all and ok
    raise SystemExit(0 if ok_all else 1)


if __name__ == "__main__":
    run_all()

