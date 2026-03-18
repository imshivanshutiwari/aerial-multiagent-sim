"""Gymnasium Environment for BVR Combat Simulator.

Wraps the BVR engine into a standard RL interface for training PPO agents.
The agent controls 'Blue-1'.
"""

from __future__ import annotations

import math
import gymnasium as gym
from gymnasium import spaces
import numpy as np

from simulation.scenario import Scenario
from ai.deconfliction import Deconfliction
from engine.missile import Missile


class BvrCombatEnv(gym.Env):
    """
    Observation:
      [0]: own normalized x
      [1]: own normalized y
      [2]: own heading (sin)
      [3]: own heading (cos)
      [4]: own velocity normalized
      [5]: missiles remaining (normalized)
      [6]: nearest enemy dx (normalized)
      [7]: nearest enemy dy (normalized)
      [8]: nearest enemy heading (sin)
      [9]: nearest enemy heading (cos)
      [10]: nearest incoming missile TTG (0 if none)
    
    Actions:
      0: Maintain
      1: Hard Left
      2: Hard Right
      3: Accelerate
      4: Decelerate
      5: Fire Missile at Nearest target
    """

    def __init__(self, scenario_path="data/scenario_configs/4v4_equal.yaml", dt=0.5):
        super().__init__()
        self.scenario_path = scenario_path
        self.dt = dt
        self.action_space = spaces.Discrete(6)
        self.observation_space = spaces.Box(low=-1.0, high=1.0, shape=(11,), dtype=np.float32)
        
        self.agent_id = "Blue-1"
        self.max_time = 300.0  # limit RL episodes to 5 mins to speed up training
        self.map_size = 200.0  # normalize coordinates to [-1, 1] relative to center
        self.max_speed = 800.0

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        if seed is None:
            seed = np.random.randint(0, 100000)
        self.rng = np.random.default_rng(seed)
        
        self.scenario = Scenario(self.scenario_path)
        self.scenario.time_limit_sec = self.max_time
        
        self.all_aircraft = self.scenario.all_aircraft()
        self.blue_agents = self.scenario.blue_agents
        self.red_agents = self.scenario.red_agents
        self.blue_decon = Deconfliction()
        self.red_decon = Deconfliction()
        
        self.missiles_in_flight = []
        self.event_log = []
        self.t = 0.0
        
        self.prev_blue_score = 0
        self.prev_red_score = 0
        
        return self._get_obs(), {}

    def step(self, action: int):
        ac = next((a for a in self.all_aircraft if a.aircraft_id == self.agent_id), None)
        
        reward = 0.0
        terminated = False
        truncated = False
        
        # 0. Apply RL Action
        if ac and ac.is_alive:
            if action == 1:
                ac.heading_deg = (ac.heading_deg - 30.0 * self.dt) % 360.0
            elif action == 2:
                ac.heading_deg = (ac.heading_deg + 30.0 * self.dt) % 360.0
            elif action == 3:
                ac.velocity_ms = min(ac.velocity_ms + 20.0 * self.dt, self.max_speed)
            elif action == 4:
                ac.velocity_ms = max(ac.velocity_ms - 20.0 * self.dt, 200.0)
            elif action == 5:
                # Fire missile
                if ac.missiles_remaining > 0:
                    reds = [r for r in self.all_aircraft if r.team == "Red" and r.is_alive]
                    if reds:
                        closest = min(reds, key=lambda r: (r.x_km - ac.x_km)**2 + (r.y_km - ac.y_km)**2)
                        ac.missiles_remaining -= 1
                        m_id = f"M-{ac.aircraft_id}-{ac.missiles_remaining}"
                        m = Missile(m_id, ac.aircraft_id, closest.aircraft_id, ac.x_km, ac.y_km, ac.velocity_ms, ac.heading_deg)
                        self.missiles_in_flight.append(m)
                        reward -= 5.0  # slight penalty to prevent spamming
            
            reward += 0.01  # survival bonus
        else:
            terminated = True
            reward -= 50.0  # killed

        # 1. Update missiles
        for m in self.missiles_in_flight:
            if not m.is_active: continue
            target = next((a for a in self.all_aircraft if a.aircraft_id == m.target_id), None)
            if target and target.is_alive:
                tvx, tvy = target.get_velocity_components()
                m.update(self.dt, target.x_km, target.y_km, tvx, tvy)
            else:
                m.is_active = False

        # 2. Check kills
        for m in list(self.missiles_in_flight):
            if not m.is_active: continue
            target = next((a for a in self.all_aircraft if a.aircraft_id == m.target_id), None)
            if target and target.is_alive:
                tvx, tvy = target.get_velocity_components()
                is_kill, miss_d = m.check_proximity_kill(target.x_km, target.y_km, tvx, tvy, self.dt, self.rng)
                if not m.is_active:
                    owner = next((a for a in self.all_aircraft if a.aircraft_id == m.owner_id), None)
                    if is_kill:
                        target.is_alive = False
                        if owner: owner.kill_count += 1
                        self.blue_decon.release(target.aircraft_id)
                        self.red_decon.release(target.aircraft_id)
        
        self.missiles_in_flight = [m for m in self.missiles_in_flight if m.is_active]

        # 3. AI Decisions (for everyone except the RL agent)
        for agent in self.blue_agents:
            if agent.aircraft.aircraft_id == self.agent_id: continue # RL controls this one
            new_m = agent.decide_and_act(self.t, self.dt, self.all_aircraft, self.missiles_in_flight, self.blue_decon, self.rng, self.event_log)
            if new_m: self.missiles_in_flight.append(new_m)

        for agent in self.red_agents:
            new_m = agent.decide_and_act(self.t, self.dt, self.all_aircraft, self.missiles_in_flight, self.red_decon, self.rng, self.event_log)
            if new_m: self.missiles_in_flight.append(new_m)

        # 4. Update kinematics
        for a in self.all_aircraft:
            # Skip updating RL agent's heading/speed because the step() action handled it,
            # but we must still update its physical position.
            a.update(self.dt)

        self.t += self.dt

        # 5. Rewards & Completion
        blue_alive = sum(1 for a in self.scenario.blue_aircraft if a.is_alive)
        red_alive = sum(1 for a in self.scenario.red_aircraft if a.is_alive)
        
        blue_kills = sum(a.kill_count for a in self.scenario.blue_aircraft)
        red_kills = sum(a.kill_count for a in self.scenario.red_aircraft)

        score_diff = (blue_kills - self.prev_blue_score) * 100.0
        score_diff -= (red_kills - self.prev_red_score) * 100.0
        reward += score_diff
        
        self.prev_blue_score = blue_kills
        self.prev_red_score = red_kills

        if blue_alive == 0 or red_alive == 0:
            terminated = True
            
        if self.t >= self.max_time:
            truncated = True

        return self._get_obs(), float(reward), terminated, truncated, {}

    def _get_obs(self):
        obs = np.zeros(11, dtype=np.float32)
        ac = next((a for a in self.all_aircraft if a.aircraft_id == self.agent_id), None)
        if not ac or not ac.is_alive:
            return obs
            
        obs[0] = (ac.x_km - 100.0) / 100.0
        obs[1] = (ac.y_km - 100.0) / 100.0
        h_rad = math.radians(ac.heading_deg)
        obs[2] = math.sin(h_rad)
        obs[3] = math.cos(h_rad)
        obs[4] = ac.velocity_ms / self.max_speed
        obs[5] = ac.missiles_remaining / 4.0
        
        reds = [r for r in self.all_aircraft if r.team == "Red" and r.is_alive]
        if reds:
            closest = min(reds, key=lambda r: (r.x_km - ac.x_km)**2 + (r.y_km - ac.y_km)**2)
            obs[6] = (closest.x_km - ac.x_km) / 200.0
            obs[7] = (closest.y_km - ac.y_km) / 200.0
            cr_rad = math.radians(closest.heading_deg)
            obs[8] = math.sin(cr_rad)
            obs[9] = math.cos(cr_rad)
        
        # Threat TTG (placeholder simple ratio)
        incoming = [m for m in self.missiles_in_flight if m.target_id == self.agent_id]
        if incoming:
            closest_m = min(incoming, key=lambda m: (m.x_km - ac.x_km)**2 + (m.y_km - ac.y_km)**2)
            dist_km = math.sqrt((closest_m.x_km - ac.x_km)**2 + (closest_m.y_km - ac.y_km)**2)
            ttg = max(0.0, 1.0 - (dist_km / 50.0))  # 1.0 if very close, 0.0 if > 50km
            obs[10] = ttg
            
        return obs
