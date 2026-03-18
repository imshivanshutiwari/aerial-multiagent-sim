import yaml
from pathlib import Path
from simulation.scenario import Scenario
from simulation.simulation_runner import SimulationRunner

scenario_path = 'data/scenario_configs/aggressive_showdown.yaml'
scenario = Scenario(scenario_path, agent_type="darpa")
runner = SimulationRunner(dt=0.5)
result = runner.run(scenario, random_seed=42)

print(f"Duration: {result.duration_sec}s")
print(f"Blue Kills: {result.blue_kills}, Red Kills: {result.red_kills}")
print(f"Blue Missiles Fired: {result.missiles_fired_blue}")
print(f"Red Missiles Fired: {result.missiles_fired_red}")

max_missiles = max(len(h.get("missiles", [])) for h in result.history)
print(f"Total History Steps: {len(result.history)}")
print(f"Max Missiles at once (History): {max_missiles}")

missile_events = [e for e in result.event_log if "MISSILE" in e["type"]]
print(f"Missile Events: {len(missile_events)}")
for e in missile_events[:5]: print(e)
