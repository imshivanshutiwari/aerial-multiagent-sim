"""Explosion effect — expanding ring for missile detonation.

- Kill: bright white flash expanding to 100 m radius over 0.5 s, then fade.
- Miss: smaller grey puff.
"""

from __future__ import annotations

from typing import Tuple

import pygame


class Explosion:
    """Visual explosion effect at a screen position.

    Parameters
    ----------
    pos : Tuple[int, int]
        Screen position.
    is_kill : bool
        True = bright white expanding ring. False = grey puff.
    max_radius : int
        Maximum radius in pixels.
    duration : float
        Time in seconds for full expansion.
    """

    def __init__(
        self,
        pos: Tuple[int, int],
        is_kill: bool = True,
        max_radius: int = 30,
        duration: float = 0.5,
    ) -> None:
        self.pos = pos
        self.is_kill = is_kill
        self.max_radius = max_radius if is_kill else max_radius // 3
        self.duration = duration
        self.elapsed: float = 0.0
        self.alive: bool = True

    def update(self, dt: float) -> None:
        """Advance the explosion animation."""
        self.elapsed += dt
        if self.elapsed >= self.duration:
            self.alive = False

    def draw(self, surface: pygame.Surface) -> None:
        """Draw the high-fidelity explosion effect."""
        if not self.alive:
            return
        t = min(1.0, self.elapsed / self.duration)
        
        # 1. Radiant Core (bright white)
        if self.is_kill and t < 0.6:
            core_r = max(1, int(self.max_radius * 0.4 * (1.0 - t)))
            core_alpha = int(255 * (0.6 - t) / 0.6)
            core_surf = pygame.Surface((core_r * 2, core_r * 2), pygame.SRCALPHA)
            pygame.draw.circle(core_surf, (255, 255, 220, core_alpha), (core_r, core_r), core_r)
            surface.blit(core_surf, (self.pos[0] - core_r, self.pos[1] - core_r))

        # 2. Expanding Shockwave Ring
        radius = max(1, int(self.max_radius * t))
        alpha = int(180 * (1.0 - t))
        
        ring_surf = pygame.Surface((radius * 2 + 10, radius * 2 + 10), pygame.SRCALPHA)
        if self.is_kill:
            # Heat-orange ring
            color = (255, 100, 20, alpha)
            pygame.draw.circle(ring_surf, color, (radius + 5, radius + 5), radius, 3)
            # Inner white ring
            pygame.draw.circle(ring_surf, (255, 255, 255, alpha // 2), (radius + 5, radius + 5), radius - 2, 1)
        else:
            # Subtle grey puff for miss
            color = (160, 160, 170, alpha)
            pygame.draw.circle(ring_surf, color, (radius + 5, radius + 5), radius, 2)
            
        surface.blit(ring_surf, (self.pos[0] - radius - 5, self.pos[1] - radius - 5))
