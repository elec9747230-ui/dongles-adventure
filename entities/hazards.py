"""Hazards that try to ruin Dongle's day."""
from __future__ import annotations

import math

import pygame

import settings
from engine.physics import Rect, apply_gravity


class Hazard:
    """Base class. Subclasses override update/draw/kind."""
    kind: str = "base"

    def __init__(self, x: float, y: float, w: float, h: float) -> None:
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.dead = False
        self.lethal = False  # True for instant-death hazards (vacuum)

    @property
    def rect(self) -> Rect:
        return Rect(x=self.x, y=self.y, w=self.w, h=self.h)

    def update(self, dt: float, camera) -> None:  # noqa: ANN001
        # Default: cull when below the camera
        if camera.is_below_screen(self.y + self.h):
            self.dead = True

    def draw(self, surface: pygame.Surface, camera) -> None:  # noqa: ANN001
        screen_y = camera.world_to_screen_y(self.y + self.h)
        pygame.draw.rect(
            surface, settings.COLOR_HAZARD,
            (int(self.x), int(screen_y), int(self.w), int(self.h)),
        )


class YarnBall(Hazard):
    """Falls straight down under gravity from a spawn altitude."""
    kind = "yarn"

    def __init__(self, x: float, y: float) -> None:
        super().__init__(x=x, y=y, w=14, h=14)
        self.vy: float = 0.0

    def update(self, dt: float, camera) -> None:  # noqa: ANN001
        self.vy = apply_gravity(self.vy, settings.GRAVITY * 0.6, dt)
        self.y += self.vy * dt
        super().update(dt, camera)

    def draw(self, surface: pygame.Surface, camera) -> None:  # noqa: ANN001
        screen_y = camera.world_to_screen_y(self.y + self.h)
        pygame.draw.circle(
            surface, (220, 100, 140),
            (int(self.x + self.w / 2), int(screen_y + self.h / 2)),
            int(self.w / 2),
        )


class Mouse(Hazard):
    """Runs horizontally; bounces at edges."""
    kind = "mouse"

    def __init__(self, x: float, y: float) -> None:
        super().__init__(x=x, y=y, w=20, h=10)
        self.vx: float = 120.0 if x < settings.INTERNAL_WIDTH / 2 else -120.0

    def update(self, dt: float, camera) -> None:  # noqa: ANN001
        self.x += self.vx * dt
        if self.x <= 0 or self.x + self.w >= settings.INTERNAL_WIDTH:
            self.vx = -self.vx
            self.x = max(0.0, min(settings.INTERNAL_WIDTH - self.w, self.x))
        super().update(dt, camera)

    def draw(self, surface: pygame.Surface, camera) -> None:  # noqa: ANN001
        screen_y = camera.world_to_screen_y(self.y + self.h)
        pygame.draw.ellipse(
            surface, (140, 130, 120),
            (int(self.x), int(screen_y), int(self.w), int(self.h)),
        )


class Crow(Hazard):
    """Sinusoidal horizontal flight that gently bobs."""
    kind = "crow"

    def __init__(self, x: float, y: float) -> None:
        super().__init__(x=x, y=y, w=22, h=14)
        self.vx: float = 90.0 if x < settings.INTERNAL_WIDTH / 2 else -90.0
        self._t: float = 0.0
        self._y_center: float = y

    def update(self, dt: float, camera) -> None:  # noqa: ANN001
        self._t += dt
        self.x += self.vx * dt
        if self.x <= 0 or self.x + self.w >= settings.INTERNAL_WIDTH:
            self.vx = -self.vx
            self.x = max(0.0, min(settings.INTERNAL_WIDTH - self.w, self.x))
        self.y = self._y_center + math.sin(self._t * 2.0) * 18.0
        super().update(dt, camera)

    def draw(self, surface: pygame.Surface, camera) -> None:  # noqa: ANN001
        screen_y = camera.world_to_screen_y(self.y + self.h)
        pygame.draw.polygon(
            surface, (40, 40, 40),
            [
                (int(self.x + self.w / 2), int(screen_y)),
                (int(self.x), int(screen_y + self.h)),
                (int(self.x + self.w), int(screen_y + self.h)),
            ],
        )


class Dog(Hazard):
    """Stationary; large damage rectangle that the player should jump over."""
    kind = "dog"

    def __init__(self, x: float, y: float) -> None:
        super().__init__(x=x, y=y, w=44, h=24)

    def draw(self, surface: pygame.Surface, camera) -> None:  # noqa: ANN001
        screen_y = camera.world_to_screen_y(self.y + self.h)
        pygame.draw.rect(
            surface, (180, 140, 70),
            (int(self.x), int(screen_y), int(self.w), int(self.h)),
        )
        pygame.draw.circle(
            surface, (60, 30, 10),
            (int(self.x + self.w - 6), int(screen_y + 6)), 4,
        )


class SprayWater(Hazard):
    """Single horizontal sweep across the play area."""
    kind = "spray"

    def __init__(self, x: float, y: float) -> None:
        super().__init__(x=x, y=y, w=18, h=6)
        self.vx: float = 220.0 if x < settings.INTERNAL_WIDTH / 2 else -220.0

    def update(self, dt: float, camera) -> None:  # noqa: ANN001
        self.x += self.vx * dt
        if self.x + self.w < 0 or self.x > settings.INTERNAL_WIDTH:
            self.dead = True
        super().update(dt, camera)

    def draw(self, surface: pygame.Surface, camera) -> None:  # noqa: ANN001
        screen_y = camera.world_to_screen_y(self.y + self.h)
        pygame.draw.rect(
            surface, (100, 180, 230),
            (int(self.x), int(screen_y), int(self.w), int(self.h)),
        )


class Vacuum(Hazard):
    """Rises at constant speed from the bottom of the camera. Lethal on touch."""
    kind = "vacuum"

    SPEED = 60.0  # px/s upward (worldY-positive)

    def __init__(self, y: float, **_kwargs) -> None:
        # Accept and discard `x` from the make_hazard signature.
        super().__init__(x=0, y=y, w=settings.INTERNAL_WIDTH, h=24)
        self.lethal = True

    def update(self, dt: float, camera) -> None:  # noqa: ANN001
        self.y += self.SPEED * dt
        # Never cull the vacuum

    def draw(self, surface: pygame.Surface, camera) -> None:  # noqa: ANN001
        screen_y = camera.world_to_screen_y(self.y + self.h)
        if -self.h <= screen_y <= settings.INTERNAL_HEIGHT:
            pygame.draw.rect(
                surface, (60, 60, 80),
                (0, int(screen_y), settings.INTERNAL_WIDTH, int(self.h)),
            )
            for i in range(0, settings.INTERNAL_WIDTH, 16):
                pygame.draw.rect(
                    surface, (200, 200, 220),
                    (i, int(screen_y - 4), 8, 6),
                )


def make_hazard(kind: str, x: float, y: float) -> Hazard:
    if kind == "yarn":
        return YarnBall(x=x, y=y)
    if kind == "mouse":
        return Mouse(x=x, y=y)
    if kind == "crow":
        return Crow(x=x, y=y)
    if kind == "dog":
        return Dog(x=x, y=y)
    if kind == "spray":
        return SprayWater(x=x, y=y)
    if kind == "vacuum":
        return Vacuum(y=y)
    raise ValueError(f"Unknown hazard kind: {kind}")
