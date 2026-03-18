"""Aircraft sprite — draw a small directional triangle for each aircraft."""

from __future__ import annotations

import math
from typing import Tuple

import pygame

# Colours
BLUE_COLOR = (80, 180, 255)
RED_COLOR = (255, 80, 80)
DEAD_COLOR = (120, 120, 120)


def draw_aircraft(
    surface: pygame.Surface,
    pos: Tuple[int, int],
    heading_deg: float,
    team: str,
    is_alive: bool,
    size: int = 14,
    z_km: float = 10.0,
) -> None:
    """Draw a high-fidelity aircraft icon with glow and engine effects."""
    if not is_alive:
        _draw_dead(surface, pos)
        return

    # Scale size based on altitude (higher = larger)
    size = int(size * (0.8 + 0.04 * z_km))

    color = BLUE_COLOR if team == "Blue" else RED_COLOR
    glow_color = (0, 80, 150) if team == "Blue" else (150, 40, 20)
    h = math.radians(heading_deg)
    cx, cy = pos

    # 1. Outer Glow (Aura)
    glow_surf = pygame.Surface((size * 4, size * 4), pygame.SRCALPHA)
    pygame.draw.circle(glow_surf, (*glow_color, 40), (size * 2, size * 2), size * 1.5)
    pygame.draw.circle(glow_surf, (*glow_color, 20), (size * 2, size * 2), size * 2.0)
    surface.blit(glow_surf, (cx - size * 2, cy - size * 2))

    # 2. Stealth-fighter Polygon vertices
    # Nose, wings, rear
    pts = [
        (int(size * 1.2 * math.cos(h)), -int(size * 1.2 * math.sin(h))),  # Nose
        (int(size * 0.8 * math.cos(h + 2.4)), -int(size * 0.8 * math.sin(h + 2.4))), # Wing L
        (int(size * 0.3 * math.cos(h + math.pi)), -int(size * 0.3 * math.sin(h + math.pi))), # Rear notch
        (int(size * 0.8 * math.cos(h - 2.4)), -int(size * 0.8 * math.sin(h - 2.4))), # Wing R
    ]
    # Offset points to center
    poly_pts = [(cx + px, cy + py) for px, py in pts]
    
    # 3. Engine Exhaust Flame (subtle)
    ex_x = cx + int(size * 0.4 * math.cos(h + math.pi))
    ex_y = cy - int(size * 0.4 * math.sin(h + math.pi))
    pygame.draw.circle(surface, (255, 200, 50), (ex_x, ex_y), 3)

    # 4. Draw Main Body
    pygame.draw.polygon(surface, color, poly_pts)
    pygame.draw.polygon(surface, (255, 255, 255), poly_pts, 1) # White outline for crispness


def _draw_dead(surface: pygame.Surface, pos: Tuple[int, int], size: int = 8) -> None:
    """Draw a grey X for a dead aircraft."""
    cx, cy = pos
    pygame.draw.line(surface, DEAD_COLOR, (cx - size, cy - size), (cx + size, cy + size), 2)
    pygame.draw.line(surface, DEAD_COLOR, (cx - size, cy + size), (cx + size, cy - size), 2)
