"""Trails for moving objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Deque, Dict, List, Tuple
from collections import deque

import pygame


@dataclass
class Trail:
    """Fixed-length fading dot trail."""

    max_len: int = 20
    points: Deque[Tuple[int, int]] = field(default_factory=lambda: deque(maxlen=20))

    def push(self, p: Tuple[int, int]) -> None:
        self.points.append(p)

    def draw(self, surface: pygame.Surface, color_rgb: Tuple[int, int, int]) -> None:
        if not self.points:
            return
        n = len(self.points)
        for i, (x, y) in enumerate(self.points):
            alpha = int(255 * (i + 1) / n)
            r = 2 if i < n - 1 else 3
            dot = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
            pygame.draw.circle(dot, (*color_rgb, alpha), (r + 1, r + 1), r)
            surface.blit(dot, (x - r - 1, y - r - 1))


class TrailManager:
    """Manage trails keyed by entity id."""

    def __init__(self, max_len: int = 20) -> None:
        self.max_len = max_len
        self._trails: Dict[str, Trail] = {}

    def update(self, entity_id: str, pos_px: Tuple[int, int]) -> None:
        tr = self._trails.get(entity_id)
        if tr is None:
            tr = Trail(max_len=self.max_len, points=deque(maxlen=self.max_len))
            self._trails[entity_id] = tr
        tr.push(pos_px)

    def draw(self, surface: pygame.Surface, entity_id: str, color_rgb: Tuple[int, int, int]) -> None:
        tr = self._trails.get(entity_id)
        if tr is None:
            return
        tr.draw(surface, color_rgb)

