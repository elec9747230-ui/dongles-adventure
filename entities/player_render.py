"""Draws Dongle — a cute white Persian cat with leg animation.

Single seam for swapping placeholder primitives for real sprite sheets later.
All callers go through `draw_player`.
"""
from __future__ import annotations

import math

import pygame

import settings

# Palette
FUR = settings.COLOR_PLAYER          # white body
FUR_SHADE = (215, 215, 220)
EAR_PINK = (240, 175, 200)
CHEEK = (255, 180, 195)
EYE = (40, 40, 70)
EYE_HL = (250, 250, 255)
NOSE = (240, 130, 160)
PAW = (240, 240, 240)
TAIL_TIP = (235, 200, 220)


def _facing(player) -> int:  # noqa: ANN001
    if player.vx < -1:
        return -1
    if player.vx > 1:
        return 1
    return getattr(player, "_last_facing", 1)


def _state(player) -> str:  # noqa: ANN001
    if not player.grounded:
        return "jump" if player.vy > 0 else "fall"
    if abs(player.vx) > 0.1:
        return "run"
    return "idle"


def draw_player(surface: pygame.Surface, player, camera) -> None:  # noqa: ANN001
    # I-frame blink: skip every other 0.15s window
    if player.iframe_timer > 0:
        if int(player.iframe_timer * 6.7) % 2 == 0:
            return

    facing = _facing(player)
    player._last_facing = facing  # type: ignore[attr-defined]
    state = _state(player)

    w = settings.PLAYER_WIDTH
    h = settings.PLAYER_HEIGHT
    screen_y_top = int(camera.world_to_screen_y(player.y + h))
    rect_x = int(player.x)

    cx = rect_x + w // 2
    body_top = screen_y_top + h // 3
    body_bot = screen_y_top + h
    body_h = body_bot - body_top

    # ----- Tail (drawn behind body) ----------------------------------------
    tail_phase = pygame.time.get_ticks() / 200.0
    tail_curl = math.sin(tail_phase) * 3 if state == "run" else math.sin(tail_phase * 0.5) * 1
    tail_base_x = rect_x + (w - 6 if facing == -1 else 6)
    tail_base_y = body_top + body_h // 2
    # Curled tail: short arc using a few overlapping circles
    for i, t in enumerate((0.0, 0.3, 0.6, 0.9)):
        tx = tail_base_x + (-facing) * (4 + i * 3)
        ty = tail_base_y - int(math.sin(t * math.pi) * 8) - i + int(tail_curl * (i / 4))
        r = max(2, 5 - i)
        pygame.draw.circle(surface, FUR if i < 3 else TAIL_TIP, (tx, ty), r)

    # ----- Legs (animated by state) ----------------------------------------
    # Two visible legs (front + back). For run, alternate forward/back across
    # a 4-step cycle. For jump, both tucked up. For fall, both spread.
    leg_y = body_bot - 1
    if state == "run":
        cycle = (pygame.time.get_ticks() // 110) % 4
        # Phases: 0=neutral, 1=front-fwd, 2=neutral, 3=back-fwd
        front_dx = (0, 4, 0, -2)[cycle] * facing
        back_dx = (0, -2, 0, 4)[cycle] * facing
        front_lift = (0, -1, 0, 0)[cycle]
        back_lift = (0, 0, 0, -1)[cycle]
    elif state == "jump":
        # Legs tucked up
        front_dx = -2 * facing
        back_dx = 2 * facing
        front_lift = -3
        back_lift = -3
    elif state == "fall":
        # Legs braced down/out
        front_dx = -3 * facing
        back_dx = 3 * facing
        front_lift = 1
        back_lift = 1
    else:  # idle
        front_dx = 0
        back_dx = 0
        front_lift = 0
        back_lift = 0

    front_x = cx + (4 * facing) + front_dx
    back_x = cx - (4 * facing) + back_dx
    # Back leg first (drawn behind)
    pygame.draw.ellipse(surface, FUR, (back_x - 3, leg_y - 5 + back_lift, 6, 6))
    pygame.draw.ellipse(surface, PAW, (back_x - 3, leg_y - 3 + back_lift, 6, 4))
    # Front leg
    pygame.draw.ellipse(surface, FUR, (front_x - 3, leg_y - 5 + front_lift, 6, 6))
    pygame.draw.ellipse(surface, PAW, (front_x - 3, leg_y - 3 + front_lift, 6, 4))

    # ----- Body ------------------------------------------------------------
    body_rect = pygame.Rect(rect_x + 3, body_top, w - 6, body_h)
    pygame.draw.ellipse(surface, FUR, body_rect)
    pygame.draw.ellipse(surface, FUR_SHADE, body_rect.inflate(-4, -4))

    # ----- Head (sphere on top of body) ------------------------------------
    head_r = h // 3
    head_cx = cx
    head_cy = screen_y_top + head_r + 1
    pygame.draw.circle(surface, FUR, (head_cx, head_cy), head_r)
    # Soft cheeks (drawn before fur shade so they peek through)
    pygame.draw.circle(surface, CHEEK, (head_cx - head_r // 2 - 1, head_cy + 3), 3)
    pygame.draw.circle(surface, CHEEK, (head_cx + head_r // 2 + 1, head_cy + 3), 3)

    # ----- Ears ------------------------------------------------------------
    ear_h = head_r
    # Left ear
    pygame.draw.polygon(
        surface, FUR,
        [
            (head_cx - head_r + 2, head_cy - head_r // 2),
            (head_cx - head_r // 2, head_cy - head_r - ear_h // 2),
            (head_cx - 2, head_cy - head_r // 2),
        ],
    )
    pygame.draw.polygon(
        surface, EAR_PINK,
        [
            (head_cx - head_r + 4, head_cy - head_r // 2 - 1),
            (head_cx - head_r // 2, head_cy - head_r - ear_h // 4),
            (head_cx - 4, head_cy - head_r // 2 - 1),
        ],
    )
    # Right ear
    pygame.draw.polygon(
        surface, FUR,
        [
            (head_cx + head_r - 2, head_cy - head_r // 2),
            (head_cx + head_r // 2, head_cy - head_r - ear_h // 2),
            (head_cx + 2, head_cy - head_r // 2),
        ],
    )
    pygame.draw.polygon(
        surface, EAR_PINK,
        [
            (head_cx + head_r - 4, head_cy - head_r // 2 - 1),
            (head_cx + head_r // 2, head_cy - head_r - ear_h // 4),
            (head_cx + 4, head_cy - head_r // 2 - 1),
        ],
    )

    # ----- Big expressive eyes --------------------------------------------
    eye_dx = 2 * facing
    eye_y = head_cy
    # Eye whites (large round)
    for sign in (-1, 1):
        ex = head_cx + sign * 5 + eye_dx
        pygame.draw.circle(surface, EYE_HL, (ex, eye_y), 4)
        pygame.draw.circle(surface, EYE, (ex, eye_y), 3)
        # White highlight
        pygame.draw.circle(surface, EYE_HL, (ex - 1, eye_y - 1), 1)

    # ----- Nose + mouth ----------------------------------------------------
    nose_y = head_cy + 4
    pygame.draw.polygon(
        surface, NOSE,
        [(head_cx - 2, nose_y), (head_cx + 2, nose_y), (head_cx, nose_y + 2)],
    )
    # Tiny smile (two arcs)
    pygame.draw.arc(surface, EYE, (head_cx - 4, nose_y + 1, 4, 4), math.pi, 2 * math.pi, 1)
    pygame.draw.arc(surface, EYE, (head_cx, nose_y + 1, 4, 4), math.pi, 2 * math.pi, 1)
