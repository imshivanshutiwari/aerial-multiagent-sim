"""Engagement rules – kill probability and BVR engagement checks.

Kill probability model
----------------------
- Within 30 m: P_kill = 0.85
- 30–100 m:   P_kill = 0.85 * exp(-(miss_distance - 30) / 20)
- Beyond 100 m: P_kill = 0
"""

import math
from engine.physics import distance_km

def kill_probability(miss_distance_m: float) -> float:
    """Compute kill probability given missile miss distance."""
    if miss_distance_m <= 30.0:
        return 0.85
    if miss_distance_m <= 100.0:
        return 0.85 * math.exp(-(miss_distance_m - 30.0) / 20.0)
    return 0.0


def missile_in_range(range_km: float, missile_range_km: float) -> bool:
    """Check if target is within missile engagement range."""
    return range_km <= missile_range_km


def estimated_pk(
    own_x: float, own_y: float, own_z: float,
    target_x: float, target_y: float, target_z: float,
    missile_range_km: float, 
    tracking_quality: float
) -> float:
    """Rough PK estimate used by AI decision logic before firing (3D aware)."""
    r_km = distance_km(own_x, own_y, own_z, target_x, target_y, target_z)
    if r_km > missile_range_km:
        return 0.0
    
    # Range factor (higher chance at closer range)
    range_factor = max(0.0, 1.0 - (r_km / missile_range_km) ** 2)
    
    # Altitude factor: easier to hit targets below you (look-down/shoot-down)
    # or targets in thinner air (high altitude)
    dz = own_z - target_z
    alt_factor = 1.0 + 0.1 * (dz / 10.0) # +/- 10% based on 10km elevation diff
    alt_factor = max(0.8, min(1.2, alt_factor))
    
    return float(0.85 * range_factor * tracking_quality * alt_factor)
