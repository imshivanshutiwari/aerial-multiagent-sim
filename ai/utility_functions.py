"""Utility functions used by Blue and Red AI agents.

All utilities return a value in [0, 1].
"""

from __future__ import annotations

import math


def utility_close_to_range(current_range_km: float, optimal_range_km: float) -> float:
    """Utility for maintaining optimal firing range.

    Returns
    -------
    float
        0-1. Higher when closer to optimal range.
    """
    if optimal_range_km <= 0:
        return 0.0
    diff = abs(current_range_km - optimal_range_km)
    # 1.0 at optimal range, tapering down to 0 at optimal_range_km distance
    return max(0.0, 1.0 - (diff / optimal_range_km))


def utility_support_wingman(
    own_x: float, own_y: float, own_z: float,
    wingman_x: float, wingman_y: float, wingman_z: float,
    threat_x: float, threat_y: float, threat_z: float,
) -> float:
    """Utility for moving to support a threatened wingman.

    Higher when the wingman is close to the threat and own position is far
    from the wingman.

    Returns
    -------
    float
        0–1.
    """
    dx = wingman_x - threat_x
    dy = wingman_y - threat_y
    dz = wingman_z - threat_z
    wingman_threat_dist = math.sqrt(dx * dx + dy * dy + dz * dz)

    dx2 = own_x - wingman_x
    dy2 = own_y - wingman_y
    dz2 = own_z - wingman_z
    own_wingman_dist = math.sqrt(dx2 * dx2 + dy2 * dy2 + dz2 * dz2)

    # High utility when wingman is close to threat and we're far
    if wingman_threat_dist < 1.0:
        wingman_threat_dist = 1.0
    urgency = 1.0 / (1.0 + wingman_threat_dist / 50.0)
    distance_factor = min(1.0, own_wingman_dist / 30.0)
    return urgency * distance_factor


def utility_maintain_energy(own_velocity_ms: float, max_velocity_ms: float) -> float:
    """Utility for maintaining kinetic energy (speed).

    Returns
    -------
    float
        0–1. Higher when speed is low relative to max.
    """
    if max_velocity_ms <= 0:
        return 0.0
    ratio = own_velocity_ms / max_velocity_ms
    return max(0.0, 1.0 - ratio)


def estimated_pk(range_km: float, missile_range_km: float, tracking_quality: float) -> float:
    """Quick estimated probability-of-kill for engagement decision.

    Parameters
    ----------
    range_km : float
        Range to target in km.
    missile_range_km : float
        Max missile range in km.
    tracking_quality : float
        0–1 radar tracking quality.

    Returns
    -------
    float
        Estimated PK [0, 1].
    """
    if range_km > missile_range_km:
        return 0.0
    range_factor = max(0.0, 1.0 - (range_km / missile_range_km) ** 2)
    return 0.85 * range_factor * tracking_quality
