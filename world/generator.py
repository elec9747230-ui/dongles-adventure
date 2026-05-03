"""Procedural chunk generation for the cat tower."""
from __future__ import annotations

import random
from dataclasses import dataclass, field

import settings
from entities.platforms import (
    DisappearingPlatform,
    HammockPlatform,
    RopePlatform,
    StandardPlatform,
    StickyTapePlatform,
    SwingingPlatform,
)
from world.difficulty import DifficultyParams


@dataclass
class Chunk:
    y_start: int
    y_end: int
    platforms: list = field(default_factory=list)
    hazard_requests: list[tuple[str, float]] = field(default_factory=list)  # (kind, world_y)
    item_requests: list[tuple[str, float, float]] = field(default_factory=list)  # (kind, x, y)


def _pick_risky_class(altitude_m: int, rng: random.Random):
    candidates = [HammockPlatform]
    if altitude_m >= 50:
        candidates.append(RopePlatform)
    if altitude_m >= 100:
        candidates.append(SwingingPlatform)
    if altitude_m >= 200:
        candidates.append(DisappearingPlatform)
    if altitude_m >= 300:
        candidates.append(StickyTapePlatform)
    return rng.choice(candidates)


def generate_chunk(*, y_start: int, difficulty: DifficultyParams, rng: random.Random) -> Chunk:
    """Generate one chunk above y_start. Guarantees reachable platforms."""
    y_end = y_start + settings.INTERNAL_HEIGHT
    chunk = Chunk(y_start=y_start, y_end=y_end)

    n = max(2, difficulty.platforms_per_chunk)
    band_h = settings.INTERNAL_HEIGHT / n
    plat_w = 60
    last_x: float | None = None

    altitude_m = y_start // settings.PIXELS_PER_METER
    risky_count = round(n * difficulty.risky_platform_ratio)
    risky_indices = set(rng.sample(range(n), risky_count)) if risky_count else set()

    for i in range(n):
        # Y inside the chunk
        y_local = i * band_h + rng.uniform(0.2 * band_h, 0.8 * band_h)
        y = y_start + y_local

        # X chosen with reachability constraint relative to last_x
        if last_x is None:
            x = rng.uniform(0, settings.INTERNAL_WIDTH - plat_w)
        else:
            min_x = max(0.0, last_x - settings.HORIZONTAL_REACH_BUDGET)
            max_x = min(settings.INTERNAL_WIDTH - plat_w, last_x + settings.HORIZONTAL_REACH_BUDGET)
            if max_x < min_x:
                min_x, max_x = 0.0, float(settings.INTERNAL_WIDTH - plat_w)
            x = rng.uniform(min_x, max_x)

        cls = _pick_risky_class(altitude_m, rng) if i in risky_indices else StandardPlatform
        plat = cls(x=x, y=y, w=plat_w, h=8.0)
        chunk.platforms.append(plat)
        last_x = x

    # Hazard rolling
    if difficulty.hazard_pool and rng.random() < difficulty.hazard_density:
        kind = rng.choice(difficulty.hazard_pool)
        y = rng.uniform(y_start + 50, y_end - 50)
        chunk.hazard_requests.append((kind, y))

    # Items: ~50% chance per chunk to drop one item
    if rng.random() < 0.5:
        ikind = rng.choices(
            population=["tuna", "feather", "catnip", "fish"],
            weights=[0.6, 0.2, 0.15, 0.05],
            k=1,
        )[0]
        ix = rng.uniform(0, settings.INTERNAL_WIDTH - 14)
        iy = rng.uniform(y_start + 50, y_end - 50)
        chunk.item_requests.append((ikind, ix, iy))

    return chunk
