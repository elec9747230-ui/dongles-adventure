"""Compute the next upcoming hazard above the current altitude."""
from __future__ import annotations

import settings

_HAZARDS = [
    (settings.HAZARD_GATE_YARN, "Yarn"),
    (settings.HAZARD_GATE_MOUSE, "Mouse"),
    (settings.HAZARD_GATE_CROW, "Crow"),
    (settings.HAZARD_GATE_DOG, "Dog"),
    (settings.HAZARD_GATE_VACUUM, "Vacuum"),
]


def next_hazard(altitude_m: int) -> tuple[str, int]:
    """Return (label, altitude_m) of the next hazard not yet unlocked.

    If all hazards are unlocked, returns ("All", -1).
    """
    for gate_m, label in _HAZARDS:
        if altitude_m < gate_m:
            return (label, gate_m)
    return ("All", -1)
