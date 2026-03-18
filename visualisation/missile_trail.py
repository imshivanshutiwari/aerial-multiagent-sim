"""Missile trail — stores last 20 positions and draws fading dots."""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Dict, Tuple

import pygame


class MissileTrail:
    """Track and draw fading missile trails.

    Each missile stores up to 20 historical screen positions.
    Dots are drawn with alpha fading from 255 (newest) to 0 (oldest).
    """

    def __init__(self, max_len: int = 20) -> None:
        self.max_len = max_len
        self._trails: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_len))

    def update(self, missile_id: str, screen_pos: Tuple[int, int]) -> None:
        """Record a new position for a missile."""
        self._trails[missile_id].append(screen_pos)

    def draw(
        self,
        surface: pygame.Surface,
        missile_id: str,
        team: str,
    ) -> None:
        """Draw a smokey, expanding trail for a missile."""
        trail = self._trails.get(missile_id)
        if not trail:
            return

        # Smoke is generally greyish-white
        smoke_color = (200, 200, 210)
        n = len(trail)
        for i, (x, y) in enumerate(trail):
            # Alpha fades as we go further back
            alpha = int(120 * (i + 1) / n)
            # Size expands as smoke dissipates
            r = 2 + int(6 * (n - i) / n)
            
            # Draw a blurred smoke "puff"
            puff = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(puff, (*smoke_color, alpha), (r, r), r)
            surface.blit(puff, (x - r, y - r))

    def remove(self, missile_id: str) -> None:
        """Remove trail data for a missile that's no longer active."""
        self._trails.pop(missile_id, None)

    def active_ids(self):
        return set(self._trails.keys())
