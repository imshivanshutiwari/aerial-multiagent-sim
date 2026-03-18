"""Radar sweep — rotating semi-transparent pie slice."""

from __future__ import annotations

import math
from typing import Tuple

import pygame


class RadarSweep:
    """Rotating radar sweep visualisation.

    A semi-transparent green (Blue) or red (Red) pie slice that rotates
    360 degrees every 4 seconds.
    """

    def __init__(
        self,
        team: str,
        rotation_speed: float = 90.0,  # deg/s → 360° in 4 s
    ) -> None:
        self.team = team
        self.angle_deg: float = 0.0
        self.rotation_speed = rotation_speed
        self.half_width_deg: float = 20.0
        self.alpha: int = 40

    def update(self, dt: float) -> None:
        """Advance the sweep angle."""
        self.angle_deg = (self.angle_deg + self.rotation_speed * dt) % 360.0

    def draw(
        self,
        surface: pygame.Surface,
        center: Tuple[int, int],
        radius_px: int,
    ) -> None:
        """Draw the sweep pie slice."""
        if radius_px < 5:
            return

        color = (0, 255, 140) if self.team == "Blue" else (255, 80, 80)
        glow_color = (0, 100, 60) if self.team == "Blue" else (100, 30, 30)

        # Build polygon points for the pie arc
        cx, cy = center
        start = self.angle_deg - self.half_width_deg
        end = self.angle_deg + self.half_width_deg
        n_pts = 16
        points = [(cx, cy)]
        for i in range(n_pts + 1):
            a = math.radians(start + (end - start) * i / n_pts)
            px = cx + int(radius_px * math.cos(a))
            py = cy - int(radius_px * math.sin(a))
            points.append((px, py))

        # Main sweep Surface
        sweep_surf = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        
        # 1. Subtle glow underlay
        pygame.draw.polygon(sweep_surf, (*glow_color, 20), points)
        
        # 2. Main semi-transparent fill
        pygame.draw.polygon(sweep_surf, (*color, self.alpha), points)
        
        # 3. Leading edge highlight (modern look)
        edge_a = math.radians(self.angle_deg + self.half_width_deg)
        ex = cx + int(radius_px * math.cos(edge_a))
        ey = cy - int(radius_px * math.sin(edge_a))
        pygame.draw.line(sweep_surf, (*color, 200), (cx, cy), (ex, ey), 2)
        
        # 4. Range rings "Ribs" within the sweep
        for r_step in [0.3, 0.6, 0.9]:
            r_px = int(radius_px * r_step)
            pygame.draw.arc(sweep_surf, (*color, 60), 
                            (cx - r_px, cy - r_px, r_px * 2, r_px * 2),
                            math.radians(start), math.radians(end), 1)

        surface.blit(sweep_surf, (0, 0))
