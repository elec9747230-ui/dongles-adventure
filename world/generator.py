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
    """Pick a variant that doesn't permanently break the climb chain.

    StickyTapePlatform is intentionally excluded — it forbids jumping after
    landing, which can strand the player when it sits between two chain links.
    Disappearing platforms are OK because they grant 1 second to push off.
    """
    candidates = [HammockPlatform]
    if altitude_m >= 50:
        candidates.append(RopePlatform)
    if altitude_m >= 100:
        candidates.append(SwingingPlatform)
    if altitude_m >= 200:
        candidates.append(DisappearingPlatform)
    return rng.choice(candidates)


def generate_chunk(
    *,
    y_start: int,
    difficulty: DifficultyParams,
    rng: random.Random,
    prev_top_y: float | None = None,
    prev_top_x: float | None = None,
) -> Chunk:
    """Generate one chunk above y_start. Guarantees reachable platforms.

    `prev_top_y` / `prev_top_x` describe the highest platform in the previous
    chunk; the first platform in this chunk is constrained to be reachable
    from it (closes the cross-chunk reachability gap).
    """
    y_end = y_start + settings.INTERNAL_HEIGHT
    chunk = Chunk(y_start=y_start, y_end=y_end)

    n = max(2, difficulty.platforms_per_chunk)
    band_h = settings.INTERNAL_HEIGHT / n
    plat_w = 60
    last_x: float | None = prev_top_x  # horizontal reachability anchor
    last_y: float | None = prev_top_y  # vertical reachability anchor

    altitude_m = y_start // settings.PIXELS_PER_METER
    risky_count = round(n * difficulty.risky_platform_ratio)
    risky_indices = set(rng.sample(range(n), risky_count)) if risky_count else set()

    for i in range(n):
        # Initial y candidate inside the chunk's band
        y_local = i * band_h + rng.uniform(0.3 * band_h, 0.7 * band_h)
        y = y_start + y_local

        # Enforce vertical reachability: next platform must be jumpable from last
        if last_y is not None:
            y_max = last_y + settings.VERTICAL_REACH_BUDGET
            y_min = last_y + settings.MIN_VERTICAL_GAP
            if y_max < y_min:
                y_max = y_min  # safety
            y = max(y_min, min(y, y_max))

        # X chosen with horizontal reachability constraint relative to last_x
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
        last_y = y

    # Hazard rolling: up to 2 hazards per chunk, biased toward the most
    # recently unlocked kind so the player meets new threats as they climb.
    pool = difficulty.hazard_pool
    if pool:
        # Weight: linearly higher for later entries (newest unlocked = heaviest).
        weights = [1 + 2 * i for i in range(len(pool))]
        max_count = 2 if difficulty.hazard_density >= 0.6 else 1
        for _ in range(max_count):
            if rng.random() >= difficulty.hazard_density:
                continue
            kind = rng.choices(pool, weights=weights, k=1)[0]
            y = rng.uniform(y_start + 50, y_end - 50)
            chunk.hazard_requests.append((kind, y))

    # Items: ~65% chance per chunk to drop one item, balanced weights
    if rng.random() < 0.65:
        ikind = rng.choices(
            population=["tuna", "feather", "catnip", "fish"],
            weights=[0.40, 0.25, 0.25, 0.10],
            k=1,
        )[0]
        ix = rng.uniform(0, settings.INTERNAL_WIDTH - 24)
        iy = rng.uniform(y_start + 50, y_end - 50)
        chunk.item_requests.append((ikind, ix, iy))

    return chunk
