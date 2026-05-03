from entities.platforms import StandardPlatform, resolve_landings
from entities.player import Player


def test_player_falling_lands_on_platform_below() -> None:
    p = Player(start_x=100.0, start_y=20.0)  # bottom at y=20
    p.vy = -100.0  # descending
    p.grounded = False
    plat = StandardPlatform(x=80.0, y=10.0, w=60.0, h=8.0)  # top at y=18
    prev_bottom = p.y
    p.y = 15.0  # moved down past platform top
    resolve_landings(p, [plat], prev_bottom_y=prev_bottom)
    assert p.grounded is True
    assert p.vy == 0.0
    assert p.y == plat.top  # snapped


def test_player_rising_through_platform_does_not_land() -> None:
    p = Player(start_x=100.0, start_y=12.0)
    p.vy = 200.0  # rising
    p.grounded = False
    plat = StandardPlatform(x=80.0, y=10.0, w=60.0, h=8.0)  # top at 18
    prev_bottom = p.y
    p.y = 20.0
    resolve_landings(p, [plat], prev_bottom_y=prev_bottom)
    assert p.grounded is False


def test_player_misses_platform_when_offset_horizontally() -> None:
    p = Player(start_x=300.0, start_y=20.0)
    p.vy = -100.0
    p.grounded = False
    plat = StandardPlatform(x=80.0, y=10.0, w=60.0, h=8.0)
    prev_bottom = p.y
    p.y = 15.0
    resolve_landings(p, [plat], prev_bottom_y=prev_bottom)
    assert p.grounded is False
