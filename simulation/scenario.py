"""Scenario loader – reads YAML configs and creates aircraft + agents.

YAML format (example 4v4_equal.yaml):
  scenario_name: "4v4 Equal Capability BVR Engagement"
  blue_force:
    count: 4
    formation: "line_abreast"
    start_x_km: 0
    start_y_km: [0, 15, -15, 30]
    heading_deg: 90
    velocity_ms: 550
  red_force:
    count: 4
    formation: "line_abreast"
    start_x_km: 300
    start_y_km: [0, 15, -15, 30]
    heading_deg: 270
    velocity_ms: 550
  engagement_area_km: 400
  time_limit_seconds: 600
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

import yaml

from engine.aircraft import Aircraft
from engine.ecm import ECMSystem
from engine.radar import Radar
from ai.blue_agent import BlueAgent
from ai.red_agent import RedAgent


class Scenario:
    """Load a YAML scenario file and create aircraft + agent instances."""

    def __init__(self, config_path: str, agent_type: str = "darpa") -> None:
        self.config_path = config_path
        self.agent_type = agent_type
        with open(config_path, "r") as f:
            self.cfg = yaml.safe_load(f)

        self.scenario_name: str = self.cfg["scenario_name"]
        self.engagement_area_km: float = float(self.cfg.get("engagement_area_km", 400))
        self.time_limit_sec: float = float(self.cfg.get("time_limit_seconds", 600))

        self.blue_aircraft: List[Aircraft] = []
        self.red_aircraft: List[Aircraft] = []
        self.blue_agents: List[BlueAgent] = []
        self.red_agents: List[RedAgent] = []

        self._build_blue()
        self._build_red()
        self._assign_wingmen()

    # ------------------------------------------------------------------
    def _build_blue(self) -> None:
        bc = self.cfg["blue_force"]
        count = int(bc["count"])
        y_list = bc["start_y_km"]
        if isinstance(y_list, (int, float)):
            y_list = [float(y_list)] * count
        for i in range(count):
            ac = Aircraft(
                aircraft_id=f"Blue-{i+1}",
                team="Blue",
                x_km=float(bc["start_x_km"]),
                y_km=float(y_list[i % len(y_list)]),
                velocity_ms=float(bc.get("velocity_ms", 550)),
                heading_deg=float(bc.get("heading_deg", 90)),
                g_limit=9.0,
                max_speed_ms=600.0,
                radar=Radar(r_max_km=150.0),
                ecm=ECMSystem(chaff_success_probability=0.35),
                missiles_remaining=4,
                rcs=3.0,
            )
            self.blue_aircraft.append(ac)
            if self.agent_type == "rl":
                from ai.rl_blue_agent import RLBlueAgent
                self.blue_agents.append(RLBlueAgent(ac))
            else:
                self.blue_agents.append(BlueAgent(ac))

    def _build_red(self) -> None:
        rc = self.cfg["red_force"]
        count = int(rc["count"])
        y_list = rc["start_y_km"]
        if isinstance(y_list, (int, float)):
            y_list = [float(y_list)] * count
        for i in range(count):
            ac = Aircraft(
                aircraft_id=f"Red-{i+1}",
                team="Red",
                x_km=float(rc["start_x_km"]),
                y_km=float(y_list[i % len(y_list)]),
                velocity_ms=float(rc.get("velocity_ms", 550)),
                heading_deg=float(rc.get("heading_deg", 270)),
                g_limit=9.0,
                max_speed_ms=600.0,
                radar=Radar(r_max_km=120.0),
                ecm=ECMSystem(chaff_success_probability=0.30),
                missiles_remaining=4,
                rcs=3.0,
            )
            self.red_aircraft.append(ac)
            self.red_agents.append(RedAgent(ac))

    def _assign_wingmen(self) -> None:
        """Blue flies in pairs: 1–2, 3–4, etc."""
        for i in range(0, len(self.blue_aircraft) - 1, 2):
            a, b = self.blue_aircraft[i], self.blue_aircraft[i + 1]
            a.wingman_id = b.aircraft_id
            b.wingman_id = a.aircraft_id

    def all_aircraft(self) -> List[Aircraft]:
        return self.blue_aircraft + self.red_aircraft
