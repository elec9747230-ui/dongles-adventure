"""Draws Dongle's body — a small white Persian cat.

Single seam for swapping placeholder primitives for real sprite sheets later.
All callers go through `draw_player`. Kept stable in size to avoid the
pulsing/jittery look from earlier dynamic squash/stretch.
"""
from __future__ import annotations

import pygame

import settings


def _facing(player) -> int:  # noqa: ANN001
    """Return -1 (left) or +1 (right) based on velocity, with stickiness."""
    if player.vx < -1:
        return -1
    if player.vx > 1:
        return 1
    return getattr(player, "_last_facing", 1)


def draw_player(surface: pygame.Surface, player, camera) -> None:  # noqa: ANN001
    # i-frame blink: skip every other 0.15s window so the cat flashes
    if player.iframe_timer > 0:
        if int(player.iframe_timer * 6.7) % 2 == 0:
            return

    facing = _facing(player)
    player._last_facing = facing  # type: ignore[attr-defined]

    w = settings.PLAYER_WIDTH
    h = settings.PLAYER_HEIGHT
    screen_y_top = int(camera.world_to_screen_y(player.y + h))
    rect_x = int(player.x)

    # Body: rounded ellipse on bottom, head sphere on top
    body_rect = pygame.Rect(rect_x + 2, screen_y_top + h // 3, w - 4, (2 * h) // 3)
    pygame.draw.ellipse(surface, settings.COLOR_PLAYER, body_rect)
    pygame.draw.ellipse(surface, (215, 215, 215), body_rect.inflate(-4, -4))

    head_r = h // 3
    head_cx = rect_x + w // 2
    head_cy = screen_y_top + head_r + 2
    pygame.draw.circle(surface, settings.COLOR_PLAYER, (head_cx, head_cy), head_r)
    pygame.draw.circle(surface, (215, 215, 215), (head_cx, head_cy), head_r - 2)

    # Ears (two pointed triangles on the head)
    ear_h = head_r
    pygame.draw.polygon(
        surface, settings.COLOR_PLAYER,
        [
            (head_cx - head_r + 2, head_cy - head_r // 2),
            (head_cx - head_r // 2, head_cy - head_r - ear_h // 2),
            (head_cx - 2, head_cy - head_r // 2),
        ],
    )
    pygame.draw.polygon(
        surface, settings.COLOR_PLAYER,
        [
            (head_cx + head_r - 2, head_cy - head_r // 2),
            (head_cx + head_r // 2, head_cy - head_r - ear_h // 2),
            (head_cx + 2, head_cy - head_r // 2),
        ],
    )
    # Pink inner ears
    pygame.draw.polygon(
        surface, (240, 180, 200),
        [
            (head_cx - head_r + 4, head_cy - head_r // 2 - 1),
            (head_cx - head_r // 2, head_cy - head_r - ear_h // 4),
            (head_cx - 4, head_cy - head_r // 2 - 1),
        ],
    )
    pygame.draw.polygon(
        surface, (240, 180, 200),
        [
            (head_cx + head_r - 4, head_cy - head_r // 2 - 1),
            (head_cx + head_r // 2, head_cy - head_r - ear_h // 4),
            (head_cx + 4, head_cy - head_r // 2 - 1),
        ],
    )

    # Eyes: two dots, slightly offset by facing
    eye_dx = 2 * facing
    eye_y = head_cy - 1
    pygame.draw.circle(surface, (40, 40, 60), (head_cx - 4 + eye_dx, eye_y), 2)
    pygame.draw.circle(surface, (40, 40, 60), (head_cx + 4 + eye_dx, eye_y), 2)

    # Tiny pink nose
    pygame.draw.circle(surface, (240, 150, 170), (head_cx, head_cy + 3), 1)
