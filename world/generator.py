"""Procedural chunk generation for the cat tower.

The world is an infinite vertical scroll: a sequence of fixed-height chunks
stacked end-to-end, each populated independently from a seeded RNG. The
generator's job is to produce a chunk whose platforms are *always* reachable
in sequence — including the very first platform, which must be reachable
from the top of the previous chunk. The reachability invariants encoded
here use the jump-arc budgets derived in ``settings.py``; violating them
would create unwinnable gaps.
"""
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
    """One vertical slice of the tower, produced by :func:`generate_chunk`.

    Hazards and items are returned as deferred *requests* rather than fully
    constructed entities so the scene layer can own their lifecycle (sprites,
    sounds, collision groups) without the generator depending on engine code.

    Attributes:
        y_start: World-space y at the bottom of the chunk (inclusive).
        y_end: World-space y at the top of the chunk (exclusive). Equal to
            ``y_start + INTERNAL_HEIGHT``.
        platforms: Concrete platform instances placed inside this chunk.
        hazard_requests: Pending hazards as ``(kind, world_y)`` tuples for the
            scene to instantiate.
        item_requests: Pending pickups as ``(kind, x, y)`` tuples.
    """

    y_start: int
    y_end: int
    platforms: list = field(default_factory=list)
    hazard_requests: list[tuple[str, float]] = field(default_factory=list)  # (kind, world_y)
    item_requests: list[tuple[str, float, float]] = field(default_factory=list)  # (kind, x, y)


def _pick_risky_class(altitude_m: int, rng: random.Random):
    """Pick a non-standard platform class that won't break the climb chain.

    Args:
        altitude_m: Current altitude; used to gate which variants are eligible
            so the player learns one mechanic at a time.
        rng: Seeded RNG for reproducible picks.

    Returns:
        A platform class (not an instance) to be constructed by the caller.

    Notes:
        StickyTapePlatform is intentionally excluded from this pool. It locks
        the player in place after landing, which — when sandwiched between
        two chain links of the reachability sequence — can strand the player
        on an unrecoverable platform. DisappearingPlatform is acceptable
        because it grants ~1 second to push off before vanishing.
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
    """Generate one chunk above ``y_start`` with guaranteed reachable platforms.

    Args:
        y_start: World-space y of the bottom edge of the new chunk.
        difficulty: Tuning knobs for this chunk (platform count, risky ratio,
            hazard density, hazard pool).
        rng: Seeded ``random.Random`` so chunk content is deterministic per
            run/seed; the scene seeds this from a master seed + chunk index.
        prev_top_y: World-y of the highest platform in the previous chunk, or
            ``None`` for the very first chunk. Used as the vertical anchor
            for the first platform so cross-chunk gaps stay jumpable.
        prev_top_x: X of that same anchor platform, used for horizontal
            reachability.

    Returns:
        A populated :class:`Chunk` ready to be merged into the scene.

    Notes:
        Reachability invariants between consecutive platforms (whether they
        live in the same chunk or span a chunk boundary):

            * vertical:   MIN_VERTICAL_GAP <= dy <= VERTICAL_REACH_BUDGET
            * horizontal: |dx| <= HORIZONTAL_REACH_BUDGET

        These budgets are derived in ``settings.py`` from the jump physics
        with a safety factor (~0.7-0.8) so the player can always *catch* the
        next platform's top, not merely graze it at apex.
    """
    # Each chunk is exactly one screen tall in internal pixels. Keeping a
    # constant chunk height lets the scene preallocate culling bounds.
    y_end = y_start + settings.INTERNAL_HEIGHT
    chunk = Chunk(y_start=y_start, y_end=y_end)

    # Floor of 2 platforms guards against a degenerate difficulty curve where
    # platforms_per_chunk could otherwise drop below the bare minimum needed
    # to connect chunk top to chunk bottom.
    n = max(2, difficulty.platforms_per_chunk)
    band_h = settings.INTERNAL_HEIGHT / n  # vertical band assigned to each platform slot
    plat_w = 60
    last_x: float | None = prev_top_x  # horizontal reachability anchor
    last_y: float | None = prev_top_y  # vertical reachability anchor

    altitude_m = y_start // settings.PIXELS_PER_METER
    # Pick which slots in this chunk get a non-standard (risky) variant.
    # Using sample() over range(n) prevents duplicates and gives a uniform
    # distribution of risky positions per chunk.
    risky_count = round(n * difficulty.risky_platform_ratio)
    risky_indices = set(rng.sample(range(n), risky_count)) if risky_count else set()

    for i in range(n):
        # Initial y candidate inside the platform's vertical band. The 0.3-0.7
        # window keeps platforms away from band edges, which avoids visually
        # stacking neighbors when adjacent bands jitter toward each other.
        y_local = i * band_h + rng.uniform(0.3 * band_h, 0.7 * band_h)
        y = y_start + y_local

        # Enforce the vertical reachability invariant. We clamp y into
        # [last_y + MIN_VERTICAL_GAP, last_y + VERTICAL_REACH_BUDGET] so the
        # next platform is far enough above to feel like progress but still
        # within a single jump's apex.
        if last_y is not None:
            y_max = last_y + settings.VERTICAL_REACH_BUDGET
            y_min = last_y + settings.MIN_VERTICAL_GAP
            if y_max < y_min:
                y_max = y_min  # safety: degenerate budgets collapse to min gap
            y = max(y_min, min(y, y_max))

        # Horizontal placement, also constrained to a jumpable window around
        # last_x. For the first platform of the very first chunk (last_x is
        # None) we allow the full playfield width.
        if last_x is None:
            x = rng.uniform(0, settings.INTERNAL_WIDTH - plat_w)
        else:
            min_x = max(0.0, last_x - settings.HORIZONTAL_REACH_BUDGET)
            max_x = min(settings.INTERNAL_WIDTH - plat_w, last_x + settings.HORIZONTAL_REACH_BUDGET)
            # If the reachability window has been pushed off-canvas (would
            # only happen with extreme tuning), fall back to the full row.
            if max_x < min_x:
                min_x, max_x = 0.0, float(settings.INTERNAL_WIDTH - plat_w)
            x = rng.uniform(min_x, max_x)

        cls = _pick_risky_class(altitude_m, rng) if i in risky_indices else StandardPlatform
        plat = cls(x=x, y=y, w=plat_w, h=8.0)
        chunk.platforms.append(plat)
        last_x = x
        last_y = y

    # Hazard rolling: up to 2 hazards per chunk (only at high density), biased
    # toward the most recently unlocked kind so newly introduced threats get
    # screen time before older ones blend back in.
    pool = difficulty.hazard_pool
    if pool:
        # Linear weights 1, 3, 5, ... — newest entry is heaviest. The exact
        # multiplier is a tuning choice; doubling+1 keeps the bias noticeable
        # without completely starving older kinds.
        weights = [1 + 2 * i for i in range(len(pool))]
        max_count = 2 if difficulty.hazard_density >= 0.6 else 1
        for _ in range(max_count):
            # Each slot is an independent Bernoulli trial against hazard_density.
            if rng.random() >= difficulty.hazard_density:
                continue
            kind = rng.choices(pool, weights=weights, k=1)[0]
            # 50px margin from the chunk edges keeps hazards away from the
            # platform-band boundaries where culling and stitching happen.
            y = rng.uniform(y_start + 50, y_end - 50)
            chunk.hazard_requests.append((kind, y))

    # Item drops: a single ~65% chance per chunk. Tuna is the most common
    # because it's the score/economy currency; fish is rarest because it's
    # the strongest power-up.
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
