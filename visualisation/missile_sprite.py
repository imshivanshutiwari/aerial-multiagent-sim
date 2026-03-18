"""Missile sprite — draw high-visibility missiles with glow and directional icons."""

from __future__ import annotations

import math
from typing import Tuple

import pygame

# Colors
BLUE_MISSILE = (100, 200, 255)
RED_MISSILE = (255, 120, 60)
TERMINAL_FLASH = (255, 255, 100)


def draw_missile(
    surface: pygame.Surface,
    pos: Tuple[int, int],
    heading_deg: float,
    team: str,
    phase: str,
    t_sec: float,
) -> None:
    """Draw a high-visibility missile with energetic glow and phase indicators."""
    cx, cy = pos
    h = math.radians(heading_deg)
    color = BLUE_MISSILE if team == "Blue" else RED_MISSILE
    
    # 1. Energetic Head Glow
    glow_size = 10
    if phase == "terminal":
        # Pulsing flash for terminal phase
        pulse = (math.sin(t_sec * 15) + 1) * 0.5
        glow_size = 12 + int(pulse * 6)
        if pulse > 0.7:
            color = TERMINAL_FLASH

    glow_surf = pygame.Surface((glow_size * 2, glow_size * 2), pygame.SRCALPHA)
    pygame.draw.circle(glow_surf, (*color, 120), (glow_size, glow_size), glow_size)
    pygame.draw.circle(glow_surf, (*color, 60), (glow_size, glow_size), glow_size // 2)
    surface.blit(glow_surf, (cx - glow_size, cy - glow_size))

    # 2. Missile Body (small rectangle/arrow)
    length = 8
    width = 2
    # End point
    ex = cx + int(length * math.cos(h))
    ey = cy - int(length * math.sin(h))
    pygame.draw.line(surface, (255, 255, 255), (cx, cy), (ex, ey), width)
