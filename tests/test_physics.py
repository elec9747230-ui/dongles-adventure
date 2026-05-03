from engine.physics import Rect, aabb_overlap, apply_gravity


def test_apply_gravity_decreases_vy_proportional_to_dt() -> None:
    new_vy = apply_gravity(vy=100.0, gravity=1200.0, dt=0.5)
    assert new_vy == 100.0 - 1200.0 * 0.5  # -500.0


def test_apply_gravity_zero_dt_returns_same_vy() -> None:
    assert apply_gravity(vy=42.0, gravity=1200.0, dt=0.0) == 42.0


def test_aabb_overlap_true_when_intersecting() -> None:
    a = Rect(x=0, y=0, w=10, h=10)
    b = Rect(x=5, y=5, w=10, h=10)
    assert aabb_overlap(a, b) is True


def test_aabb_overlap_false_when_only_touching_edges() -> None:
    a = Rect(x=0, y=0, w=10, h=10)
    b = Rect(x=10, y=0, w=10, h=10)
    assert aabb_overlap(a, b) is False


def test_aabb_overlap_false_when_separated() -> None:
    a = Rect(x=0, y=0, w=10, h=10)
    b = Rect(x=20, y=20, w=10, h=10)
    assert aabb_overlap(a, b) is False
