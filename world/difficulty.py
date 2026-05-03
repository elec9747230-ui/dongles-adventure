"""Altitude -> generation parameter mapping."""
from __future__ import annotations

from dataclasses import dataclass

import settings


@dataclass(frozen=True)
class DifficultyParams:
    platforms_per_chunk: int     # how many platforms to place in one chunk
    risky_platform_ratio: float  # 0..1: fraction of placed platforms that are non-standard
    hazard_density: float        # 0..1: probability that a hazard spawns in a chunk
    hazard_pool: tuple[str, ...] # which hazard kinds are eligible


def difficulty_for_altitude(altitude_m: int) -> DifficultyParams:
    pool: list[str] = ["yarn"]
    if altitude_m >= settings.HAZARD_GATE_MOUSE:
        pool.append("mouse")
    if altitude_m >= settings.HAZARD_GATE_CROW:
        pool.append("crow")
    if altitude_m >= settings.HAZARD_GATE_DOG:
        pool.append("dog")
    if altitude_m >= settings.HAZARD_GATE_SPRAY:
        pool.append("spray")
    if altitude_m >= settings.HAZARD_GATE_VACUUM:
        pool.append("vacuum")

    # Linear interpolation across 0..500m, clamped beyond.
    t = min(1.0, altitude_m / 500.0)

    platforms_per_chunk = round(7 - 2 * t)            # 7 -> 5
    risky_ratio = 0.25 + 0.45 * t                      # 0.25 -> 0.70 (variety from start)
    hazard_density = 0.0 + 0.6 * t                     # 0.0 -> 0.6

    # 500m+ guarantees vacuum hazard density floor of 0.5
    if altitude_m >= settings.HAZARD_GATE_VACUUM:
        hazard_density = max(hazard_density, 0.5)

    return DifficultyParams(
        platforms_per_chunk=platforms_per_chunk,
        risky_platform_ratio=risky_ratio,
        hazard_density=hazard_density,
        hazard_pool=tuple(pool),
    )
