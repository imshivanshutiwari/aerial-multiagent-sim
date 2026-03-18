"""HUD overlay — heads-up display for the Pygame tactical window.

Top-left: scenario name, simulated time, speed multiplier.
Top-right: scrolling event log (last 10 events, colour-coded).
Bottom-center: score "BLUE: X kills | RED: Y kills".
Bottom-left: Blue force status rows.
"""

from __future__ import annotations

from typing import List, Tuple

import pygame

from engine.aircraft import Aircraft


# Colours
WHITE = (255, 255, 255)
CYAN = (80, 255, 255)
ORANGE = (255, 160, 40)
BLUE = (80, 180, 255)
GREEN = (80, 255, 80)
GREY = (160, 160, 160)
RED = (255, 50, 50)

# Layout constants
MARGIN = 50
LINE_SPACING = 24


class HUD:
    """Heads-up display overlay."""

    def __init__(self, font: pygame.font.Font) -> None:
        self.font = font

    def draw(
        self,
        surface: pygame.Surface,
        scenario_name: str,
        t_sec: float,
        speed_mult: int,
        paused: bool,
        blue_kills: int,
        red_kills: int,
        blue_aircraft: List[Aircraft],
        event_log: List[dict],
    ) -> None:
        w, h = surface.get_size()

        # ---- Background Panels (Tactical UI look) ----
        # Top-left panel
        tl_surf = pygame.Surface((300, 100), pygame.SRCALPHA)
        pygame.draw.rect(tl_surf, (10, 20, 40, 160), (0, 0, 300, 100), border_radius=8)
        surface.blit(tl_surf, (MARGIN - 10, MARGIN - 10))

        # Top-right panel (Event Log)
        tr_surf = pygame.Surface((560, 240), pygame.SRCALPHA)
        pygame.draw.rect(tr_surf, (10, 20, 40, 160), (0, 0, 560, 240), border_radius=8)
        surface.blit(tr_surf, (w - 540 - MARGIN - 10, MARGIN - 10))

        # Bottom-left panel (Status)
        bl_surf = pygame.Surface((320, 200), pygame.SRCALPHA)
        pygame.draw.rect(bl_surf, (10, 20, 40, 160), (0, 0, 320, 200), border_radius=8)
        surface.blit(bl_surf, (MARGIN - 10, h - MARGIN - 210))

        # ---- Top-left: scenario info ----
        lines = [
            f">> {scenario_name}",
            f"SYSTEM TIME: {t_sec:7.1f} s",
            f"SIM SPEED : {speed_mult}x" + (" (PAUSED)" if paused else ""),
        ]
        y = MARGIN
        for line in lines:
            surface.blit(self.font.render(line, True, CYAN), (MARGIN, y))
            y += LINE_SPACING

        # ---- Top-right: event log (last 10) ----
        x0 = w - 540 - MARGIN
        y0 = MARGIN
        recent = event_log[-10:]
        for ev in recent:
            team = ev.get("team", "")
            etype = ev.get("type", "")
            c = WHITE if etype == "KILL" else (BLUE if team == "Blue" else ORANGE)
            line = f"[{ev.get('t', 0):6.1f}] {ev.get('actor', '')} {etype}"
            surface.blit(self.font.render(line, True, c), (x0, y0))
            y0 += 20

        # ---- Center-bottom: Force Status ----
        blue_alive = sum(1 for a in blue_aircraft if a.is_alive)
        red_count = len([ev for ev in event_log if ev.get("team") == "Red"]) # No, simpler
        # We don't have red_aircraft passed here. Let's just use the kills.
        score_text = f"BLUE: {blue_alive} ALIVE | RED KILLS: {blue_kills} | BLUE KILLS: {red_kills}"
        score_img = self.font.render(score_text, True, WHITE)
        srect = score_img.get_rect()
        srect.midbottom = (w // 2, h - MARGIN)
        
        # Background for score
        bg_rect = srect.inflate(40, 10)
        s_bg = pygame.Surface(bg_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(s_bg, (20, 30, 60, 200), (0, 0, *bg_rect.size), border_radius=4)
        surface.blit(s_bg, bg_rect.topleft)
        surface.blit(score_img, srect)

        # ---- Bottom-left: Blue status ----
        y0 = h - MARGIN - 10 - LINE_SPACING * len(blue_aircraft)
        surface.blit(self.font.render("--- BLUE SQUADRON STATUS ---", True, BLUE), (MARGIN, y0))
        y0 += LINE_SPACING
        for ac in blue_aircraft:
            status = "KIA" if not ac.is_alive else ("DEF" if ac.defensive_manoeuvre_active else "ACT")
            
            # RWR Status Color
            rwr = ac.rwr_status
            rwr_color = GREEN if rwr == "OFF" else (CYAN if rwr == "SEARCH" else (ORANGE if rwr == "LOCK" else RED))
            
            # Missile indicators
            m_rem = ac.missiles_remaining
            m_str = "█" * m_rem + "░" * (4 - m_rem)
            line = f"{ac.aircraft_id:6} [{m_str}] {status}  RWR: {rwr}"
            
            main_color = GREY if not ac.is_alive else (GREEN if status == "ACT" else ORANGE)
            surface.blit(self.font.render(line, True, main_color), (MARGIN, y0))
            
            # Draw a small indicator if LOCK or MISSILE
            if ac.is_alive and rwr in ["LOCK", "MISSILE"]:
                warn_text = " !! LOCK !!" if rwr == "LOCK" else " !! MISSILE !!"
                surface.blit(self.font.render(warn_text, True, rwr_color), (MARGIN + 220, y0))
            
            y0 += 18
