"""Probabilistic sensing and tracking models (non-weapon).

This adapts classic range-fourth-power radar-like detection in a safety-focused,
non-weapon context: agents can *sense and track* each other to perform
navigation, formation keeping, and avoidance objectives.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np

from .physics import Vec2


@dataclass
class SensorModel:
    """Range-fourth probabilistic detector + tracking quality.

    Parameters
    ----------
    r_max_km:
        Nominal maximum detection range (km) at which P_detect = 1 - exp(-1).
    frequency_ghz:
        Display/metadata only (no full RF radar equation used).
    is_active:
        If False, sensor is off (no detections).
    """

    r_max_km: float
    frequency_ghz: float = 10.0
    is_active: bool = True

    def _effective_rmax_km(self, target_degradation_factor: float) -> float:
        """Apply target counter-sensing degradation to effective range."""
        f = float(target_degradation_factor)
        f = max(0.05, min(1.0, f))
        return self.r_max_km * f

    def detection_probability(self, own_pos: Vec2, target_pos: Vec2, target_degradation_factor: float) -> float:
        """Compute detection probability.

        Uses reduced-form range-fourth model:
            P_detect(R) = 1 - exp(-(R_max_eff / R)^4)
        """
        if not self.is_active:
            return 0.0
        r_km = max(1e-6, own_pos.distance_km(target_pos))
        rmax_eff = self._effective_rmax_km(target_degradation_factor)
        x = (rmax_eff / r_km) ** 4
        # numeric stability for extremely close ranges
        if x > 50:
            return 1.0
        return float(1.0 - math.exp(-x))

    def detect(
        self,
        rng: np.random.Generator,
        own_pos: Vec2,
        target_pos: Vec2,
        target_degradation_factor: float,
    ) -> bool:
        """Stochastically detect a target using the sensor model."""
        p = self.detection_probability(own_pos, target_pos, target_degradation_factor)
        return bool(rng.random() < p)

    def track_quality(
        self,
        own_pos: Vec2,
        target_pos: Vec2,
        target_degradation_factor: float,
    ) -> float:
        """Return tracking quality in [0,1].

        Tracking quality rises with SNR proxy, saturating near 1.0.
        """
        if not self.is_active:
            return 0.0
        r_km = max(1e-6, own_pos.distance_km(target_pos))
        rmax_eff = self._effective_rmax_km(target_degradation_factor)
        snr_proxy = (rmax_eff / r_km) ** 4
        q = 1.0 - math.exp(-0.7 * snr_proxy)
        return float(max(0.0, min(1.0, q)))

    def get_detection_range_for_display(self, target_degradation_factor: float = 1.0) -> float:
        """Return effective detection range in km for visualization."""
        return float(self._effective_rmax_km(target_degradation_factor))


@dataclass
class CounterSensing:
    """Simple non-weapon 'ECM-like' counter-sensing system.

    This intentionally avoids weapon-specific details; it only reduces the
    probability that *others* can detect/track this agent.
    """

    energy_remaining_sec: float = 60.0
    is_active: bool = False

    # When active, others' effective r_max is multiplied by this factor (<1).
    degradation_factor_when_active: float = 0.6

    def activate(self) -> None:
        """Activate counter-sensing if energy remains."""
        if self.energy_remaining_sec > 0:
            self.is_active = True

    def deactivate(self) -> None:
        """Deactivate counter-sensing."""
        self.is_active = False

    def update(self, dt: float) -> None:
        """Update remaining energy over dt seconds."""
        if dt <= 0:
            return
        if self.is_active:
            self.energy_remaining_sec = max(0.0, self.energy_remaining_sec - dt)
            if self.energy_remaining_sec <= 0.0:
                self.is_active = False

    def target_degradation_factor(self) -> float:
        """Factor applied to an observer's effective range against this target."""
        return float(self.degradation_factor_when_active if self.is_active else 1.0)

