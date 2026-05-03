"""Draws Dongle's body in one of five states: idle / run / jump / fall / hurt.

This file is the single seam that swaps placeholder primitives for real
sprite sheets later. All callers go through `draw_player`.
"""
from __future__ import annotations

import math

import pygame

import settings


def _state(player) -> str:  # noqa: ANN001
    if player.iframe_timer > 0:
        return "hurt"
    if not player.grounded:
        return "jump" if player.vy > 0 else "fall"
    if abs(player.vx) > 0.1:
        return "run"
    return "idle"


def draw_player(surface: pygame.Surface, player, camera) -> None:  # noqa: ANN001
    state = _state(player)

    # i-frame blink: skip drawing every other 0.1s window
    if state == "hurt":
        blink_phase = int(player.iframe_timer * 10) % 2
        if blink_phase == 0:
            return

    # Squash/stretch hint for jump/fall
    w = settings.PLAYER_WIDTH
    h = settings.PLAYER_HEIGHT
    if state == "jump":
        w = int(w * 0.85)
        h = int(h * 1.15)
    elif state == "fall":
        w = int(w * 1.10)
        h = int(h * 0.90)

    screen_y_top = camera.world_to_screen_y(player.y + h)
    rect_x = int(player.x + (settings.PLAYER_WIDTH - w) / 2)

    # Body: white Persian cat (rounded body)
    body = pygame.Rect(rect_x, int(screen_y_top), w, h)
    pygame.draw.ellipse(surface, settings.COLOR_PLAYER, body)
    # Inner shadow
    pygame.draw.ellipse(surface, (210, 210, 210), body.inflate(-6, -6))

    # Two ear triangles
    ear_h = h // 4
    pygame.draw.polygon(
        surface, settings.COLOR_PLAYER,
        [
            (rect_x + 4, int(screen_y_top + 6)),
            (rect_x + 4, int(screen_y_top - ear_h + 6)),
            (rect_x + 4 + ear_h, int(screen_y_top + 6)),
        ],
    )
    pygame.draw.polygon(
        surface, settings.COLOR_PLAYER,
        [
            (rect_x + w - 4, int(screen_y_top + 6)),
            (rect_x + w - 4, int(screen_y_top - ear_h + 6)),
            (rect_x + w - 4 - ear_h, int(screen_y_top + 6)),
        ],
    )

    # Eyes (two dots) — facing direction reflected by horizontal velocity
    eye_offset = 4 if player.vx >= 0 else -4
    eye_y = int(screen_y_top + h // 3)
    pygame.draw.circle(surface, (40, 40, 60), (rect_x + w // 2 - 5 + eye_offset, eye_y), 2)
    pygame.draw.circle(surface, (40, 40, 60), (rect_x + w // 2 + 5 + eye_offset, eye_y), 2)

    # Run animation: tiny ground shadow flicker
    if state == "run":
        bob = int(math.sin(pygame.time.get_ticks() / 80) * 1)
        pygame.draw.line(
            surface, (180, 180, 180),
            (rect_x, int(screen_y_top + h - 1 + bob)),
            (rect_x + w, int(screen_y_top + h - 1 + bob)), 1,
        )
