"""Pure-function physics primitives for Dongle's Adventure.

Conventions:
- world_y increases UPWARD (altitude).
- Velocity vy: positive => moving up, negative => moving down.
- Gravity is a positive scalar that REDUCES vy over time (pulls down).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Rect:
    """Axis-aligned rectangle. Origin at lower-left corner in world space.

    Width and height are positive; x and y are the lower-left corner coords.
    """
    x: float
    y: float
    w: float
    h: float

    @property
    def left(self) -> float:
        return self.x

    @property
    def right(self) -> float:
        return self.x + self.w

    @property
    def bottom(self) -> float:
        return self.y

    @property
    def top(self) -> float:
        return self.y + self.h


def apply_gravity(vy: float, gravity: float, dt: float) -> float:
    """Return new vy after applying gravity for `dt` seconds.

    `gravity` is a positive scalar (e.g., 1200 px/s^2). Subtracted because
    gravity pulls altitude down and we use up-positive vy.
    """
    return vy - gravity * dt


def aabb_overlap(a: Rect, b: Rect) -> bool:
    """Strict AABB overlap. Returns False for edge-touching rectangles."""
    return a.right > b.left and b.right > a.left and a.top > b.bottom and b.top > a.bottom
