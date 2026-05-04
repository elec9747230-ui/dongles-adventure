"""Compute the next upcoming hazard tier above the player's current altitude.

Used by the HUD to telegraph the next gameplay surprise ("next: Crow at 60m")
so the player has a beat of anticipation before encountering a new mechanic.
"""
from __future__ import annotations

import settings

# Ordered list of (gate_altitude_m, display_label). Order matters: the lookup
# walks this list in ascending altitude and returns the first unmet gate, so
# entries must be sorted ascending by altitude.
_HAZARDS = [
    (settings.HAZARD_GATE_YARN, "Yarn"),
    (settings.HAZARD_GATE_MOUSE, "Mouse"),
    (settings.HAZARD_GATE_CROW, "Crow"),
    (settings.HAZARD_GATE_DOG, "Dog"),
    (settings.HAZARD_GATE_VACUUM, "Vacuum"),
]


def next_hazard(altitude_m: int) -> tuple[str, int]:
    """Return ``(label, gate_m)`` of the next hazard tier not yet unlocked.

    Args:
        altitude_m: Current altitude in meters.

    Returns:
        A tuple of the upcoming hazard's display label and its unlock altitude.
        If the player has already passed every gate, returns ``("All", -1)``
        as a sentinel the HUD renders as "All hazards unlocked".
    """
    for gate_m, label in _HAZARDS:
        if altitude_m < gate_m:
            return (label, gate_m)
    return ("All", -1)
