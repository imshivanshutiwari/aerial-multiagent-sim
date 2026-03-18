"""BVR Air Combat AI Agent Simulator — entry point.

Run:
    python main.py                              # headless simulation
    python main.py --pygame                     # Pygame tactical display
    streamlit run dashboard/app.py              # Streamlit dashboard
"""

from __future__ import annotations

import argparse
from pathlib import Path

from simulation.scenario import Scenario
from simulation.simulation_runner import SimulationRunner


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="BVR Air Combat AI Agent Simulator — "
                    "Inspired by Lockheed Martin DARPA AIR Program"
    )
    p.add_argument(
        "--scenario", type=str,
        default=str(Path("data/scenario_configs/4v4_equal.yaml")),
        help="Path to scenario YAML.",
    )
    p.add_argument(
        "--agent", type=str, choices=["darpa", "rl"], default="darpa",
        help="Which AI logic to use for Blue team.",
    )
    p.add_argument("--seed", type=int, default=42, help="Random seed.")
    p.add_argument("--dt", type=float, default=0.5, help="Time step (sec).")
    p.add_argument("--pygame", action="store_true",
                   help="Launch interactive Pygame tactical display.")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    if args.pygame:
        import pygame
        from visualisation.pygame_renderer import run_pygame
        from visualisation.menu import show_scenario_menu
        
        while True:
            pygame.init()
            screen = pygame.display.set_mode((1000, 600))
            pygame.display.set_caption("BVR Combat Simulation — Main Menu")
            font = pygame.font.SysFont("consolas", 20, bold=True)
            
            chosen = show_scenario_menu(screen, font)
            if not chosen:
                pygame.quit()
                break
                
            actual_seed = None if args.seed == -1 else args.seed
            pygame.quit() # Close menu context
            
            # Launch the actual 3D tactical renderer
            run_pygame(chosen, seed=actual_seed, agent_type=args.agent)
            
        return

    # Headless mode
    actual_seed = None if args.seed == -1 else args.seed
    scenario = Scenario(args.scenario, agent_type=args.agent)
    runner = SimulationRunner(dt=args.dt)
    result = runner.run(scenario, random_seed=args.seed)

    # 11. Send summary email
    try:
        from utils.email_sim import send_simulation_report
        send_simulation_report(result)
    except Exception as e:
        print(f"Warning: Failed to generate local email report: {e}")

    print("=" * 60)
    print(f" BVR Combat Simulation Results")
    print("=" * 60)
    print(f" Scenario:           {result.scenario_name}")
    print(f" Duration:           {result.duration_sec:.1f} sec")
    print(f" Blue kills:         {result.blue_kills}")
    print(f" Red kills:          {result.red_kills}")
    print(f" Blue losses:        {result.blue_losses}")
    print(f" Red losses:         {result.red_losses}")
    print(f" Kill ratio:         {result.kill_ratio:.2f}")
    print(f" Blue missiles fired:{result.missiles_fired_blue}")
    print(f" Red missiles fired: {result.missiles_fired_red}")
    print(f" Events logged:      {len(result.event_log)}")
    print("=" * 60)

    # Print last 10 events
    print("\nLast 10 events:")
    for ev in result.event_log[-10:]:
        print(f"  [{ev['t']:6.1f}s] {ev.get('actor','')} — {ev['type']}: {ev['detail']}")


if __name__ == "__main__":
    main()
