"""Swerling Type-1 Radar model for BVR Combat Simulation.

Implements the range-fourth-power detection probability:
    P_detect(R) = 1 - exp(-(R_max_eff / R)^4)

When the target is jamming, the effective R_max is reduced by 40%.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from engine.physics import distance_km


@dataclass
class Radar:
    """Aircraft radar sensor.

    Parameters
    ----------
    r_max_km : float
        Maximum detection range in km (where P_detect ≈ 0.632).
    frequency_ghz : float
        Radar frequency for display/metadata.
    is_active : bool
        Whether the radar is currently emitting.
    """

    r_max_km: float = 150.0
    frequency_ghz: float = 10.0
    is_active: bool = True

    # ---- tracking state (set externally by agent logic) ----
    tracking_target_id: str | None = field(default=None, repr=False)

    # ------------------------------------------------------------------
    # Detection
    # ------------------------------------------------------------------
    def detect(
        self,
        own_x: float, own_y: float, own_z: float,
        target_x: float, target_y: float, target_z: float,
        target_rcs: float,
        target_jamming_active: bool,
        rng: np.random.Generator,
    ) -> bool:
        """Stochastic detection using 3D distance and SNR-based model."""
        if not self.is_active:
            return False
        
        # 3D Elevation Gate: Simplified -60 to +60 degrees
        dx, dy, dz = target_x - own_x, target_y - own_y, target_z - own_z
        dist_sq = dx**2 + dy**2 + dz**2
        r_km = math.sqrt(dist_sq)
        if r_km < 0.1: return True
        
        dist_2d = math.sqrt(dx**2 + dy**2)
        elevation = math.degrees(math.atan2(dz, dist_2d))
        if abs(elevation) > 60.0: return False # Target above/below radar cone

        # Calculate SNR (Simplified Radar Range Equation)
        # Scale K so that at r_max and ref_rcs, SNR=1.0
        ref_rcs = 3.0
        k = (self.r_max_km ** 4) / ref_rcs
        jamming_factor = 5.0 if target_jamming_active else 1.0
        l_atm = 10 ** (0.02 * r_km / 10.0) # 0.02 dB/km loss
        
        snr = (k * target_rcs) / (r_km**4 * jamming_factor * l_atm)
        
        # Detection probability
        p = float(1.0 - math.exp(-snr)) if snr < 10.0 else 1.0
        return bool(rng.random() < p)

    # ------------------------------------------------------------------
    # Tracking quality
    # ------------------------------------------------------------------
    def track(
        self,
        own_x: float, own_y: float, own_z: float,
        target_x: float, target_y: float, target_z: float,
        target_rcs: float,
        target_jamming_active: bool,
    ) -> float:
        """3D tracking quality 0.0 – 1.0 derived from SNR."""
        if not self.is_active:
            return 0.0
        r_km = max(1e-6, distance_km(own_x, own_y, own_z, target_x, target_y, target_z))
        
        ref_rcs = 3.0
        k = (self.r_max_km ** 4) / ref_rcs
        jamming_factor = 5.0 if target_jamming_active else 1.0
        l_atm = 10 ** (0.02 * r_km / 10.0)
        
        snr = (k * target_rcs) / (r_km**4 * jamming_factor * l_atm)
        return float(min(1.0, 1.0 - math.exp(-0.8 * snr)))

    # ------------------------------------------------------------------
    # Display helper
    # ------------------------------------------------------------------
    def get_detection_range_for_display(
        self, target_jamming_active: bool = False
    ) -> float:
        """Current effective detection range in km (for radar sweep viz)."""
        return self._effective_rmax(target_jamming_active)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _effective_rmax(self, target_jamming_active: bool) -> float:
        """Apply jamming degradation to R_max."""
        if target_jamming_active:
            return self.r_max_km * 0.6
        return self.r_max_km

    def _detection_probability(
        self,
        own_x: float,
        own_y: float,
        target_x: float,
        target_y: float,
        target_jamming_active: bool,
    ) -> float:
        r_km = max(1e-6, distance_km(own_x, own_y, target_x, target_y))
        rmax = self._effective_rmax(target_jamming_active)
        x = (rmax / r_km) ** 4
        if x > 50:
            return 1.0
        return float(1.0 - math.exp(-x))
