"""Visual effects for intercept success events (non-lethal)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

import pygame

from visualisation import colors


@dataclass
class Pulse:
    """Expanding ring pulse effect."""

    center_px: Tuple[int, int]
    max_radius_px: int
    color_rgb: Tuple[int, int, int]
    duration_sec: float = 0.6
    t: float = 0.0

    def update(self, dt: float) -> None:
        self.t += max(0.0, dt)

    @property
    def alive(self) -> bool:
        return self.t < self.duration_sec

    def draw(self, surface: pygame.Surface) -> None:
        if not self.alive:
            return
        frac = self.t / self.duration_sec
        radius = int(1 + frac * self.max_radius_px)
        alpha = int(255 * (1.0 - frac))
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        pygame.draw.circle(overlay, (*self.color_rgb, alpha), self.center_px, radius, width=2)
        surface.blit(overlay, (0, 0))

