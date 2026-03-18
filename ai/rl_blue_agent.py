"""RL-capable Blue Agent using a trained Stable Baselines 3 PPO model."""

from __future__ import annotations

import math
import numpy as np
from stable_baselines3 import PPO

from engine.missile import Missile
from engine.aircraft import Aircraft
from ai.blue_agent import BlueAgent


class RLBlueAgent(BlueAgent):
    """
    Inherits from BlueAgent to fulfill the typing contract in SimulationRunner,
    but executes neural network inference instead of the DARPA 5-step loop.
    """

    def __init__(self, aircraft: Aircraft, model_path: str = "models/ppo_bvr_agent.zip"):
        super().__init__(aircraft)
        self.agent_id = aircraft.aircraft_id
        
        # Load the trained model
        try:
            self.model = PPO.load(model_path)
            self.model_loaded = True
        except Exception:
            self.model_loaded = False
            print(f"[RLBlueAgent] Warning: Could not load model from {model_path}. "
                  "Agent will hover aimlessly. Run `python train_rl_agent.py` first.")

    def decide_and_act(
        self,
        t: float,
        dt: float,
        all_aircraft: list[Aircraft],
        missiles_in_flight: list[Missile],
        deconfliction,
        rng: np.random.Generator,
        event_log: list[dict],
    ) -> list[Missile] | None:
        """Observe state, predict action via Neural Network, apply to kinestatics."""
        
        ac = next((a for a in all_aircraft if a.aircraft_id == self.agent_id), None)
        if not ac or not ac.is_alive:
            return None

        if not self.model_loaded:
            return None

        # 1. Format Observation matching the Gymnasium Env exactly
        obs = np.zeros(11, dtype=np.float32)
        obs[0] = (ac.x_km - 100.0) / 100.0
        obs[1] = (ac.y_km - 100.0) / 100.0
        h_rad = math.radians(ac.heading_deg)
        obs[2] = math.sin(h_rad)
        obs[3] = math.cos(h_rad)
        obs[4] = ac.velocity_ms / 800.0
        obs[5] = ac.missiles_remaining / 4.0
        
        reds = [r for r in all_aircraft if r.team == "Red" and r.is_alive]
        closest_red = None
        if reds:
            closest_red = min(reds, key=lambda r: (r.x_km - ac.x_km)**2 + (r.y_km - ac.y_km)**2)
            obs[6] = (closest_red.x_km - ac.x_km) / 200.0
            obs[7] = (closest_red.y_km - ac.y_km) / 200.0
            cr_rad = math.radians(closest_red.heading_deg)
            obs[8] = math.sin(cr_rad)
            obs[9] = math.cos(cr_rad)
            
        incoming = [m for m in missiles_in_flight if m.target_id == self.agent_id]
        if incoming:
            closest_m = min(incoming, key=lambda m: (m.x_km - ac.x_km)**2 + (m.y_km - ac.y_km)**2)
            dist_km = math.sqrt((closest_m.x_km - ac.x_km)**2 + (closest_m.y_km - ac.y_km)**2)
            ttg = max(0.0, 1.0 - (dist_km / 50.0))
            obs[10] = ttg

        # 2. Network Inference
        action, _states = self.model.predict(obs, deterministic=True)
        action = int(action)

        # 3. Apply Action Translator
        fired_missile = None
        
        if action == 1:
            ac.heading_deg = (ac.heading_deg - 30.0 * dt) % 360.0
        elif action == 2:
            ac.heading_deg = (ac.heading_deg + 30.0 * dt) % 360.0
        elif action == 3:
            ac.velocity_ms = min(ac.velocity_ms + 20.0 * dt, 800.0)
        elif action == 4:
            ac.velocity_ms = max(ac.velocity_ms - 20.0 * dt, 200.0)
        elif action == 5:
            # Fire missile
            if ac.missiles_remaining > 0 and closest_red is not None:
                ac.missiles_remaining -= 1
                m_id = f"M-{ac.aircraft_id}-{ac.missiles_remaining}"
                fired_missile = Missile(m_id, ac.aircraft_id, closest_red.aircraft_id, 
                                        ac.x_km, ac.y_km, ac.velocity_ms, ac.heading_deg)
                event_log.append({
                    "t": t, "actor": self.agent_id, "team": "Blue", "type": "RL_FIRE",
                    "detail": f"NN fired {m_id} at {closest_red.aircraft_id}", "target": closest_red.aircraft_id
                })
                
        return fired_missile
