"""Active Radar Homing Missile with Proportional Navigation guidance.

Phases
------
1. **Boost** (0–3 s): constant acceleration 30 m/s², fly toward predicted
   intercept point.
2. **Midcourse** (3–30 s): inertial guidance toward updated intercept point,
   constant speed.
3. **Terminal** (>30 s): active seeker on, proportional navigation.
   a_cmd = N * V_c * dθ/dt   with N = 4.

Missile max speed 1 200 m/s.  Range ≈ 100 km.  Fuel duration 40 s.
If fuel runs out the missile goes ballistic (no guidance) and is deactivated
once it can no longer close on any target.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Tuple

from engine.physics import (
    KM_TO_M,
    M_TO_KM,
    compute_closing_rate,
    compute_intercept_point_3d,
    compute_los_angles,
    compute_los_rate,
    distance_m,
    update_position,
)

_PN_N: float = 4.0  # proportional navigation constant
_BOOST_DURATION: float = 3.0  # seconds
_TERMINAL_ONSET: float = 15.0  # seconds after launch (turn on seeker sooner)
_BOOST_ACCEL: float = 200.0  # m/s² (reach Mach 4 quickly)
_MAX_SPEED: float = 1200.0  # m/s
_FUEL_DURATION: float = 80.0  # seconds
_KILL_DIRECT_RANGE_M: float = 30.0
_KILL_PROX_RANGE_M: float = 100.0
_PK_DIRECT: float = 0.85


@dataclass
class Missile:
    """An active-radar homing missile in flight.

    Parameters
    ----------
    missile_id : str
        Unique ID.
    owner_id : str
        Aircraft that fired this missile.
    target_id : str
        Intended target aircraft ID.
    x_km, y_km : float
        Launch position in km.
    velocity_ms : float
        Initial speed (typically equal to launch aircraft speed).
    heading_deg : float
        Initial heading (degrees).
    """

    missile_id: str
    owner_id: str
    target_id: str
    x_km: float
    y_km: float
    z_km: float
    velocity_ms: float
    heading_deg: float
    climb_rate_ms: float = 0.0

    # internal state
    fuel_remaining_sec: float = field(default=_FUEL_DURATION, init=False)
    time_since_launch: float = field(default=0.0, init=False)
    seeker_active: bool = field(default=False, init=False)
    is_active: bool = field(default=True, init=False)
    phase: str = field(default="boost", init=False)
    miss_distance_at_closest: float = field(default=1e9, init=False)
    lost_lock: bool = field(default=False, init=False)

    # trail history for visualisation (screen coords added externally)
    trail_positions: list = field(default_factory=list, init=False, repr=False)

    # ------------------------------------------------------------------
    # Phase logic
    # ------------------------------------------------------------------
    def _update_phase(self) -> None:
        t = self.time_since_launch
        if t < _BOOST_DURATION:
            self.phase = "boost"
            self.seeker_active = False
        elif t < _TERMINAL_ONSET:
            self.phase = "midcourse"
            self.seeker_active = False
        else:
            self.phase = "terminal"
            self.seeker_active = True

    # ------------------------------------------------------------------
    # Main update
    # ------------------------------------------------------------------
    def update(
        self,
        dt: float,
        target_x_km: float,
        target_y_km: float,
        target_z_km: float,
        target_vx_ms: float,
        target_vy_ms: float,
        target_vz_ms: float,
        target_rcs: float,
    ) -> None:
        """Advance missile state by *dt* seconds.

        Parameters
        ----------
        dt : float
            Time step (s).
        target_x_km, target_y_km, target_z_km: float
            Target position in km.
        target_vx_ms, target_vy_ms, target_vz_ms : float
            Target velocity components in m/s.
        target_rcs : float
            Aspect-dependent Radar Cross Section of target.
        """
        if not self.is_active:
            return

        self.time_since_launch += dt
        self._update_phase()

        # Fuel check
        self.fuel_remaining_sec -= dt
        if self.fuel_remaining_sec <= 0:
            self.fuel_remaining_sec = 0.0
            self.is_active = False
            return

        # If lock was broken by chaff, fly straight (no guidance)
        if self.lost_lock:
            self.x_km, self.y_km, self.z_km = update_position(
                self.x_km, self.y_km, self.z_km, self.heading_deg, self.velocity_ms, self.climb_rate_ms, dt
            )
            self._record_miss_distance(target_x_km, target_y_km, target_z_km)
            return

        # Convert to metres for guidance
        mx = self.x_km * KM_TO_M
        my = self.y_km * KM_TO_M
        mz = self.z_km * KM_TO_M
        tx = target_x_km * KM_TO_M
        ty = target_y_km * KM_TO_M
        tz = target_z_km * KM_TO_M
        m_vx, m_vy, m_vz = self.get_velocity_components()

        if self.phase == "boost":
            # Accelerate toward predicted intercept point
            self.velocity_ms = min(_MAX_SPEED, self.velocity_ms + _BOOST_ACCEL * dt)
            ix, iy, iz = compute_intercept_point_3d(
                tx, ty, tz, target_vx_ms, target_vy_ms, target_vz_ms,
                mx, my, mz, self.velocity_ms,
            )
            self.heading_deg, el = compute_los_angles(mx, my, mz, ix, iy, iz)
            # Simple vertical guidance: climb_rate = V * sin(elevation)
            self.climb_rate_ms = self.velocity_ms * math.sin(math.radians(el))

        # Maintain speed, fly toward updated intercept point
        elif self.phase == "midcourse":
            ix, iy, iz = compute_intercept_point_3d(
                tx, ty, tz, target_vx_ms, target_vy_ms, target_vz_ms,
                mx, my, mz, self.velocity_ms,
            )
            self.heading_deg, el = compute_los_angles(mx, my, mz, ix, iy, iz)
            self.climb_rate_ms = self.velocity_ms * math.sin(math.radians(el))

        elif self.phase == "terminal":
            # Proportional Navigation guidance in 3D (simplified to angular rate cross)
            # In 3D we would use vector PN, but let's stick to LOS rate magnitude for a_cmd
            # and resolve it into horizontal and vertical components.
            los_rate = compute_los_rate(
                mx, my, mz, m_vx, m_vy, m_vz, tx, ty, tz, target_vx_ms, target_vy_ms, target_vz_ms
            )
            closing = compute_closing_rate(
                mx, my, mz, m_vx, m_vy, m_vz, tx, ty, tz, target_vx_ms, target_vy_ms, target_vz_ms
            )
            # Actually closing rate 2D is mostly fine for speed check, but let's fix it later.
            a_cmd = _PN_N * closing * los_rate
            
            # Resolve a_cmd into change of velocity vector direction
            if self.velocity_ms > 0:
                # Direct missile velocity toward target (simplified)
                # In terminal, we'll just track LOS angles directly with lower lag
                t_az, t_el = compute_los_angles(mx, my, mz, tx, ty, tz)
                self.heading_deg = t_az # Simplified Terminal
                self.climb_rate_ms = self.velocity_ms * math.sin(math.radians(t_el))

        # Integrate position
        self.x_km, self.y_km, self.z_km = update_position(
            self.x_km, self.y_km, self.z_km, self.heading_deg, self.velocity_ms, self.climb_rate_ms, dt
        )

        # Track closest approach
        self._record_miss_distance(target_x_km, target_y_km, target_z_km)

    # ------------------------------------------------------------------
    # Kill check
    # ------------------------------------------------------------------
    def check_proximity_kill(
        self,
        target_x_km: float,
        target_y_km: float,
        target_z_km: float,
        target_vx_ms: float,
        target_vy_ms: float,
        target_vz_ms: float,
        dt: float,
        rng,
    ) -> Tuple[bool, float]:
        """Check if the missile scores a kill using continuous CPA.

        Parameters
        ----------
        target_x_km, target_y_km, target_z_km : float
            Target position at END of tick in km.
        target_vx_ms, target_vy_ms, target_vz_ms : float
            Target velocity in m/s.
        dt : float
            Time step.
        rng : numpy Generator

        Returns
        -------
        Tuple[bool, float]
            (is_kill, miss_distance_m).
        """
        # Missile position at end of tick
        mx_m = self.x_km * KM_TO_M
        my_m = self.y_km * KM_TO_M
        mz_m = self.z_km * KM_TO_M
        tx_m = target_x_km * KM_TO_M
        ty_m = target_y_km * KM_TO_M
        tz_m = target_z_km * KM_TO_M

        m_vx, m_vy, m_vz = self.get_velocity_components()
        
        # Relative velocity
        dvx = m_vx - target_vx_ms
        dvy = m_vy - target_vy_ms
        dvz = m_vz - target_vz_ms
        v_rel_sq = dvx**2 + dvy**2 + dvz**2

        # Relative position at the END of the tick
        dx = mx_m - tx_m
        dy = my_m - ty_m
        dz = mz_m - tz_m
        
        # Closest Point of Approach (CPA) during the LAST dt seconds
        if v_rel_sq > 0.001:
            t_cpa = -(dx * dvx + dy * dvy + dz * dvz) / v_rel_sq
            t_cpa = max(-dt, min(0.0, t_cpa))
        else:
            t_cpa = 0.0

        miss_m = math.sqrt((dx + dvx * t_cpa)**2 + (dy + dvy * t_cpa)**2 + (dz + dvz * t_cpa)**2)

        if miss_m > _KILL_PROX_RANGE_M:
            return False, miss_m

        # Within prox range – missile detonates
        self.is_active = False
        if miss_m <= _KILL_DIRECT_RANGE_M:
            pk = _PK_DIRECT
        else:
            pk = _PK_DIRECT * math.exp(-(miss_m - _KILL_DIRECT_RANGE_M) / 20.0)

        return bool(rng.random() < pk), miss_m

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def get_velocity_components(self) -> Tuple[float, float, float]:
        h = math.radians(self.heading_deg)
        horiz_speed = math.sqrt(max(0.0, self.velocity_ms**2 - self.climb_rate_ms**2))
        return (
            horiz_speed * math.cos(h),
            horiz_speed * math.sin(h),
            self.climb_rate_ms
        )

    def _record_miss_distance(self, tx_km: float, ty_km: float, tz_km: float) -> None:
        d = distance_m(
            self.x_km * KM_TO_M, self.y_km * KM_TO_M, self.z_km * KM_TO_M,
            tx_km * KM_TO_M, ty_km * KM_TO_M, tz_km * KM_TO_M,
        )
        if d < self.miss_distance_at_closest:
            self.miss_distance_at_closest = d

    def get_state_dict(self) -> dict:
        return {
            "missile_id": self.missile_id,
            "owner_id": self.owner_id,
            "target_id": self.target_id,
            "x_km": self.x_km,
            "y_km": self.y_km,
            "velocity_ms": self.velocity_ms,
            "heading_deg": self.heading_deg,
            "phase": self.phase,
            "fuel_sec": self.fuel_remaining_sec,
            "seeker_active": self.seeker_active,
            "is_active": self.is_active,
        }
