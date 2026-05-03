import random

import settings
from world.difficulty import difficulty_for_altitude
from world.generator import generate_chunk


def test_chunk_is_one_screen_tall() -> None:
    chunk = generate_chunk(y_start=0, difficulty=difficulty_for_altitude(0), rng=random.Random(1))
    assert chunk.y_start == 0
    assert chunk.y_end == settings.INTERNAL_HEIGHT


def test_chunk_has_correct_number_of_platforms() -> None:
    diff = difficulty_for_altitude(0)
    chunk = generate_chunk(y_start=0, difficulty=diff, rng=random.Random(1))
    assert len(chunk.platforms) == diff.platforms_per_chunk


def test_chunk_platforms_are_within_chunk_bounds() -> None:
    chunk = generate_chunk(y_start=540, difficulty=difficulty_for_altitude(50), rng=random.Random(2))
    for plat in chunk.platforms:
        assert 540 <= plat.y < 1080
        assert 0 <= plat.x
        assert plat.x + plat.w <= settings.INTERNAL_WIDTH


def test_chunk_platforms_are_reachable_from_one_below() -> None:
    chunk = generate_chunk(y_start=0, difficulty=difficulty_for_altitude(0), rng=random.Random(3))
    sorted_plats = sorted(chunk.platforms, key=lambda p: p.y)
    for lower, upper in zip(sorted_plats, sorted_plats[1:]):
        # Closest horizontal distance between lower's edge and upper's edge
        dx = max(0.0, max(lower.x - (upper.x + upper.w), upper.x - (lower.x + lower.w)))
        assert dx <= settings.HORIZONTAL_REACH_BUDGET, (
            f"Platforms unreachable: lower y={lower.y} upper y={upper.y} dx={dx}"
        )


def test_chunk_platforms_are_vertically_reachable() -> None:
    """Vertical gap between consecutive platforms must fit within the jump arc."""
    for seed in range(20):
        for altitude_m in (0, 100, 250, 400, 550):
            chunk = generate_chunk(
                y_start=altitude_m * settings.PIXELS_PER_METER,
                difficulty=difficulty_for_altitude(altitude_m),
                rng=random.Random(seed),
            )
            sorted_plats = sorted(chunk.platforms, key=lambda p: p.y)
            for lower, upper in zip(sorted_plats, sorted_plats[1:]):
                dy = upper.y - lower.y
                assert dy <= settings.VERTICAL_REACH_BUDGET + 0.5, (
                    f"Vertical gap {dy:.1f}px > budget {settings.VERTICAL_REACH_BUDGET:.1f}px "
                    f"(seed={seed}, altitude={altitude_m}m)"
                )
                assert dy >= settings.MIN_VERTICAL_GAP - 0.1, (
                    f"Platforms too close (dy={dy:.1f}px) — likely overlap"
                )


def test_chunk_first_platform_reachable_from_prev_chunk_top() -> None:
    """When prev_top_y is supplied, the first platform is jumpable from it."""
    chunk = generate_chunk(
        y_start=540,
        difficulty=difficulty_for_altitude(54),
        rng=random.Random(5),
        prev_top_y=480.0,
    )
    bottom = min(chunk.platforms, key=lambda p: p.y)
    assert bottom.y - 480.0 <= settings.VERTICAL_REACH_BUDGET


def test_chunk_generation_is_deterministic_with_same_seed() -> None:
    diff = difficulty_for_altitude(100)
    a = generate_chunk(y_start=0, difficulty=diff, rng=random.Random(42))
    b = generate_chunk(y_start=0, difficulty=diff, rng=random.Random(42))
    assert [(p.x, p.y) for p in a.platforms] == [(p.x, p.y) for p in b.platforms]


def test_chunk_can_emit_hazard_request_when_density_positive() -> None:
    diff = difficulty_for_altitude(500)  # high density
    rng = random.Random(7)
    seen_hazard = False
    for _ in range(20):
        chunk = generate_chunk(y_start=0, difficulty=diff, rng=rng)
        if chunk.hazard_requests:
            seen_hazard = True
            kind, y = chunk.hazard_requests[0]
            assert kind in diff.hazard_pool
            assert 0 <= y < settings.INTERNAL_HEIGHT
            break
    assert seen_hazard
