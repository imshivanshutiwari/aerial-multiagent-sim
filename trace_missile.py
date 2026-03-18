import json
from simulation.scenario import Scenario
from simulation.simulation_runner import SimulationRunner

sc = Scenario('data/scenario_configs/4v4_equal.yaml')
runner = SimulationRunner(dt=0.5, history_period=0.5)

original_update = runner.run
def debug_run(self, scenario, random_seed=42):
    import numpy as np
    from ai.deconfliction import Deconfliction
    rng = np.random.default_rng(random_seed)

    all_aircraft = scenario.all_aircraft()
    blue_agents = scenario.blue_agents
    red_agents = scenario.red_agents

    blue_decon = Deconfliction()
    red_decon = Deconfliction()

    missiles_in_flight = []
    event_log = []
    state_history = []

    t = 0.0
    while t < scenario.time_limit_sec:
        for m in missiles_in_flight:
            if not m.is_active: continue
            target = next((a for a in all_aircraft if a.aircraft_id == m.target_id), None)
            if target and target.is_alive:
                tvx, tvy = target.get_velocity_components()
                m.update(self.dt, target.x_km, target.y_km, tvx, tvy)
                dist = ((m.x_km - target.x_km)**2 + (m.y_km - target.y_km)**2)**0.5 * 1000
                if m.missile_id == 'M-Blue-1-1' and m.phase == 'terminal':
                    print(f"t={t:.1f} dist={dist:.1f}m m_v={m.velocity_ms:.1f} m_h={m.heading_deg:.1f} t_h={target.heading_deg:.1f} fuel={m.fuel_remaining_sec:.1f}")
        
        for m in missiles_in_flight:
            if not m.is_active: continue
            target = next((a for a in all_aircraft if a.aircraft_id == m.target_id), None)
            if target and target.is_alive:
                is_kill, miss_dist = m.check_proximity_kill(target.x_km, target.y_km, rng)
                if miss_dist <= 100.0:
                    print(f"[{t}] DETONATED! {m.missile_id} at {target.aircraft_id}. kill={is_kill} dist={miss_dist:.1f}m")
        
        missiles_in_flight = [m for m in missiles_in_flight if m.is_active]

        for agent in blue_agents:
            new_m = agent.decide_and_act(t, self.dt, all_aircraft, missiles_in_flight, blue_decon, rng, event_log)
            if new_m:
                missiles_in_flight.append(new_m)
        for agent in red_agents:
            new_m = agent.decide_and_act(t, self.dt, all_aircraft, missiles_in_flight, red_decon, rng, event_log)
            if new_m:
                missiles_in_flight.append(new_m)
        
        for ac in all_aircraft:
            ac.update(self.dt)
        
        t += self.dt
        if not any(a.is_alive for a in scenario.blue_aircraft) or not any(a.is_alive for a in scenario.red_aircraft):
            break

SimulationRunner.run = debug_run
res = runner.run(sc, random_seed=42)
