"""Coordinate transforms between world (km) and screen (pixels)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class CoordinateMapper:
    """Map a rectangular world region to a screen surface.

    Parameters
    ----------
    width_px, height_px:
        Screen size in pixels.
    km_per_px:
        World scale (km per pixel).
    origin_center:
        If True, world origin (0,0) is at screen center. Otherwise top-left.
    """

    width_px: int
    height_px: int
    km_per_px: float = 0.25
    origin_center: bool = True

    @property
    def px_per_km(self) -> float:
        return 1.0 / self.km_per_px

    def world_to_screen(self, x_km: float, y_km: float) -> Tuple[int, int]:
        if self.origin_center:
            cx = self.width_px // 2
            cy = self.height_px // 2
            sx = int(round(cx + x_km * self.px_per_km))
            sy = int(round(cy - y_km * self.px_per_km))
            return sx, sy
        return int(round(x_km * self.px_per_km)), int(round(y_km * self.px_per_km))

    def screen_to_world(self, x_px: int, y_px: int) -> Tuple[float, float]:
        if self.origin_center:
            cx = self.width_px // 2
            cy = self.height_px // 2
            x_km = (x_px - cx) * self.km_per_px
            y_km = (cy - y_px) * self.km_per_px
            return float(x_km), float(y_km)
        return float(x_px * self.km_per_px), float(y_px * self.km_per_px)

