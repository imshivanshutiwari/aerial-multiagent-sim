"""Event logging for the BVR simulation.

Every decision and combat event is recorded with:
  timestamp, aircraft_id, team, event_type, detail string, extra dict.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Event:
    """A single logged event."""
    t_sec: float
    actor_id: str
    team: str
    event_type: str
    detail: str
    extra: Dict[str, Any] = field(default_factory=dict)


class EventLogger:
    """Thread-safe-ish event accumulator."""

    def __init__(self) -> None:
        self._events: List[Event] = []

    def log(
        self,
        t_sec: float,
        actor_id: str,
        team: str,
        event_type: str,
        detail: str,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._events.append(Event(
            t_sec=t_sec,
            actor_id=actor_id,
            team=team,
            event_type=event_type,
            detail=detail,
            extra=extra or {},
        ))

    def events(self) -> List[Event]:
        return list(self._events)

    def to_dicts(self) -> List[Dict]:
        return [
            {
                "t": e.t_sec,
                "actor": e.actor_id,
                "team": e.team,
                "type": e.event_type,
                "detail": e.detail,
                **e.extra,
            }
            for e in self._events
        ]

    def clear(self) -> None:
        self._events.clear()
