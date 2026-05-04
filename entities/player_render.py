"""Draws Dongle — a cute white Persian cat with leg animation.

Renders the player as composed primitives (ellipses, circles, polygons)
rather than a sprite sheet. The single public entry point :func:`draw_player`
acts as the seam where a real sprite-sheet implementation can be swapped in
without touching scene code.

The cat is drawn at the internal resolution (no scaling here); the engine's
final blit-to-window step is responsible for upscaling. Animation derives
from the player's velocity-based state machine (idle/run/jump/fall) plus a
pygame-tick-driven cadence for legs and tail.
"""
from __future__ import annotations

import math

import pygame

import settings

# Palette - pulled from settings where shared, hand-tuned for the cat.
FUR = settings.COLOR_PLAYER          # white body
FUR_SHADE = (215, 215, 220)          # subtle inner shade ellipse
EAR_PINK = (240, 175, 200)           # inner ear
CHEEK = (255, 180, 195)              # blush dots
EYE = (40, 40, 70)                   # iris (very dark blue)
EYE_HL = (250, 250, 255)             # eye sclera + sparkle
NOSE = (240, 130, 160)               # tiny pink triangle
PAW = (240, 240, 240)                # paw pad ellipse
TAIL_TIP = (235, 200, 220)           # tip of the tail (slightly pinker)


def _facing(player) -> int:  # noqa: ANN001
    """Determine which direction the cat should face this frame.

    Args:
        player: Player whose ``vx`` decides direction; near-zero velocity
            falls back to the cached ``_last_facing`` so the cat doesn't
            snap forward when the player stands still.

    Returns:
        ``-1`` for left-facing, ``+1`` for right-facing.
    """
    # +/-1 deadband ignores tiny float noise from physics integration so the
    # cat stays still rather than jittering left/right when stationary.
    if player.vx < -1:
        return -1
    if player.vx > 1:
        return 1
    return getattr(player, "_last_facing", 1)


def _state(player) -> str:  # noqa: ANN001
    """Map the player's physics state to one of four animation states.

    Args:
        player: The :class:`~entities.player.Player`.

    Returns:
        One of ``"jump"``, ``"fall"``, ``"run"``, ``"idle"``. Airborne states
        are decided by velocity sign (positive vy = jump, otherwise fall),
        ground states by horizontal speed.
    """
    if not player.grounded:
        return "jump" if player.vy > 0 else "fall"
    if abs(player.vx) > 0.1:
        return "run"
    return "idle"


def draw_player(surface: pygame.Surface, player, camera) -> None:  # noqa: ANN001
    """Render Dongle in his current state and facing direction.

    Composes the cat from back-to-front: tail, legs, body, head, ears, eyes,
    nose/mouth. During i-frames the cat blinks by skipping every other render
    window so damage is visually obvious.

    Args:
        surface: Internal-resolution render target.
        player: Player whose position, velocity, and timers drive the visual.
        camera: Camera providing the world-to-screen Y mapping. Note that
            ``_last_facing`` is cached on ``player`` to avoid the cat
            snapping forward when standing still.
    """
    # I-frame blink: hide on alternating ~0.15s windows. The 6.7 multiplier
    # gives roughly 3-4 blink cycles over IFRAME_DURATION, mimicking the
    # classic "hit-stop flicker" players expect after taking damage.
    if player.iframe_timer > 0:
        if int(player.iframe_timer * 6.7) % 2 == 0:
            return

    facing = _facing(player)
    # Cache facing on the player so _facing() can use it next frame when vx
    # is near zero (prevents idle direction flicker after stopping).
    player._last_facing = facing  # type: ignore[attr-defined]
    state = _state(player)

    w = settings.PLAYER_WIDTH
    h = settings.PLAYER_HEIGHT
    # Hitbox top in screen pixels. Drawing builds downward from this anchor.
    screen_y_top = int(camera.world_to_screen_y(player.y + h))
    rect_x = int(player.x)

    cx = rect_x + w // 2
    # Body occupies the lower 2/3 of the hitbox; the upper 1/3 is the head.
    body_top = screen_y_top + h // 3
    body_bot = screen_y_top + h
    body_h = body_bot - body_top

    # ----- Tail (drawn behind body) ----------------------------------------
    # Tail uses a global pygame clock so the cadence is independent of the
    # game's fixed timestep. Running causes a faster, larger curl.
    tail_phase = pygame.time.get_ticks() / 200.0
    tail_curl = math.sin(tail_phase) * 3 if state == "run" else math.sin(tail_phase * 0.5) * 1
    # Tail base sits on the rear side of the body relative to facing.
    tail_base_x = rect_x + (w - 6 if facing == -1 else 6)
    tail_base_y = body_top + body_h // 2
    # Curled tail approximated by 4 overlapping circles tracing a short arc.
    # Last circle is drawn in TAIL_TIP color for a subtle two-tone look.
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
        # 110 ms per phase => ~2.27 Hz, 4-frame cycle ~= 440 ms — matches a
        # comfortable Persian-cat trot cadence. Tied to the wall clock so it
        # looks correct regardless of frame rate.
        cycle = (pygame.time.get_ticks() // 110) % 4
        # Phases: 0=neutral, 1=front-fwd, 2=neutral, 3=back-fwd. Multiplied
        # by `facing` so the leg always swings in the direction of motion.
        front_dx = (0, 4, 0, -2)[cycle] * facing
        back_dx = (0, -2, 0, 4)[cycle] * facing
        # Subtle vertical lift on the leg that's mid-stride.
        front_lift = (0, -1, 0, 0)[cycle]
        back_lift = (0, 0, 0, -1)[cycle]
    elif state == "jump":
        # Legs tucked up while rising — reads as effort/launch.
        front_dx = -2 * facing
        back_dx = 2 * facing
        front_lift = -3
        back_lift = -3
    elif state == "fall":
        # Legs braced outward while falling — reads as anticipation of landing.
        front_dx = -3 * facing
        back_dx = 3 * facing
        front_lift = 1
        back_lift = 1
    else:  # idle
        front_dx = 0
        back_dx = 0
        front_lift = 0
        back_lift = 0

    # Leg X is offset 4 px from center so the front and back legs read as
    # separate limbs rather than overlapping.
    front_x = cx + (4 * facing) + front_dx
    back_x = cx - (4 * facing) + back_dx
    # Back leg first so the front leg's draw order puts it visually closer.
    pygame.draw.ellipse(surface, FUR, (back_x - 3, leg_y - 5 + back_lift, 6, 6))
    pygame.draw.ellipse(surface, PAW, (back_x - 3, leg_y - 3 + back_lift, 6, 4))
    # Front leg
    pygame.draw.ellipse(surface, FUR, (front_x - 3, leg_y - 5 + front_lift, 6, 6))
    pygame.draw.ellipse(surface, PAW, (front_x - 3, leg_y - 3 + front_lift, 6, 4))

    # ----- Body ------------------------------------------------------------
    # Outer fur ellipse plus an inset shade ellipse to suggest volume.
    body_rect = pygame.Rect(rect_x + 3, body_top, w - 6, body_h)
    pygame.draw.ellipse(surface, FUR, body_rect)
    pygame.draw.ellipse(surface, FUR_SHADE, body_rect.inflate(-4, -4))

    # ----- Head (sphere on top of body) ------------------------------------
    # Head radius is 1/3 of player height so head + body roughly tile h.
    head_r = h // 3
    head_cx = cx
    head_cy = screen_y_top + head_r + 1
    pygame.draw.circle(surface, FUR, (head_cx, head_cy), head_r)
    # Cheek blush dots — small enough to suggest "Persian cat with full face".
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
    # Eyes shift 2 px in the facing direction so the gaze tracks motion.
    eye_dx = 2 * facing
    eye_y = head_cy
    for sign in (-1, 1):
        ex = head_cx + sign * 5 + eye_dx
        # Layered: outer sclera ring (4), iris (3), and a 1-px sparkle in the
        # upper-left to give the eye a moist, alive look.
        pygame.draw.circle(surface, EYE_HL, (ex, eye_y), 4)
        pygame.draw.circle(surface, EYE, (ex, eye_y), 3)
        pygame.draw.circle(surface, EYE_HL, (ex - 1, eye_y - 1), 1)

    # ----- Nose + mouth ----------------------------------------------------
    nose_y = head_cy + 4
    # Pink triangle nose, point downward.
    pygame.draw.polygon(
        surface, NOSE,
        [(head_cx - 2, nose_y), (head_cx + 2, nose_y), (head_cx, nose_y + 2)],
    )
    # Mouth = two adjacent half-circle arcs, forming the classic cat ":3" smile.
    pygame.draw.arc(surface, EYE, (head_cx - 4, nose_y + 1, 4, 4), math.pi, 2 * math.pi, 1)
    pygame.draw.arc(surface, EYE, (head_cx, nose_y + 1, 4, 4), math.pi, 2 * math.pi, 1)
