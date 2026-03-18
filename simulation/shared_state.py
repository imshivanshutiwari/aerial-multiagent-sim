"""Shared state passed into agent decision loops."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

import numpy as np

from ai.deconfliction import AssignmentBook
from simulation.event_logger import EventLogger


@dataclass
class SharedState:
    """Mutable shared state for one simulation run."""

    rng: np.random.Generator
    logger: EventLogger
    assignments_blue: AssignmentBook = field(default_factory=AssignmentBook)
    assignments_red: AssignmentBook = field(default_factory=AssignmentBook)

    # Cache of latest detections/tracking per actor per target for analysis/visuals
    detections: Dict[str, List[str]] = field(default_factory=dict)  # actor_id -> list of detected target_ids
    tracking_quality: Dict[str, Dict[str, float]] = field(default_factory=dict)  # actor_id -> (target_id -> q)

