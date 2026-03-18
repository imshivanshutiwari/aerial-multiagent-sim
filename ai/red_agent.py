"""Red force AI agent – BVR decision cycle with inferior parameters.

Same 5-step logic as Blue but:
  - Radar R_max = 120 km  (vs 150 for Blue)
  - Missile range = 80 km (vs 100)
  - Chaff success = 0.30   (vs 0.35)
  - NO formation logic (less disciplined opponent)
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional

import numpy as np

from engine.aircraft import Aircraft
from engine.missile import Missile
from engine.physics import compute_los_angles, distance_km
from engine.engagement_rules import estimated_pk
from ai.threat_assessment import ThreatEntry, assess_threats
from ai.utility_functions import (
    utility_close_to_range,
    utility_maintain_energy,
)
from ai.deconfliction import Deconfliction

# Red-specific constants (inferior)
_DECISION_PERIOD: float = 2.0
_OPTIMAL_RANGE_KM: float = 35.0
_MISSILE_RANGE_KM: float = 80.0
_PK_THRESHOLD: float = 0.40
_DEFENSIVE_RANGE_KM: float = 30.0
_CHAFF_RANGE_KM: float = 15.0
_CHAFF_SUCCESS_PROB: float = 0.30
_ENERGY_FLOOR_MS: float = 500.0


class RedAgent:
    """Rule/utility-based BVR controller for a Red aircraft.

    Identical to BlueAgent but with inferior parameters and no formation logic.
    """

    def __init__(self, aircraft: Aircraft) -> None:
        self.aircraft = aircraft
        self._clock: float = 0.0
        # Store approach heading for forward flight when no contacts
        self._approach_heading: float = aircraft.heading_deg
        # Override chaff probability for Red
        self.aircraft.ecm.chaff_success_probability = _CHAFF_SUCCESS_PROB

    def decide_and_act(
        self,
        t_sec: float,
        dt: float,
        all_aircraft: List[Aircraft],
        all_missiles: List[Missile],
        deconfliction: Deconfliction,
        rng: np.random.Generator,
        event_log: list,
    ) -> Optional[Missile]:
        """Run decision cycle. Returns a Missile if fired, else None."""
        if not self.aircraft.is_alive:
            return None

        self._clock += dt
        if self._clock < _DECISION_PERIOD:
            return None
        self._clock = 0.0

        own = self.aircraft
        enemies = [a for a in all_aircraft if a.team != own.team and a.is_alive]

        # --- Detect enemies via radar ---
        detected: List[Aircraft] = []
        enemy_tracking_me: Dict[str, bool] = {}
        for e in enemies:
            if own.radar.detect(
                own.x_km, own.y_km, own.z_km,
                e.x_km, e.y_km, e.z_km,
                e.get_rcs(own.x_km, own.y_km, own.z_km), e.ecm.jammer_active, rng,
            ):
                detected.append(e)
            enemy_tracking_me[e.aircraft_id] = (
                e.radar.is_active and
                e.radar.tracking_target_id == own.aircraft_id
            )

        # Step 1 — Threat assessment
        threats = assess_threats(own, detected, enemy_tracking_me)
        primary = threats[0] if threats else None

        # Step 2 — Missile defence
        incoming = [m for m in all_missiles
                    if m.is_active and m.target_id == own.aircraft_id
                    and m.phase == "terminal"]
        for m in incoming:
            m_range = distance_km(own.x_km, own.y_km, own.z_km, m.x_km, m.y_km, m.z_km)
            if m_range < _DEFENSIVE_RANGE_KM:
                los, _ = compute_los_angles(m.x_km, m.y_km, m.z_km, own.x_km, own.y_km, own.z_km)
                own.heading_deg = (los + 90.0) % 360.0
                own.defensive_manoeuvre_active = True
                if m_range < _CHAFF_RANGE_KM:
                    if own.ecm.dispense_chaff():
                        if own.ecm.chaff_success(rng):
                            m.lost_lock = True
                            event_log.append({
                                "t": t_sec, "actor": own.aircraft_id,
                                "team": own.team, "type": "CHAFF_SUCCESS",
                                "detail": f"Chaff broke lock of {m.missile_id}",
                            })
                event_log.append({
                    "t": t_sec, "actor": own.aircraft_id,
                    "team": own.team, "type": "DEFENSIVE_NOTCH",
                    "detail": f"Notching {m.missile_id} at {m_range:.1f} km",
                })
                return None

        own.defensive_manoeuvre_active = False

        # Step 3 — Engagement decision
        fired_missile: Optional[Missile] = None
        if primary is not None and own.missiles_remaining > 0:
            pri_ac = next((e for e in detected if e.aircraft_id == primary.target_id), None)
            if pri_ac is not None:
                tq = own.radar.track(
                    own.x_km, own.y_km, own.z_km,
                    pri_ac.x_km, pri_ac.y_km, pri_ac.z_km,
                    pri_ac.rcs, pri_ac.ecm.jammer_active,
                )
                pk_est = estimated_pk(
                    own.x_km, own.y_km, own.z_km,
                    pri_ac.x_km, pri_ac.y_km, pri_ac.z_km,
                    _MISSILE_RANGE_KM, tq
                )
                if (pk_est >= _PK_THRESHOLD
                        and primary.range_km <= _MISSILE_RANGE_KM
                        and not deconfliction.is_target_assigned(primary.target_id)):
                    fired_missile = own.fire_missile(pri_ac)
                    deconfliction.assign(own.aircraft_id, primary.target_id)
                    own.radar.tracking_target_id = primary.target_id
                    event_log.append({
                        "t": t_sec, "actor": own.aircraft_id,
                        "team": own.team, "type": "MISSILE_FIRE",
                        "detail": (f"Fired {fired_missile.missile_id} at "
                                   f"{primary.target_id} R={primary.range_km:.1f}km "
                                   f"PK_est={pk_est:.2f}"),
                    })

        # Step 4 — Positioning
        if primary is not None and fired_missile is None:
            pri_ac = next((e for e in detected if e.aircraft_id == primary.target_id), None)
            if pri_ac is not None:
                u_close = utility_close_to_range(primary.range_km, _OPTIMAL_RANGE_KM)
                los_to_target, _ = compute_los_angles(
                    own.x_km, own.y_km, own.z_km, pri_ac.x_km, pri_ac.y_km, pri_ac.z_km
                )
                if primary.range_km > _OPTIMAL_RANGE_KM:
                    h_close = los_to_target
                else:
                    h_close = (los_to_target + 180.0) % 360.0

                u_energy = utility_maintain_energy(own.velocity_ms, own.max_speed_ms)

                if u_energy > u_close:
                    pass  # keep current heading
                else:
                    own.heading_deg = h_close

                if own.velocity_ms < _ENERGY_FLOOR_MS:
                    own.velocity_ms = _ENERGY_FLOOR_MS
                
                # Altitude management: Red tries to stay at 8km (lower than Blue)
                target_alt = 8.0
                if own.z_km < target_alt - 0.5:
                    own.climb_rate_ms = 40.0
                elif own.z_km > target_alt + 0.5:
                    own.climb_rate_ms = -40.0
                else:
                    own.climb_rate_ms = 0.0
        elif primary is None:
            # No contacts: fly approach heading toward enemy territory
            own.heading_deg = self._approach_heading
            if own.velocity_ms < _ENERGY_FLOOR_MS:
                own.velocity_ms = _ENERGY_FLOOR_MS
            own.climb_rate_ms = 0.0

        # Step 5 — NO formation logic for Red (less disciplined)

        return fired_missile
