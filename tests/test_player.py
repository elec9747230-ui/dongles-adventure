from entities.player import Player


def make_player() -> Player:
    return Player(start_x=180.0, start_y=0.0)


def test_player_starts_at_initial_position_with_zero_velocity() -> None:
    p = make_player()
    assert (p.x, p.y) == (180.0, 0.0)
    assert (p.vx, p.vy) == (0.0, 0.0)


def test_player_moves_right_when_right_held() -> None:
    p = make_player()
    p.set_input(left_held=False, right_held=True, jump_pressed=False, jump_held=False)
    p.update(dt=0.1)
    assert p.x > 180.0
    assert p.vx > 0


def test_player_left_overrides_right_when_both_held() -> None:
    p = make_player()
    p.set_input(left_held=True, right_held=True, jump_pressed=False, jump_held=False)
    p.update(dt=0.1)
    assert p.vx < 0


def test_player_falls_under_gravity_when_airborne() -> None:
    p = make_player()
    p.grounded = False
    p.update(dt=0.1)
    assert p.vy < 0
    assert p.y < 0


def test_player_jumps_when_grounded_and_jump_pressed() -> None:
    p = make_player()
    p.grounded = True
    p.set_input(left_held=False, right_held=False, jump_pressed=True, jump_held=True)
    p.update(dt=1 / 60)
    assert p.vy > 0
    assert p.grounded is False


def test_player_short_jump_when_jump_released_during_ascent() -> None:
    p = make_player()
    p.grounded = True
    p.set_input(left_held=False, right_held=False, jump_pressed=True, jump_held=True)
    p.update(dt=1 / 60)
    high_vy = p.vy
    p.set_input(left_held=False, right_held=False, jump_pressed=False, jump_held=False)
    p.update(dt=1 / 60)
    assert p.vy <= 240.0
    assert p.vy < high_vy


def test_jump_buffer_triggers_jump_when_landing_within_window() -> None:
    p = make_player()
    p.grounded = False
    p.set_input(left_held=False, right_held=False, jump_pressed=True, jump_held=True)
    p.update(dt=1 / 60)
    assert p.vy <= 0 or p.vy < 520.0
    p.grounded = True
    p.set_input(left_held=False, right_held=False, jump_pressed=False, jump_held=True)
    p.update(dt=1 / 60)
    assert p.vy > 0


def test_coyote_time_allows_jump_shortly_after_leaving_platform() -> None:
    p = make_player()
    p.grounded = True
    p.set_input(left_held=False, right_held=False, jump_pressed=False, jump_held=False)
    p.update(dt=1 / 60)
    p.grounded = False
    p.update(dt=0.05)  # within COYOTE_TIME (0.08s)
    p.set_input(left_held=False, right_held=False, jump_pressed=True, jump_held=True)
    p.update(dt=1 / 60)
    assert p.vy > 0
