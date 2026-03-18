"""Blue force AI agent – full 5-step BVR decision cycle.

Decision cycle (every 2 simulated seconds):
  1. Threat assessment
  2. Missile defence check (notch + chaff if incoming terminal missile <40 km)
  3. Engagement decision (fire if PK > 0.55, deconflicted)
  4. Positioning (utility-based: close-to-range, maintain-energy, support-wingman)
  5. Formation check (pair-based 15 km lateral separation)

Blue parameters:
  - Radar R_max = 150 km
  - Missile range = 100 km
  - Chaff success = 0.35
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional

import numpy as np

from engine.aircraft import Aircraft
from engine.missile import Missile
from engine.physics import (
    apply_heading_change,
    compute_los_angles,
    compute_turn_rate,
    distance_km,
)
from engine.engagement_rules import estimated_pk
from ai.threat_assessment import ThreatEntry, assess_threats
from ai.utility_functions import (
    utility_close_to_range,
    utility_maintain_energy,
    utility_support_wingman,
)
from ai.deconfliction import Deconfliction


# Blue-specific constants
_DECISION_PERIOD: float = 2.0
_OPTIMAL_RANGE_KM: float = 45.0
_MISSILE_RANGE_KM: float = 100.0
_PK_THRESHOLD: float = 0.40
_DEFENSIVE_RANGE_KM: float = 30.0
_CHAFF_RANGE_KM: float = 15.0
_FORMATION_SEP_KM: float = 15.0
_FORMATION_MAX_KM: float = 30.0
_ENERGY_FLOOR_MS: float = 500.0


class BlueAgent:
    """Rule/utility-based BVR controller for a Blue aircraft."""

    def __init__(self, aircraft: Aircraft) -> None:
        self.aircraft = aircraft
        self._clock: float = 0.0
        # Store the initial heading as the default combat approach heading
        self._approach_heading: float = aircraft.heading_deg
        self._is_rejoining: bool = False

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
        """Run the 5-step BVR decision cycle.

        Returns a new Missile if one is fired, else None.
        """
        if not self.aircraft.is_alive:
            return None

        self._clock += dt
        if self._clock < _DECISION_PERIOD:
            return None
        self._clock = 0.0

        own = self.aircraft
        enemies = [a for a in all_aircraft if a.team != own.team and a.is_alive]
        friendlies = [a for a in all_aircraft if a.team == own.team and a.is_alive
                      and a.aircraft_id != own.aircraft_id]

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
            # Check if enemy's radar is tracking us
            enemy_tracking_me[e.aircraft_id] = (
                e.radar.is_active and
                e.radar.tracking_target_id == own.aircraft_id
            )

        # =========================================================
        # STEP 1 — Threat assessment
        # =========================================================
        threats = assess_threats(own, detected, enemy_tracking_me)
        primary = threats[0] if threats else None

        # =========================================================
        # STEP 2 — Missile defence check
        # =========================================================
        incoming = [m for m in all_missiles
                    if m.is_active and m.target_id == own.aircraft_id
                    and m.phase == "terminal"]
        for m in incoming:
            m_range = distance_km(own.x_km, own.y_km, own.z_km, m.x_km, m.y_km, m.z_km)
            if m_range < _DEFENSIVE_RANGE_KM:
                los, _ = compute_los_angles(m.x_km, m.y_km, m.z_km, own.x_km, own.y_km, own.z_km)
                own.heading_deg = (los + 90.0) % 360.0
                own.defensive_manoeuvre_active = True

                # Dispense chaff if within 15 km
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
                return None  # Step 2 overrides all other decisions

        own.defensive_manoeuvre_active = False

        # =========================================================
        # STEP 3 — Engagement decision
        # =========================================================
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

        # =========================================================
        # STEP 4 — Positioning (utility-based)
        # =========================================================
        if primary is not None and fired_missile is None:
            pri_ac = next((e for e in detected if e.aircraft_id == primary.target_id), None)
            if pri_ac is not None:
                # a) Close to optimal range
                u_close = utility_close_to_range(primary.range_km, _OPTIMAL_RANGE_KM)
                los_to_target, _ = compute_los_angles(
                    own.x_km, own.y_km, own.z_km, pri_ac.x_km, pri_ac.y_km, pri_ac.z_km
                )
                if primary.range_km > _OPTIMAL_RANGE_KM:
                    h_close = los_to_target
                else:
                    h_close = (los_to_target + 180.0) % 360.0

                # b) Maintain energy
                u_energy = utility_maintain_energy(own.velocity_ms, own.max_speed_ms)

                # c) Support wingman
                u_support = 0.0
                h_support = own.heading_deg
                if own.wingman_id:
                    wingman = next((f for f in friendlies
                                    if f.aircraft_id == own.wingman_id), None)
                    if wingman:
                        u_support = utility_support_wingman(
                            own.x_km, own.y_km, own.z_km,
                            wingman.x_km, wingman.y_km, wingman.z_km,
                            pri_ac.x_km, pri_ac.y_km, pri_ac.z_km,
                        )
                        h_support, _ = compute_los_angles(
                            own.x_km, own.y_km, own.z_km, wingman.x_km, wingman.y_km, wingman.z_km
                        )

                # Pick highest utility
                best_u = u_close
                best_h = h_close
                if u_energy > best_u:
                    best_u = u_energy
                    best_h = own.heading_deg
                if u_support > best_u:
                    best_u = u_support
                    best_h = h_support

                own.heading_deg = best_h
                if own.velocity_ms < _ENERGY_FLOOR_MS:
                    own.velocity_ms = _ENERGY_FLOOR_MS
                    
                # Altitude management: Try to maintain 10km for optimal sensor coverage
                target_alt = 10.0
                if own.z_km < target_alt - 0.5:
                    own.climb_rate_ms = 50.0  # Climb
                elif own.z_km > target_alt + 0.5:
                    own.climb_rate_ms = -50.0 # Descend
                else:
                    own.climb_rate_ms = 0.0
        elif primary is None:
            # No contacts: fly approach heading toward enemy territory
            own.heading_deg = self._approach_heading
            if own.velocity_ms < _ENERGY_FLOOR_MS:
                own.velocity_ms = _ENERGY_FLOOR_MS
            own.climb_rate_ms = 0.0

        # =========================================================
        # STEP 5 — Formation check (Blue flies in pairs)
        # Only adjust heading slightly if separation is excessive,
        # but do NOT override approach heading when far from enemies
        # =========================================================
        if own.wingman_id and primary is not None:
            wingman = next((f for f in friendlies
                            if f.aircraft_id == own.wingman_id), None)
            if wingman:
                sep = distance_km(own.x_km, own.y_km, own.z_km, wingman.x_km, wingman.y_km, wingman.z_km)
                
                # Hysteresis: Start rejoining at _FORMATION_MAX_KM, Stop at _FORMATION_SEP_KM
                if self._is_rejoining:
                    if sep < _FORMATION_SEP_KM:
                        self._is_rejoining = False
                else:
                    if sep > _FORMATION_MAX_KM:
                        self._is_rejoining = True
                        event_log.append({
                            "t": t_sec, "actor": own.aircraft_id,
                            "team": own.team, "type": "FORMATION_REJOIN",
                            "detail": f"Separation {sep:.1f}km > {_FORMATION_MAX_KM}km, rejoining wingman",
                        })

                if self._is_rejoining:
                    # Blend toward wingman instead of hard override
                    wm_heading, _ = compute_los_angles(
                        own.x_km, own.y_km, own.z_km, wingman.x_km, wingman.y_km, wingman.z_km
                    )
                    own.heading_deg = wm_heading

        return fired_missile
