"""Electronic Counter-Measures (ECM) system for BVR Combat Simulation.

Each aircraft carries:
- A **jammer** that reduces enemy radar effective R_max by 40%.
  Limited to 60 seconds of continuous use.
- **Chaff** dispensers (6 rounds).  When dispensed against a terminal-phase
  missile, there is a 35% probability of breaking the missile's radar lock.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class ECMSystem:
    """Electronic counter-measures carried by a single aircraft.

    Parameters
    ----------
    jammer_energy_remaining_sec : float
        Remaining jammer on-time in seconds (initial 60).
    chaff_count : int
        Number of chaff cartridges remaining (initial 6).
    jammer_active : bool
        Whether the jammer is currently emitting.
    chaff_success_probability : float
        Probability a single chaff dispense breaks a missile lock (0.35).
    """

    jammer_energy_remaining_sec: float = 60.0
    chaff_count: int = 6
    jammer_active: bool = False
    chaff_success_probability: float = 0.35

    # ------------------------------------------------------------------
    # Jammer
    # ------------------------------------------------------------------
    def activate_jammer(self) -> None:
        """Activate the jammer if energy remains."""
        if self.jammer_energy_remaining_sec > 0:
            self.jammer_active = True

    def deactivate_jammer(self) -> None:
        """Deactivate the jammer."""
        self.jammer_active = False

    # ------------------------------------------------------------------
    # Chaff
    # ------------------------------------------------------------------
    def dispense_chaff(self) -> bool:
        """Dispense one chaff cartridge.

        Returns
        -------
        bool
            True if a cartridge was available and dispensed.
        """
        if self.chaff_count > 0:
            self.chaff_count -= 1
            return True
        return False

    def chaff_success(self, rng: np.random.Generator) -> bool:
        """Roll for chaff effectiveness.

        Returns
        -------
        bool
            True if the chaff successfully breaks a missile lock.
        """
        return bool(rng.random() < self.chaff_success_probability)

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------
    def update(self, dt: float) -> None:
        """Drain jammer energy over *dt* seconds."""
        if self.jammer_active:
            self.jammer_energy_remaining_sec -= dt
            if self.jammer_energy_remaining_sec <= 0:
                self.jammer_energy_remaining_sec = 0.0
                self.jammer_active = False
