from engine.camera import Camera


def test_camera_initial_y_top_is_screen_height() -> None:
    cam = Camera(screen_height=540, player_offset_from_top=324)
    cam.follow(player_world_y=0.0)
    assert cam.y_top == 324.0  # 0 + 324 (player's screen_y target)


def test_camera_y_top_increases_when_player_climbs() -> None:
    cam = Camera(screen_height=540, player_offset_from_top=324)
    cam.follow(player_world_y=0.0)
    cam.follow(player_world_y=200.0)
    assert cam.y_top == 524.0  # 200 + 324


def test_camera_y_top_never_decreases_when_player_falls() -> None:
    cam = Camera(screen_height=540, player_offset_from_top=324)
    cam.follow(player_world_y=500.0)
    high = cam.y_top
    cam.follow(player_world_y=100.0)
    assert cam.y_top == high


def test_world_to_screen_y_inverts_axis() -> None:
    cam = Camera(screen_height=540, player_offset_from_top=324)
    cam.follow(player_world_y=0.0)  # y_top = 324
    assert cam.world_to_screen_y(0.0) == 324.0
    assert cam.world_to_screen_y(324.0) == 0.0


def test_is_below_screen_when_world_y_more_than_screen_height_below_top() -> None:
    cam = Camera(screen_height=540, player_offset_from_top=324)
    cam.follow(player_world_y=0.0)  # y_top = 324; bottom = 324 - 540 = -216
    assert cam.is_below_screen(world_y=-217.0) is True
    assert cam.is_below_screen(world_y=-216.0) is False
