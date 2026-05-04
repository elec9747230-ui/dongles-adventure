"""Altitude-to-generation-parameter mapping for the cat tower.

This module exposes a pure function that converts the player's current altitude
(in meters) into a bundle of tuning knobs used by the chunk generator. Keeping
the curve here lets game-feel be tuned in one place without touching the
generator's geometry or the entity classes.
"""
from __future__ import annotations

from dataclasses import dataclass

import settings


@dataclass(frozen=True)
class DifficultyParams:
    """Immutable tuning bundle returned by :func:`difficulty_for_altitude`.

    Frozen so it can be safely cached/shared between threads or scenes; the
    chunk generator treats this as a read-only spec.

    Attributes:
        platforms_per_chunk: How many platforms to place inside one chunk.
            Lower values produce sparser, harder-to-traverse chunks.
        risky_platform_ratio: Fraction in [0, 1] of placed platforms that
            should be a non-standard variant (rope, hammock, swinging, etc.).
        hazard_density: Probability in [0, 1] that a single hazard-roll succeeds
            inside a chunk. Combined with the per-chunk roll count to derive
            the expected number of hazards spawned.
        hazard_pool: Tuple of hazard kind identifiers that are currently
            eligible to spawn, gated by altitude unlocks.
    """

    platforms_per_chunk: int     # how many platforms to place in one chunk
    risky_platform_ratio: float  # 0..1: fraction of placed platforms that are non-standard
    hazard_density: float        # 0..1: probability that a hazard spawns in a chunk
    hazard_pool: tuple[str, ...] # which hazard kinds are eligible


def difficulty_for_altitude(altitude_m: int) -> DifficultyParams:
    """Compute the difficulty bundle for the given altitude.

    Args:
        altitude_m: The player's current altitude in meters. Negative values
            are treated like zero by the linear interpolation below (the
            ``min(1.0, ...)`` clamp only handles the upper bound, but ``t``
            never goes below 0 in practice because altitude starts at 0).

    Returns:
        A ``DifficultyParams`` describing how the next chunk should look.
    """

    # Build the eligible hazard pool by progressively unlocking each kind once
    # the player crosses its altitude gate. "yarn" is always present so the
    # very first chunks still have something to dodge.
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

    # Difficulty curve: linear interpolation parameter t in [0, 1] across the
    # first 400 m of climb. Beyond 400 m the curve plateaus (clamp at 1.0)
    # because the vacuum-tier overrides below take over from there.
    t = min(1.0, altitude_m / 400.0)

    # Fewer platforms per chunk as altitude rises: 7 near the ground -> 5 at
    # the plateau. Sparser chunks force longer, riskier jumps.
    platforms_per_chunk = round(7 - 2 * t)            # 7 -> 5
    # Risky-platform variety ramps from 25% to 70%. Starts non-zero so the
    # player encounters non-standard mechanics within the very first minute.
    risky_ratio = 0.25 + 0.45 * t                      # 0.25 -> 0.70 (variety from start)
    # Hazard spawn probability per roll: ~30% near the ground, 80% at the top.
    hazard_density = 0.30 + 0.50 * t

    # Vacuum tier (end-game): force a high-density floor regardless of t,
    # since at this altitude the curve has plateaued and we still want the
    # difficulty to feel oppressive.
    if altitude_m >= settings.HAZARD_GATE_VACUUM:
        hazard_density = max(hazard_density, 0.6)

    return DifficultyParams(
        platforms_per_chunk=platforms_per_chunk,
        risky_platform_ratio=risky_ratio,
        hazard_density=hazard_density,
        hazard_pool=tuple(pool),
    )
