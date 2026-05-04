"""Pure-function physics primitives for Dongle's Adventure.

This module is intentionally state-free: every function takes inputs and
returns outputs, with no hidden globals. That keeps the physics easy to
unit-test and lets us run the same code path on prediction (e.g. ghost
trajectories) and on the live player without surprises.

Conventions:

- ``world_y`` increases UPWARD (altitude). This is the OPPOSITE of pygame
  screen coordinates; conversion is the camera's job (see
  :mod:`engine.camera`).
- Velocity ``vy``: positive => moving up, negative => moving down.
- Gravity is a positive scalar that REDUCES ``vy`` over time (pulls down).

Typical jump-height formula (provided here so callers don't have to rederive
it): for a desired peak height ``H`` (px) and gravity ``g`` (px/s^2), the
required initial jump velocity is ``v0 = sqrt(2 * g * H)``. Hang time to apex
is ``v0 / g``. These shape the "feel" knobs in :mod:`settings`.

Terminal velocity (a maximum downward speed) is *not* enforced inside
:func:`apply_gravity` — callers should clamp ``vy`` themselves after the
gravity step (e.g. ``vy = max(vy, -TERMINAL_VY)``). Keeping the clamp out of
this function preserves the pure-function contract and lets different
entities pick different terminal speeds (player vs. enemies vs. particles).

Coyote-time (a few frames of grace where a jump is still allowed *after*
walking off a ledge) is also implemented at the entity level, not here: it's
a timer the player ticks down each frame, and the jump check uses
``coyote_timer > 0`` instead of ``is_grounded``. Coyote-time exists because
human reaction times mean players often hit jump 1-3 frames late on running
falls, and rejecting those inputs feels unfair even though the code is
"correct".
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Rect:
    """Axis-aligned rectangle. Origin at lower-left corner in world space.

    Width and height are positive; x and y are the lower-left corner coords.
    The class is frozen so rectangles can be hashed and freely passed around
    without aliasing bugs — produce a new ``Rect`` to "move" one.

    Attributes:
        x (float): World-space x of the LEFT edge.
        y (float): World-space y of the BOTTOM edge (up-positive, so this is
            the lower altitude of the rectangle).
        w (float): Width in pixels; expected to be > 0.
        h (float): Height in pixels; expected to be > 0.
    """
    x: float
    y: float
    w: float
    h: float

    @property
    def left(self) -> float:
        """World-space x coordinate of the left edge."""
        return self.x

    @property
    def right(self) -> float:
        """World-space x coordinate of the right edge."""
        return self.x + self.w

    @property
    def bottom(self) -> float:
        """World-space y coordinate of the bottom edge (lowest altitude)."""
        return self.y

    @property
    def top(self) -> float:
        """World-space y coordinate of the top edge (highest altitude)."""
        return self.y + self.h


def apply_gravity(vy: float, gravity: float, dt: float) -> float:
    """Return new vy after applying gravity for ``dt`` seconds.

    Args:
        vy: Current vertical velocity (up-positive, px/s).
        gravity: Positive gravity scalar in px/s^2 (e.g. ``1200``). Tuning
            this single number is the cleanest way to make the game feel
            heavier/floatier.
        dt: Frame delta time in seconds.

    Returns:
        New ``vy`` after one Euler integration step.

    Why subtract: ``vy`` is up-positive but gravity pulls altitude DOWN, so
    each tick we subtract ``gravity * dt``. The integration is explicit Euler
    — first-order and slightly energy-gaining at large ``dt`` — but for a
    60 Hz platformer with bounded ``dt`` it's fine and matches the formula
    students intuit from physics class. Note: this function does NOT clamp
    to a terminal velocity; do that at the call site.
    """
    return vy - gravity * dt


def aabb_overlap(a: Rect, b: Rect) -> bool:
    """Strict AABB overlap. Returns False for edge-touching rectangles.

    Args:
        a: First rectangle.
        b: Second rectangle.

    Returns:
        ``True`` iff the open interiors of ``a`` and ``b`` intersect.

    Why strict (``>`` instead of ``>=``): when the player lands exactly on a
    platform their feet's bottom edge equals the platform's top edge. With
    non-strict comparison that would register as an overlap and the resolver
    would push them off again; strict comparison lets "resting on top of"
    be a stable state.
    """
    return a.right > b.left and b.right > a.left and a.top > b.bottom and b.top > a.bottom
