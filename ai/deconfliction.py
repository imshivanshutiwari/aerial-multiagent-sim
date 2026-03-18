"""Missile deconfliction — prevent multiple friendlies targeting the same enemy.

Maintains a simple booking ledger per team.
"""

from __future__ import annotations

from typing import Dict, Optional


class Deconfliction:
    """Track which aircraft has been assigned to which target.

    Only one friendly missile should be in-flight against each enemy at a time
    (unless the first missile has missed or been defeated).
    """

    def __init__(self) -> None:
        # target_id → shooter_aircraft_id
        self._assignments: Dict[str, str] = {}

    def is_target_assigned(self, target_id: str) -> bool:
        return target_id in self._assignments

    def assigned_shooter(self, target_id: str) -> Optional[str]:
        return self._assignments.get(target_id)

    def assign(self, shooter_id: str, target_id: str) -> None:
        self._assignments[target_id] = shooter_id

    def release(self, target_id: str) -> None:
        self._assignments.pop(target_id, None)

    def release_by_shooter(self, shooter_id: str) -> None:
        to_remove = [t for t, s in self._assignments.items() if s == shooter_id]
        for t in to_remove:
            del self._assignments[t]

    def all_assignments(self) -> Dict[str, str]:
        return dict(self._assignments)
