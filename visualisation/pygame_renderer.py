"""Pygame tactical display for BVR Combat Simulation.

Window 1600×900. Dark background #080C14. Top-down tactical map.
400 km × 225 km. Each pixel = 0.25 km.

Controls:
  1 = real-time, 2 = 10×, 3 = 50×, 4 = 200×
  SPACE = pause, R = reset, ESC = quit
"""

from __future__ import annotations

import math
from typing import Dict, List, Tuple

import numpy as np
import pygame

from engine.aircraft import Aircraft
from engine.missile import Missile
from engine.physics import KM_TO_M, distance_km
from ai.deconfliction import Deconfliction
from simulation.scenario import Scenario
from simulation.simulation_runner import SimulationRunner
from visualisation.aircraft_sprite import draw_aircraft
from visualisation.missile_sprite import draw_missile
from visualisation.missile_trail import MissileTrail
from visualisation.radar_sweep import RadarSweep
from visualisation.explosion import Explosion
from visualisation.hud import HUD, CYAN, WHITE, BLUE, ORANGE, GREY


# Screen layout
WIDTH = 1600
HEIGHT = 900
BG_COLOR = (8, 12, 20)
KM_PER_PX = 0.25
GRID_COLOR = (20, 28, 42)


def _world_to_screen(x_km: float, y_km: float, km_per_px: float, cam_x: float = 0.0, cam_y: float = 0.0) -> Tuple[int, int]:
    """Convert world (km) to screen (px). Local offset by cam_x/y."""
    sx = WIDTH // 2 + int((x_km - cam_x) / km_per_px)
    sy = HEIGHT // 2 - int((y_km - cam_y) / km_per_px)
    return sx, sy


def _km_to_px(km: float, km_per_px: float) -> int:
    return max(1, int(km / km_per_px))


class PygameRenderer:
    """Live BVR simulation with full tactical display."""

    def __init__(self, scenario_path: str, seed: int = 42, agent_type: str = "darpa") -> None:
        self.scenario_path = scenario_path
        self.seed = seed
        self.agent_type = agent_type
        self.dt_sim = 0.5
        
        # Explicitly define for linter
        self.all_aircraft: List[Aircraft] = []
        self._curr_states: Dict[str, Tuple[float, float, float, float]] = {}
        self._prev_states: Dict[str, Tuple[float, float, float, float]] = {}
        self.event_log: List[dict] = []
        self.missiles: List[Missile] = []
        self.shake_amount: float = 0.0
        self.blur_surface: pygame.Surface = None
        self.font: pygame.font.Font = None
        self.scenario: Scenario = None  # Will be set in _reset
        self.rng: np.random.Generator = None
        self.blue_decon: Deconfliction = None
        self.red_decon: Deconfliction = None
        self.t_sim: float = 0.0
        self.missile_trails: MissileTrail = None
        self.sweeps: Dict[str, RadarSweep] = {}
        self.explosions: List[Explosion] = []
        self._last_event_count: int = 0
        self.t_since_step: float = 0.0

        self.speed_modes = {
            pygame.K_1: 1, pygame.K_2: 10,
            pygame.K_3: 50, pygame.K_4: 200,
        }
        self.speed_mult = 10
        self.paused = False
        self.km_per_px = 0.25 # Start at 0.25, will auto-scale
        self.cam_x = 0.0
        self.cam_y = 0.0

        self._reset()

    def _reset(self) -> None:
        self.scenario = Scenario(self.scenario_path, agent_type=self.agent_type)
        self.rng = np.random.default_rng(self.seed)
        self.all_aircraft = self.scenario.all_aircraft()
        self.missiles: List[Missile] = []
        self.event_log: List[dict] = []
        self.blue_decon = Deconfliction()
        self.red_decon = Deconfliction()
        self.t_sim = 0.0

        # Visual effects
        self.shake_amount = 0.0
        self.blur_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self.missile_trails = MissileTrail()
        self.sweeps: Dict[str, RadarSweep] = {}
        for ac in self.all_aircraft:
            self.sweeps[ac.aircraft_id] = RadarSweep(team=ac.team)
        self.explosions: List[Explosion] = []
        self._last_event_count = 0
        self.cam_x = 0.0
        self.cam_y = 0.0

        # For interpolation
        self.t_since_step = 0.0
        self._curr_states = {
            ac.aircraft_id: (ac.x_km, ac.y_km, ac.z_km, ac.heading_deg)
            for ac in self.all_aircraft
        }
        self._prev_states = self._curr_states.copy()

    def run(self) -> None:
        pygame.init()
        screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("BVR Combat Simulation — Tactical Display")
        clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas", 18, bold=True)
        self.hud = HUD(self.font)

        # ---- Modern Splash Screen ----
        from visualisation.splash_screen import SplashScreen
        splash = SplashScreen(WIDTH, HEIGHT)
        while not splash.is_finished():
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    pygame.quit()
                    return
            splash.draw(screen)
            clock.tick(60)

        running = True
        while running:
            dt_real = clock.tick(60) / 1000.0

            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    running = False
                elif ev.type == pygame.KEYDOWN:
                    if ev.key in self.speed_modes:
                        self.speed_mult = self.speed_modes[ev.key]
                    elif ev.key == pygame.K_SPACE:
                        self.paused = not self.paused
                    elif ev.key == pygame.K_r:
                        self._reset()
                    elif ev.key == pygame.K_ESCAPE:
                        running = False

            if not self.paused:
                self.t_since_step += dt_real * self.speed_mult
                if self.t_since_step >= self.dt_sim:
                    self._step_sim()
                    self.t_since_step = 0.0

            # Interpolation Alpha
            alpha = min(1.0, self.t_since_step / self.dt_sim)

            # Auto-scale zoom
            self._update_zoom()

            # Camera Shake Decay
            self.shake_amount *= 0.9

            # Update visual effects
            for sw in self.sweeps.values():
                sw.update(dt_real)
            for ex in self.explosions:
                ex.update(dt_real)
            self.explosions = [e for e in self.explosions if e.alive]

            # Check for new kill/miss events → create explosions
            prev_k = self._last_event_count
            self._spawn_explosions()
            if len(self.event_log) > prev_k:
                self.shake_amount = 15.0 # Impact shake

            # ---- DRAW ----
            # Motion Blur: instead of screen.fill(BG_COLOR), we draw a semi-transparent BG
            pygame.draw.rect(self.blur_surface, (*BG_COLOR, 60), (0, 0, WIDTH, HEIGHT))
            screen.blit(self.blur_surface, (0, 0))
            
            # Screen Shake displacement
            shake_ox = self.rng.uniform(-self.shake_amount, self.shake_amount)
            shake_oy = self.rng.uniform(-self.shake_amount, self.shake_amount)
            
            self._draw_grid(screen)

            # Radar detection rings + sweeps
            for ac in self.all_aircraft:
                if not ac.is_alive:
                    continue
                # INTERPOLATED POS
                px_km, py_km, pz_km, _ = self._get_interpolated_state(ac.aircraft_id, alpha)
                cx, cy = _world_to_screen(px_km, py_km, self.km_per_px, self.cam_x, self.cam_y)
                r_px = _km_to_px(ac.radar.get_detection_range_for_display(), self.km_per_px)
                ring_color = (20, 40, 80) if ac.team == "Blue" else (80, 20, 20)
                pygame.draw.circle(screen, ring_color, (cx, cy), r_px, 1)
                self.sweeps[ac.aircraft_id].draw(screen, (cx, cy), r_px)

            # Missile trails + dots
            for m in self.missiles:
                if not m.is_active:
                    continue
                # Interpolate if missile existed in prev step
                pos = _world_to_screen(m.x_km, m.y_km, self.km_per_px, self.cam_x, self.cam_y)
                self.missile_trails.update(m.missile_id, pos)
                owner = next((a for a in self.all_aircraft
                              if a.aircraft_id == m.owner_id), None)
                team = owner.team if owner else "Blue"
                self.missile_trails.draw(screen, m.missile_id, team)
                # Draw high-fidelity missile head
                draw_missile(screen, pos, m.heading_deg, team, m.phase, self.t_sim)

            # Aircraft sprites
            for ac in self.all_aircraft:
                px_km, py_km, pz_km, head = self._get_interpolated_state(ac.aircraft_id, alpha)
                pos = _world_to_screen(px_km, py_km, self.km_per_px, self.cam_x, self.cam_y)
                
                # GROUND SHADOW (3D DEPTH)
                if ac.is_alive:
                    shadow_pos = (pos[0] + int(shake_ox), pos[1] + int(shake_oy))
                    # Shadow size scales inversely with altitude (subtle)
                    s_size = max(2, int(8 - pz_km / 2.0))
                    pygame.draw.circle(screen, (30, 35, 50, 140), shadow_pos, s_size)
                
                # Apply shake to icon pos
                pos_shaken = (pos[0] + int(shake_ox), pos[1] + int(shake_oy))
                draw_aircraft(screen, pos_shaken, head, ac.team, ac.is_alive, z_km=pz_km)

            # Explosions
            for ex in self.explosions:
                ex.draw(screen)

            # Results calculation for overlay
            blue_kills = sum(a.kill_count for a in self.scenario.blue_aircraft)
            red_kills = sum(a.kill_count for a in self.scenario.red_aircraft)

            # Draw HUD
            self.hud.draw(
                screen,
                self.scenario.scenario_name,
                self.t_sim,
                self.speed_mult,
                self.paused,
                blue_kills,
                red_kills,
                self.scenario.blue_aircraft,
                self.event_log,
            )

            # Match Summary (End of Sim)
            blue_k = sum(a.kill_count for a in self.scenario.blue_aircraft)
            red_k = sum(a.kill_count for a in self.scenario.red_aircraft)
            
            if self.t_sim >= self.scenario.time_limit_sec:
                # Dim the screen
                dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                dim.fill((0, 0, 0, 180))
                screen.blit(dim, (0, 0))
                
                # Draw Box
                bw, bh = 500, 300
                bx, by = (WIDTH - bw) // 2, (HEIGHT - bh) // 2
                pygame.draw.rect(screen, (15, 25, 50), (bx, by, bw, bh), border_radius=12)
                pygame.draw.rect(screen, CYAN, (bx, by, bw, bh), 2, border_radius=12)
                
                # Render Text
                title = self.font.render("MISSION COMPLETE", True, WHITE)
                screen.blit(title, (bx + (bw - title.get_width()) // 2, by + 40))
                
                res_b = self.font.render(f"BLUE KILLS: {blue_k} | LOSSES: {4 - sum(1 for a in self.scenario.blue_aircraft if a.is_alive)}", True, BLUE)
                res_r = self.font.render(f"RED KILLS:  {red_k} | LOSSES: {blue_k}", True, ORANGE)
                
                screen.blit(res_b, (bx + 50, by + 120))
                screen.blit(res_r, (bx + 50, by + 160))
                
                hint = self.font.render("Press 'R' to RESTART or 'ESC' to EXIT", True, GREY)
                screen.blit(hint, (bx + (bw - hint.get_width()) // 2, by + bh - 50))

            pygame.display.flip()

        pygame.quit()

    def _step_sim(self) -> None:
        """Run 1 sim step and update interpolation targets."""
        if self.t_sim >= self.scenario.time_limit_sec:
            return
            
        # 1. Previous state = what we just finished interpolating to
        self._prev_states = self._curr_states
        
        # 2. Update physics
        for m in self.missiles:
            if not m.is_active:
                continue
            
            # Explicitly find target_ac to satisfy linter
            t_ac = None
            for a_cand in self.all_aircraft:
                if a_cand.aircraft_id == m.target_id:
                    t_ac = a_cand
                    break
            
            if t_ac is None or not t_ac.is_alive:
                m.is_active = False
                continue
                
            tvx, tvy, tvz = t_ac.get_velocity_components()
            trcs = t_ac.get_rcs(m.x_km, m.y_km, m.z_km)
            m.update(self.dt_sim, t_ac.x_km, t_ac.y_km, t_ac.z_km, tvx, tvy, tvz, trcs)

        # 3. Kill checks
        for m in list(self.missiles):
            if not m.is_active:
                continue
                
            t_ac = None
            for a_cand in self.all_aircraft:
                if a_cand.aircraft_id == m.target_id:
                    t_ac = a_cand
                    break

            if t_ac is None or not t_ac.is_alive:
                m.is_active = False
                continue
                
            tvx, tvy, tvz = t_ac.get_velocity_components()
            is_kill, miss_d = m.check_proximity_kill(
                t_ac.x_km, t_ac.y_km, t_ac.z_km, tvx, tvy, tvz, self.dt_sim, self.rng
            )
            
            if not m.is_active: # Missile just died or hit
                o_ac = None
                for a_cand in self.all_aircraft:
                    if a_cand.aircraft_id == m.owner_id:
                        o_ac = a_cand
                        break
                
                if is_kill and o_ac:
                    t_ac.is_alive = False
                    o_ac.kill_count += 1
                    self.blue_decon.release(t_ac.aircraft_id)
                    self.red_decon.release(t_ac.aircraft_id)
                    self.event_log.append({
                        "t": self.t_sim, "actor": m.owner_id,
                        "team": o_ac.team,
                        "type": "KILL",
                        "detail": f"{m.missile_id} killed {t_ac.aircraft_id}",
                        "target": t_ac.aircraft_id,
                    })
                else:
                    self.blue_decon.release(t_ac.aircraft_id)
                    self.red_decon.release(t_ac.aircraft_id)
                    self.event_log.append({
                        "t": self.t_sim, "actor": m.owner_id,
                        "team": o_ac.team if o_ac else "?",
                        "type": "MISSILE_MISS",
                        "detail": f"{m.missile_id} missed {t_ac.aircraft_id}",
                        "target": t_ac.aircraft_id,
                    })

        self.missiles = [m for m in self.missiles if m.is_active]

        # 2.5 Update RWR status for visualization
        for a in self.all_aircraft:
            if not a.is_alive: continue
            a.rwr_status = "OFF"
            
            # Missile check
            m_incoming = [m for m in self.missiles if m.is_active and m.target_id == a.aircraft_id and m.phase == "terminal"]
            if m_incoming:
                a.rwr_status = "MISSILE"
                continue
            
            # Radar check
            for enemy in self.all_aircraft:
                if not enemy.is_alive or enemy.team == a.team or not enemy.radar.is_active:
                    continue
                if enemy.radar.tracking_target_id == a.aircraft_id:
                    a.rwr_status = "LOCK"
                    break
                # Scan check (proximity)
                if a.rwr_status != "LOCK":
                    dist = distance_km(a.x_km, a.y_km, a.z_km, enemy.x_km, enemy.y_km, enemy.z_km)
                    if dist < enemy.radar.r_max_km * 1.2:
                        a.rwr_status = "SEARCH"

        # 3. Agent decisions
        for agent in self.scenario.blue_agents:
            new_m = agent.decide_and_act(
                self.t_sim, self.dt_sim, self.all_aircraft,
                self.missiles, self.blue_decon, self.rng, self.event_log,
            )
            if new_m:
                self.missiles.append(new_m)

        for agent in self.scenario.red_agents:
            new_m = agent.decide_and_act(
                self.t_sim, self.dt_sim, self.all_aircraft,
                self.missiles, self.red_decon, self.rng, self.event_log,
            )
            if new_m:
                self.missiles.append(new_m)

        # 4. Update aircraft
        for ac in self.all_aircraft:
            ac.update(self.dt_sim)

        self.t_sim += self.dt_sim

        # Stop checks
        blue_alive = any(a.is_alive for a in self.scenario.blue_aircraft)
        red_alive = any(a.is_alive for a in self.scenario.red_aircraft)
        if not blue_alive or not red_alive:
            pass # Continue drawing until user quits
            
        # 5. Capture new target states
        self._curr_states = {}
        for ac in self.all_aircraft:
            self._curr_states[ac.aircraft_id] = (ac.x_km, ac.y_km, ac.z_km, ac.heading_deg)

    def _spawn_explosions(self) -> None:
        """Create explosion effects for new KILL/MISS events."""
        while self._last_event_count < len(self.event_log):
            ev = self.event_log[self._last_event_count]
            self._last_event_count += 1
            if ev["type"] in ("KILL", "MISSILE_MISS"):
                target = next((a for a in self.all_aircraft
                               if a.aircraft_id == ev.get("target", "")), None)
                if target:
                    # Explode at current pos
                    pos = _world_to_screen(target.x_km, target.y_km, self.km_per_px, self.cam_x, self.cam_y)
                    self.explosions.append(
                        Explosion(pos, is_kill=(ev["type"] == "KILL"))
                    )

    def _update_zoom(self) -> None:
        """Auto-adjust KM_PER_PX to keep all active entities in view."""
        active = [a for a in self.all_aircraft if a.is_alive]
        if not active:
            return
        
        min_x = min(a.x_km for a in active)
        max_x = max(a.x_km for a in active)
        min_y = min(a.y_km for a in active)
        max_y = max(a.y_km for a in active)
        
        for m in self.missiles:
            if not m.is_active: continue
            min_x = min(min_x, m.x_km)
            max_x = max(max_x, m.x_km)
            min_y = min(min_y, m.y_km)
            max_y = max(max_y, m.y_km)
            
        # Include current explosions (already in world space if we track it)
        # Actually simplest is to just include ALL aircraft, dead or alive, if they recently exploded.
        # But let's just include all aircraft for now to be safe, or just dead ones within 2 seconds.
        for ac in self.all_aircraft:
            if not ac.is_alive:
                # Keep dead aircraft in view for a bit if needed, or just always include them
                # to keep the whole theater in view? No, that's too much.
                pass

        # Padding
        dx = (max_x - min_x) + 40
        dy = (max_y - min_y) + 40
        
        # We need to fit dx km in WIDTH pixels and dy km in HEIGHT pixels
        target_kpp_x = dx / (WIDTH * 0.8) # scale to 80% screen
        target_kpp_y = dy / (HEIGHT * 0.8)
        
        target_kpp = max(0.01, max(target_kpp_x, target_kpp_y))
        # Smoothly move toward targets
        mid_x = (min_x + max_x) / 2
        mid_y = (min_y + max_y) / 2
        
        self.km_per_px += (target_kpp - self.km_per_px) * 0.05
        self.cam_x += (mid_x - self.cam_x) * 0.05
        self.cam_y += (mid_y - self.cam_y) * 0.05

    def _get_interpolated_state(self, ac_id: str, alpha: float) -> Tuple[float, float, float, float]:
        if ac_id not in self._prev_states or ac_id not in self._curr_states:
            ac = next(a for a in self.all_aircraft if a.aircraft_id == ac_id)
            return ac.x_km, ac.y_km, ac.z_km, ac.heading_deg
        
        p = self._prev_states[ac_id]
        c = self._curr_states[ac_id]
        
        ix = p[0] + (c[0] - p[0]) * alpha
        iy = p[1] + (c[1] - p[1]) * alpha
        iz = p[2] + (c[2] - p[2]) * alpha
        
        p_h, c_h = p[3], c[3]
        diff = (c_h - p_h + 180) % 360 - 180
        ih = (p_h + diff * alpha) % 360
        
        return ix, iy, iz, ih

    def _draw_grid(self, surface: pygame.Surface) -> None:
        grid_km = 50.0
        if self.km_per_px > 1.0:
            grid_km = 100.0
        elif self.km_per_px < 0.1:
            grid_km = 10.0
            
        step_px = _km_to_px(grid_km, self.km_per_px)
        w, h = surface.get_size()
        cx, cy = w // 2, h // 2
        
        # Grid offset based on camera
        ox = int((self.cam_x / self.km_per_px) % step_px)
        oy = int((self.cam_y / self.km_per_px) % step_px)
        
        for x in range((cx - ox) % step_px, w, step_px):
            pygame.draw.line(surface, GRID_COLOR, (x, 0), (x, h), 1)
        for y in range((cy + oy) % step_px, h, step_px):
            pygame.draw.line(surface, GRID_COLOR, (0, y), (w, y), 1)
            
        # Tactical Axis (World 0,0)
        ax, ay = _world_to_screen(0, 0, self.km_per_px, self.cam_x, self.cam_y)
        pygame.draw.line(surface, (30, 45, 70), (ax, 0), (ax, h), 2)
        pygame.draw.line(surface, (30, 45, 70), (0, ay), (w, ay), 2)


def run_pygame(scenario_path: str, seed: int = 42, agent_type: str = "darpa") -> None:
    """Entry point for Pygame display."""
    PygameRenderer(scenario_path, seed, agent_type).run()
