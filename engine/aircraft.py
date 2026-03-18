"""Aircraft model for BVR Combat Simulation.

Each aircraft carries:
- A Radar instance
- An ECMSystem instance
- 4 active radar homing missiles
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

from engine.ecm import ECMSystem
from engine.missile import Missile
from engine.physics import (
    KM_TO_M,
    apply_heading_change,
    compute_turn_rate,
    distance_km,
    update_position,
)
from engine.radar import Radar


_MISSILE_COUNTER = 0


def _next_missile_id(owner_id: str) -> str:
    global _MISSILE_COUNTER
    _MISSILE_COUNTER += 1
    return f"M-{owner_id}-{_MISSILE_COUNTER}"


@dataclass
class Aircraft:
    """A fighter aircraft in the BVR simulation.

    Parameters
    ----------
    aircraft_id : str
        Unique identifier (e.g. "Blue-1").
    team : str
        "Blue" or "Red".
    x_km, y_km : float
        Initial position in km.
    velocity_ms : float
        Initial speed in m/s.
    heading_deg : float
        Initial heading (0 = +x, 90 = +y).
    g_limit : float
        Max sustained G.
    max_speed_ms : float
        Maximum speed in m/s.
    radar : Radar
        Radar sensor.
    ecm : ECMSystem
        ECM suite.
    missiles_remaining : int
        Number of missiles available (initially 4).
    rcs : float
        Radar cross-section in m².
    wingman_id : str | None
        ID of the paired wingman, if any.
    """

    aircraft_id: str
    team: str
    x_km: float
    y_km: float
    z_km: float = 10.0  # Default altitude: 10km
    velocity_ms: float = 550.0
    heading_deg: float = 90.0
    g_limit: float = 9.0
    max_speed_ms: float = 600.0
    radar: Radar = field(default_factory=lambda: Radar(r_max_km=150.0))
    ecm: ECMSystem = field(default_factory=ECMSystem)
    missiles_remaining: int = 4
    rcs: float = 3.0
    wingman_id: Optional[str] = None
    climb_rate_ms: float = 0.0
    rwr_status: str = "OFF"  # SEARCH, LOCK, MISSILE, OFF

    # runtime state
    is_alive: bool = field(default=True, init=False)
    kill_count: int = field(default=0, init=False)
    defensive_manoeuvre_active: bool = field(default=False, init=False)

    # ------------------------------------------------------------------
    def update(self, dt: float) -> None:
        """Update position and ECM energy for one time-step."""
        if not self.is_alive:
            return
        self.x_km, self.y_km, self.z_km = update_position(
            self.x_km, self.y_km, self.z_km, self.heading_deg, self.velocity_ms, self.climb_rate_ms, dt
        )
        self.ecm.update(dt)

    def fire_missile(self, target: "Aircraft") -> Missile:
        """Fire one missile at *target*.

        Returns
        -------
        Missile
            The newly launched missile.

        Raises
        ------
        RuntimeError
            If no missiles remain.
        """
        if self.missiles_remaining <= 0:
            raise RuntimeError(f"{self.aircraft_id} has no missiles remaining")
        self.missiles_remaining -= 1
        m = Missile(
            missile_id=_next_missile_id(self.aircraft_id),
            owner_id=self.aircraft_id,
            target_id=target.aircraft_id,
            x_km=self.x_km,
            y_km=self.y_km,
            z_km=self.z_km,
            velocity_ms=self.velocity_ms,
            heading_deg=self.heading_deg,
        )
        return m

    def get_velocity_components(self) -> Tuple[float, float, float]:
        """Return (vx, vy, vz) in m/s."""
        h = math.radians(self.heading_deg)
        horiz_speed = math.sqrt(max(0.0, self.velocity_ms**2 - self.climb_rate_ms**2))
        return horiz_speed * math.cos(h), horiz_speed * math.sin(h), self.climb_rate_ms

    def get_rcs(self, sensor_x: float, sensor_y: float, sensor_z: float) -> float:
        """Calculate aspect-dependent RCS.
        
        Parameters
        ----------
        sensor_x, sensor_y, sensor_z : float
            Position of the radar/missile sensor in km.
            
        Returns
        -------
        float
            Effective RCS in m².
        """
        # Vector from self to sensor
        dx, dy, dz = sensor_x - self.x_km, sensor_y - self.y_km, sensor_z - self.z_km
        dist = math.sqrt(dx**2 + dy**2 + dz**2)
        if dist < 0.01: return self.rcs
        
        # Unit vector TO sensor
        ux, uy, uz = dx/dist, dy/dist, dz/dist
        
        # Aircraft heading vector (horizontal part)
        h_rad = math.radians(self.heading_deg)
        ax, ay = math.cos(h_rad), math.sin(h_rad)
        
        # Aspect angle in horizontal plane (Dot product)
        # dot_h near 1.0 = sensor is in front (Nose on)
        # dot_h near -1.0 = sensor is behind (Tail on)
        # dot_h near 0.0 = sensor is to the side (Beam)
        dot_h = ux * ax + uy * ay
        
        # Vertical aspect (elevation)
        # uz near 1.0 = sensor is directly above
        # uz near -1.0 = sensor is directly below
        abs_uz = abs(uz)
        
        # Horizontal RCS component
        # Multipliers: Nose(0.1), Tail(0.8), Side(2.5)
        h_rcs = self.rcs * (
            0.1 * max(0.0, dot_h) +      # Nose sector
            0.8 * max(0.0, -dot_h) +     # Tail sector
            2.5 * (1.0 - abs(dot_h))   # Side sector
        )
        
        # Blend with vertical aspect (Top/Bottom, assume 2.0x base RCS)
        effective_rcs = h_rcs * (1.0 - abs_uz) + (self.rcs * 2.0) * abs_uz
        
        return max(0.01, effective_rcs)

    def get_state_dict(self) -> Dict:
        """Serialisable state snapshot."""
        return {
            "aircraft_id": self.aircraft_id,
            "team": self.team,
            "x_km": self.x_km,
            "y_km": self.y_km,
            "z_km": self.z_km,
            "velocity_ms": self.velocity_ms,
            "heading_deg": self.heading_deg,
            "climb_rate": self.climb_rate_ms,
            "is_alive": self.is_alive,
            "missiles_remaining": self.missiles_remaining,
            "kill_count": self.kill_count,
            "defensive": self.defensive_manoeuvre_active,
            "jammer_active": self.ecm.jammer_active,
            "jammer_energy": self.ecm.jammer_energy_remaining_sec,
            "chaff_count": self.ecm.chaff_count,
            "radar_active": self.radar.is_active,
            "radar_rmax_km": self.radar.r_max_km,
            "rcs": self.rcs,
            "rwr": self.rwr_status,
            "wingman_id": self.wingman_id,
        }
