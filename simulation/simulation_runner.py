"""Simulation runner — main loop with dt=0.5 s.

Each iteration:
1. Update all missiles (guidance + kinematics)
2. Check for kills (proximity)
3. Run all agent decision cycles
4. Update all aircraft positions
5. Log events, record state snapshots every 5 s

Stops when: all Red dead, all Blue dead, time limit, or all missiles expended
and no missiles in flight.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np

from engine.aircraft import Aircraft
from engine.missile import Missile
from engine.physics import distance_km
from ai.blue_agent import BlueAgent
from ai.red_agent import RedAgent
from ai.deconfliction import Deconfliction
from simulation.scenario import Scenario


@dataclass
class SimulationResult:
    """Result container."""
    scenario_name: str
    blue_kills: int
    red_kills: int
    blue_losses: int
    red_losses: int
    kill_ratio: float
    duration_sec: float
    missiles_fired_blue: int
    missiles_fired_red: int
    event_log: List[Dict]
    state_history: List[Dict]


class SimulationRunner:
    """Run a single BVR engagement scenario.

    Parameters
    ----------
    dt : float
        Time step in seconds (default 0.5).
    history_period : float
        Record state snapshot every *history_period* seconds (default 5).
    """

    def __init__(self, dt: float = 0.5, history_period: float = 5.0) -> None:
        self.dt = dt
        self.history_period = history_period

    def run(self, scenario: Scenario, random_seed: int = 42) -> SimulationResult:
        rng = np.random.default_rng(random_seed)

        all_aircraft = scenario.all_aircraft()
        blue_agents = scenario.blue_agents
        red_agents = scenario.red_agents

        blue_decon = Deconfliction()
        red_decon = Deconfliction()

        missiles_in_flight: List[Missile] = []
        event_log: List[Dict] = []
        state_history: List[Dict] = []

        missiles_fired_blue = 0
        missiles_fired_red = 0

        t = 0.0
        last_snapshot = -self.history_period
        time_limit = scenario.time_limit_sec

        while t < time_limit:
            # ---- 1. Update missiles ----
            for m in missiles_in_flight:
                if not m.is_active:
                    continue
                target = next((a for a in all_aircraft
                               if a.aircraft_id == m.target_id), None)
                if target is None or not target.is_alive:
                    m.is_active = False
                    continue
                tvx, tvy, tvz = target.get_velocity_components()
                trcs = target.get_rcs(m.x_km, m.y_km, m.z_km)
                m.update(self.dt, target.x_km, target.y_km, target.z_km, tvx, tvy, tvz, trcs)

            # ---- 2. Check kills ----
            for m in missiles_in_flight:
                if not m.is_active:
                    continue
                target = next((a for a in all_aircraft
                               if a.aircraft_id == m.target_id), None)
                if target is None or not target.is_alive:
                    m.is_active = False
                    continue
                tvx, tvy, tvz = target.get_velocity_components()
                is_kill, miss_dist = m.check_proximity_kill(
                    target.x_km, target.y_km, target.z_km, tvx, tvy, tvz, self.dt, rng
                )
                if not m.is_active:  # Detonated (either hit or miss within _KILL_PROX_RANGE_M)
                    # Missile detonated
                    owner = next((a for a in all_aircraft
                                  if a.aircraft_id == m.owner_id), None)
                    if is_kill:
                        target.is_alive = False
                        if owner:
                            owner.kill_count += 1
                        # Release deconfliction
                        blue_decon.release(target.aircraft_id)
                        red_decon.release(target.aircraft_id)
                        event_log.append({
                            "t": t, "actor": m.owner_id,
                            "team": owner.team if owner else "?",
                            "type": "KILL",
                            "detail": f"{m.missile_id} killed {target.aircraft_id} "
                                      f"(miss={miss_dist:.1f}m)",
                            "target": target.aircraft_id,
                            "miss_m": miss_dist,
                        })
                    else:
                        blue_decon.release(target.aircraft_id)
                        red_decon.release(target.aircraft_id)
                        event_log.append({
                            "t": t, "actor": m.owner_id,
                            "team": owner.team if owner else "?",
                            "type": "MISSILE_MISS",
                            "detail": f"{m.missile_id} missed {target.aircraft_id} "
                                      f"(miss={miss_dist:.1f}m)",
                            "target": target.aircraft_id,
                            "miss_m": miss_dist,
                        })

            # Prune dead missiles
            missiles_in_flight = [m for m in missiles_in_flight if m.is_active]

            # ---- 2.5 Update RWR (Radar Warning Receiver) status ----
            for a in all_aircraft:
                if not a.is_alive: continue
                # Reset RWR
                a.rwr_status = "OFF"
                
                # Check for active missiles in terminal phase targeting this aircraft
                m_incoming = [m for m in missiles_in_flight 
                             if m.is_active and m.target_id == a.aircraft_id and m.phase == "terminal"]
                if m_incoming:
                    a.rwr_status = "MISSILE"
                    continue
                
                # Check for enemy radars
                for enemy in all_aircraft:
                    if not enemy.is_alive or enemy.team == a.team or not enemy.radar.is_active:
                        continue
                    
                    # If this enemy is tracking us specifically
                    if enemy.radar.tracking_target_id == a.aircraft_id:
                        a.rwr_status = "LOCK"
                        break
                    
                    # If this enemy is scanning and can see us
                    # (Quick check - we reuse radar detect probability logic roughly)
                    if a.rwr_status != "LOCK":
                        # We use a lower threshold for RWR detection of scans
                        dist = distance_km(a.x_km, a.y_km, a.z_km, enemy.x_km, enemy.y_km, enemy.z_km)
                        if dist < enemy.radar.r_max_km * 1.2: # RWR sensitive at 120% radar range
                            a.rwr_status = "SEARCH"

            # ---- 3. Agent decisions ----
            for agent in blue_agents:
                new_m = agent.decide_and_act(
                    t, self.dt, all_aircraft, missiles_in_flight,
                    blue_decon, rng, event_log,
                )
                if new_m is not None:
                    missiles_in_flight.append(new_m)
                    missiles_fired_blue += 1

            for agent in red_agents:
                new_m = agent.decide_and_act(
                    t, self.dt, all_aircraft, missiles_in_flight,
                    red_decon, rng, event_log,
                )
                if new_m is not None:
                    missiles_in_flight.append(new_m)
                    missiles_fired_red += 1

            # ---- 4. Update aircraft ----
            for ac in all_aircraft:
                ac.update(self.dt)

            # ---- 5. Snapshot ----
            if t - last_snapshot >= self.history_period:
                last_snapshot = t
                state_history.append(self._snapshot(t, all_aircraft, missiles_in_flight))

            t += self.dt

            # ---- Stop conditions ----
            blue_alive = any(a.is_alive for a in scenario.blue_aircraft)
            red_alive = any(a.is_alive for a in scenario.red_aircraft)
            if not blue_alive or not red_alive:
                break
            # All missiles expended and none in flight
            total_remaining = sum(a.missiles_remaining for a in all_aircraft if a.is_alive)
            if total_remaining == 0 and len(missiles_in_flight) == 0:
                break

        # Final snapshot
        state_history.append(self._snapshot(t, all_aircraft, missiles_in_flight))

        blue_kills = sum(a.kill_count for a in scenario.blue_aircraft)
        red_kills = sum(a.kill_count for a in scenario.red_aircraft)
        blue_losses = sum(1 for a in scenario.blue_aircraft if not a.is_alive)
        red_losses = sum(1 for a in scenario.red_aircraft if not a.is_alive)

        return SimulationResult(
            scenario_name=scenario.scenario_name,
            blue_kills=blue_kills,
            red_kills=red_kills,
            blue_losses=blue_losses,
            red_losses=red_losses,
            kill_ratio=blue_kills / max(red_losses, 1),
            duration_sec=t,
            missiles_fired_blue=missiles_fired_blue,
            missiles_fired_red=missiles_fired_red,
            event_log=event_log,
            state_history=state_history,
        )

    @staticmethod
    def _snapshot(
        t: float,
        aircraft: List[Aircraft],
        missiles: List[Missile],
    ) -> Dict:
        return {
            "t_sec": t,
            "aircraft": [a.get_state_dict() for a in aircraft],
            "missiles": [m.get_state_dict() for m in missiles if m.is_active],
        }
