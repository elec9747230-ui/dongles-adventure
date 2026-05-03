"""Platforms - the floors Dongle lands on while climbing."""
from __future__ import annotations

import math
from typing import Iterable

import pygame

import settings
from engine.physics import Rect, aabb_overlap


class StandardPlatform:
    """A solid, stable cat-tower tier. One-way: player can jump up through it."""

    def __init__(self, x: float, y: float, w: float = 48.0, h: float = 8.0) -> None:
        self.x = x
        self.y = y  # bottom-y in world coords
        self.w = w
        self.h = h

    @property
    def top(self) -> float:
        return self.y + self.h

    @property
    def rect(self) -> Rect:
        return Rect(x=self.x, y=self.y, w=self.w, h=self.h)

    def update(self, dt: float) -> None:
        pass  # static

    def on_landed(self, player) -> None:  # noqa: ANN001
        pass  # standard platform is inert on landing

    def draw(self, surface: pygame.Surface, camera) -> None:  # noqa: ANN001
        screen_y_top = camera.world_to_screen_y(self.top)
        pygame.draw.rect(
            surface, settings.COLOR_PLATFORM,
            (int(self.x), int(screen_y_top), int(self.w), int(self.h)),
        )


class HammockPlatform(StandardPlatform):
    """Stable, slight visual sway (purely cosmetic for now)."""

    def draw(self, surface: pygame.Surface, camera) -> None:  # noqa: ANN001
        screen_y_top = camera.world_to_screen_y(self.top)
        pygame.draw.rect(
            surface, (210, 180, 150),
            (int(self.x), int(screen_y_top), int(self.w), int(self.h)),
        )
        pygame.draw.line(
            surface, (140, 100, 70),
            (int(self.x), int(screen_y_top + self.h - 1)),
            (int(self.x + self.w), int(screen_y_top + self.h - 1)), 1,
        )


class RopePlatform(StandardPlatform):
    """Narrow platform: precise jumps required."""

    def __init__(self, x: float, y: float, w: float | None = None, h: float | None = None) -> None:
        # Width/height fixed regardless of generator hints.
        super().__init__(x=x, y=y, w=24.0, h=4.0)

    def draw(self, surface: pygame.Surface, camera) -> None:  # noqa: ANN001
        screen_y_top = camera.world_to_screen_y(self.top)
        pygame.draw.rect(
            surface, (200, 200, 100),
            (int(self.x), int(screen_y_top), int(self.w), int(self.h)),
        )


class SwingingPlatform(StandardPlatform):
    """Drifts left-right with sinusoidal motion."""

    def __init__(
        self,
        x: float,
        y: float,
        w: float = 60.0,
        h: float = 8.0,
        amplitude: float = 50.0,
        period: float = 3.0,
    ) -> None:
        super().__init__(x=x, y=y, w=w, h=h)
        self._x_center = x
        self._t = 0.0
        self._amp = amplitude
        self._period = period

    def update(self, dt: float) -> None:
        self._t += dt
        phase = (self._t / self._period) * 2 * math.pi
        self.x = self._x_center + math.sin(phase) * self._amp
        # Clamp inside the playfield
        self.x = max(0.0, min(settings.INTERNAL_WIDTH - self.w, self.x))

    def draw(self, surface: pygame.Surface, camera) -> None:  # noqa: ANN001
        screen_y_top = camera.world_to_screen_y(self.top)
        pygame.draw.rect(
            surface, (160, 200, 220),
            (int(self.x), int(screen_y_top), int(self.w), int(self.h)),
        )


class DisappearingPlatform(StandardPlatform):
    """Vanishes 1.0s after first landing."""

    def __init__(self, x: float, y: float, w: float = 60.0, h: float = 8.0) -> None:
        super().__init__(x=x, y=y, w=w, h=h)
        self._timer: float | None = None  # None until landed
        self.gone: bool = False

    def on_landed(self, player) -> None:  # noqa: ANN001
        if self._timer is None:
            self._timer = 1.0

    def update(self, dt: float) -> None:
        if self._timer is not None and not self.gone:
            self._timer -= dt
            if self._timer <= 0:
                self.gone = True

    def draw(self, surface: pygame.Surface, camera) -> None:  # noqa: ANN001
        if self.gone:
            return
        screen_y_top = camera.world_to_screen_y(self.top)
        flicker = self._timer is not None and self._timer < 0.5
        color = (200, 200, 200) if not flicker else (200, 100, 100)
        pygame.draw.rect(
            surface, color,
            (int(self.x), int(screen_y_top), int(self.w), int(self.h)),
        )


class StickyTapePlatform(StandardPlatform):
    """Cannot jump from here; nudges player into a fall."""

    def on_landed(self, player) -> None:  # noqa: ANN001
        # Forbid jumping for as long as touching this platform: zero coyote, drain buffer.
        player._coyote_timer = 0.0
        player._jump_pressed_buffer = 0.0
        player.vy = -10.0  # nudge down so they slip off

    def draw(self, surface: pygame.Surface, camera) -> None:  # noqa: ANN001
        screen_y_top = camera.world_to_screen_y(self.top)
        pygame.draw.rect(
            surface, (220, 180, 60),
            (int(self.x), int(screen_y_top), int(self.w), int(self.h)),
        )


def resolve_landings(player, platforms: Iterable, prev_bottom_y: float) -> None:  # noqa: ANN001
    """Detect downward landings against one-way platforms and snap the player.

    `prev_bottom_y` is the player's y BEFORE this frame's movement (one-way condition).
    """
    if player.vy > 0:  # rising
        return
    for plat in platforms:
        if getattr(plat, "gone", False):
            continue
        # Horizontal overlap
        if not aabb_overlap(player.rect, plat.rect):
            continue
        # One-way: the previous-frame bottom must have been at or above platform top
        if prev_bottom_y < plat.top:
            continue
        # Snap to platform top
        player.y = plat.top
        player.vy = 0.0
        player.grounded = True
        player.just_landed = True
        plat.on_landed(player)
        break
