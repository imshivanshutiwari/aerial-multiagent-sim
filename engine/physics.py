"""Core physics functions for the BVR Combat Simulator.

All distances at scenario level are in **km**.
All distances at missile-guidance level are in **m**.
All angles at the interface level are in **degrees**; radians used internally.
All times in **seconds**.

Constants
---------
KM_TO_M : float
    1000.0 – explicit conversion, never implicit.
"""

from __future__ import annotations

import math
from typing import Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
KM_TO_M: float = 1000.0
M_TO_KM: float = 1.0 / KM_TO_M
G_ACCEL: float = 9.81  # m/s²


# ---------------------------------------------------------------------------
# Aircraft kinematics
# ---------------------------------------------------------------------------

def compute_turn_rate(velocity_ms: float, g_limit: float) -> float:
    """Maximum sustainable turn rate.

    Parameters
    ----------
    velocity_ms : float
        Aircraft speed in m/s.  Must be > 0.
    g_limit : float
        Maximum G-load the aircraft can sustain.

    Returns
    -------
    float
        Maximum turn rate in degrees per second.

    Notes
    -----
    Formula:  turn_rate = (g_limit * 9.81) / velocity_ms   (rad/s → deg/s)
    """
    if velocity_ms <= 0:
        return 0.0
    return math.degrees((g_limit * G_ACCEL) / velocity_ms)


def apply_heading_change(
    heading_deg: float,
    desired_heading_deg: float,
    max_turn_rate_deg_per_sec: float,
    dt: float,
) -> float:
    """Rotate heading toward *desired_heading_deg* by at most max_turn_rate*dt.

    Parameters
    ----------
    heading_deg : float
        Current heading in degrees.
    desired_heading_deg : float
        Target heading in degrees.
    max_turn_rate_deg_per_sec : float
        Maximum turn rate (deg/s).
    dt : float
        Time-step in seconds.

    Returns
    -------
    float
        New heading in [0, 360).
    """
    diff = (desired_heading_deg - heading_deg + 540.0) % 360.0 - 180.0
    max_delta = max_turn_rate_deg_per_sec * dt
    delta = max(-max_delta, min(max_delta, diff))
    return (heading_deg + delta) % 360.0


def update_position(
    x_km: float, y_km: float, z_km: float, 
    heading_deg: float, velocity_ms: float, climb_rate_ms: float, dt: float
) -> Tuple[float, float, float]:
    """Advance 3D position by one time-step.

    Parameters
    ----------
    x_km, y_km, z_km : float
        Current position in km (z is altitude).
    heading_deg : float
        Heading in degrees (0 = +x, 90 = +y).
    velocity_ms : float
        Total speed in m/s.
    climb_rate_ms : float
        Vertical speed in m/s (Positive = climb).
    dt : float
        Time-step in seconds.

    Returns
    -------
    Tuple[float, float, float]
        New (x_km, y_km, z_km).
    """
    h = math.radians(heading_deg)
    # Horizontal speed (ground speed)
    horiz_speed = math.sqrt(max(0.0, velocity_ms**2 - climb_rate_ms**2))
    dx_m = horiz_speed * math.cos(h) * dt
    dy_m = horiz_speed * math.sin(h) * dt
    dz_m = climb_rate_ms * dt
    return x_km + dx_m * M_TO_KM, y_km + dy_m * M_TO_KM, z_km + dz_m * M_TO_KM


# ---------------------------------------------------------------------------
# Line-of-sight geometry
# ---------------------------------------------------------------------------

def compute_los_angles(x1: float, y1: float, z1: float, x2: float, y2: float, z2: float) -> Tuple[float, float]:
    """3D Line-of-sight angles (Azimuth and Elevation) from point 1 to point 2.

    Returns
    -------
    Tuple[float, float]
        (Azimuth deg [0, 360), Elevation deg [-90, 90]).
    """
    dx, dy, dz = x2 - x1, y2 - y1, z2 - z1
    dist_2d = math.sqrt(dx**2 + dy**2)
    az = math.degrees(math.atan2(dy, dx)) % 360.0
    el = math.degrees(math.atan2(dz, dist_2d))
    return az, el


def compute_los_rate(
    x1: float, y1: float, z1: float, vx1: float, vy1: float, vz1: float,
    x2: float, y2: float, z2: float, vx2: float, vy2: float, vz2: float,
) -> float:
    """Rate of change of the LOS angle in 3D (simplified to angular magnitude)."""
    dx, dy, dz = x2 - x1, y2 - y1, z2 - z1
    r_sq = dx**2 + dy**2 + dz**2
    if r_sq < 1.0: return 0.0
    
    # Relative velocity
    dvx, dvy, dvz = vx2 - vx1, vy2 - vy1, vz2 - vz1
    
    # Cross product [r x v] / r²
    # Magnitude of angular velocity vector
    wx = (dy * dvz - dz * dvy) / r_sq
    wy = (dz * dvx - dx * dvz) / r_sq
    wz = (dx * dvy - dy * dvx) / r_sq
    return math.sqrt(wx**2 + wy**2 + wz**2)


def compute_closing_rate(
    x1: float, y1: float, z1: float,
    vx1: float, vy1: float, vz1: float,
    x2: float, y2: float, z2: float,
    vx2: float, vy2: float, vz2: float,
) -> float:
    """Closing speed between two entities in 3D.

    Parameters
    ----------
    Same as :func:`compute_los_rate`.

    Returns
    -------
    float
        Closing speed in m/s.  Positive = closing, negative = opening.
    """
    dx, dy, dz = x2 - x1, y2 - y1, z2 - z1
    r = math.sqrt(dx**2 + dy**2 + dz**2)
    if r < 1.0:
        return 0.0
    
    # Relative velocity of 2 w.r.t. 1
    dvx, dvy, dvz = vx2 - vx1, vy2 - vy1, vz2 - vz1
    
    # Closing rate is - (d/dt distance)
    return -(dx * dvx + dy * dvy + dz * dvz) / r


def compute_intercept_point_3d(
    tx: float, ty: float, tz: float,
    tvx: float, tvy: float, tvz: float,
    mx: float, my: float, mz: float,
    v_missile: float,
    max_iters: int = 15
) -> Tuple[float, float, float]:
    """3D predicted intercept point prediction."""
    dx, dy, dz = tx - mx, ty - my, tz - mz
    r = math.sqrt(dx**2 + dy**2 + dz**2)
    if v_missile <= 0: return tx, ty, tz
    t_est = r / v_missile
    
    for _ in range(max_iters):
        px, py, pz = tx + tvx * t_est, ty + tvy * t_est, tz + tvz * t_est
        dx, dy, dz = px - mx, py - my, pz - mz
        r = math.sqrt(dx**2 + dy**2 + dz**2)
        if r < 1.0: return px, py, pz
        t_est = r / v_missile
        
    return tx + tvx * t_est, ty + tvy * t_est, tz + tvz * t_est


def distance_km(x1: float, y1: float, z1: float, x2: float, y2: float, z2: float) -> float:
    """3D Euclidean distance in km."""
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2 + (z2 - z1)**2)


def distance_m(x1: float, y1: float, z1: float, x2: float, y2: float, z2: float) -> float:
    """3D Euclidean distance in metres."""
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2 + (z2 - z1)**2)
