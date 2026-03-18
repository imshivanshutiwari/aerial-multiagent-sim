"""Threat assessment for BVR AI agents.

For each detected enemy, compute:
    threat_score = (1 / range_km) * enemy_missiles * (1 if tracking_me else 0.3)

Sort descending; top entry = primary threat.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from engine.aircraft import Aircraft
from engine.physics import distance_km


@dataclass
class ThreatEntry:
    """One assessed threat."""
    target_id: str
    range_km: float
    threat_score: float
    enemy_missiles: int
    is_tracking_me: bool
    tracking_quality: float


def assess_threats(
    own: Aircraft,
    detected_enemies: List[Aircraft],
    enemy_tracking_me: Dict[str, bool],
) -> List[ThreatEntry]:
    """Assess detected enemies and return a sorted threat list.

    Parameters
    ----------
    own : Aircraft
        The assessing aircraft.
    detected_enemies : list[Aircraft]
        Enemies detected by the aircraft's radar.
    enemy_tracking_me : dict[str, bool]
        For each enemy ID, whether that enemy's radar is tracking *own*.

    Returns
    -------
    list[ThreatEntry]
        Sorted by threat_score descending.
    """
    entries: List[ThreatEntry] = []
    for e in detected_enemies:
        r = max(0.1, distance_km(own.x_km, own.y_km, own.z_km, e.x_km, e.y_km, e.z_km))
        tracking_me = enemy_tracking_me.get(e.aircraft_id, False)
        score = (1.0 / r) * e.missiles_remaining * (1.0 if tracking_me else 0.3)
        entries.append(ThreatEntry(
            target_id=e.aircraft_id,
            range_km=r,
            threat_score=score,
            enemy_missiles=e.missiles_remaining,
            is_tracking_me=tracking_me,
            tracking_quality=0.0,
        ))
    entries.sort(key=lambda t: t.threat_score, reverse=True)
    return entries
