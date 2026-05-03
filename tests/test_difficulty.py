from world.difficulty import difficulty_for_altitude


def test_starting_altitude_uses_easy_params() -> None:
    p = difficulty_for_altitude(altitude_m=0)
    assert p.platforms_per_chunk >= 5
    assert p.hazard_density == 0.0
    assert "yarn" in p.hazard_pool


def test_50m_unlocks_mouse() -> None:
    p = difficulty_for_altitude(altitude_m=50)
    assert "mouse" in p.hazard_pool


def test_150m_unlocks_crow() -> None:
    p = difficulty_for_altitude(altitude_m=150)
    assert "crow" in p.hazard_pool


def test_300m_unlocks_dog_and_spray() -> None:
    p = difficulty_for_altitude(altitude_m=300)
    assert "dog" in p.hazard_pool and "spray" in p.hazard_pool


def test_500m_unlocks_vacuum_and_max_density() -> None:
    p = difficulty_for_altitude(altitude_m=500)
    assert "vacuum" in p.hazard_pool
    assert p.hazard_density >= 0.5


def test_platforms_per_chunk_decreases_monotonically() -> None:
    counts = [difficulty_for_altitude(m).platforms_per_chunk for m in range(0, 600, 50)]
    assert all(b <= a for a, b in zip(counts, counts[1:]))


def test_hazard_density_increases_monotonically() -> None:
    densities = [difficulty_for_altitude(m).hazard_density for m in range(0, 600, 50)]
    assert all(b >= a for a, b in zip(densities, densities[1:]))
