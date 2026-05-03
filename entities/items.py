"""Pickup items."""
from __future__ import annotations

import pygame

import settings
from engine.physics import Rect


class Item:
    kind: str = "base"

    def __init__(self, x: float, y: float, w: int = 14, h: int = 14) -> None:
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.dead = False

    @property
    def rect(self) -> Rect:
        return Rect(x=self.x, y=self.y, w=self.w, h=self.h)

    def update(self, dt: float, camera) -> None:  # noqa: ANN001
        if camera.is_below_screen(self.y + self.h):
            self.dead = True

    def apply(self, player) -> int:  # noqa: ANN001
        """Apply effect; return tuna delta to add to scene's tuna counter."""
        return 0

    def draw(self, surface: pygame.Surface, camera) -> None:  # noqa: ANN001
        screen_y = camera.world_to_screen_y(self.y + self.h)
        pygame.draw.rect(
            surface, settings.COLOR_ITEM,
            (int(self.x), int(screen_y), self.w, self.h),
        )


class TunaCan(Item):
    kind = "tuna"

    def apply(self, player) -> int:  # noqa: ANN001
        return 1  # tuna count++

    def draw(self, surface: pygame.Surface, camera) -> None:  # noqa: ANN001
        screen_y = camera.world_to_screen_y(self.y + self.h)
        pygame.draw.rect(
            surface, (210, 210, 230),
            (int(self.x), int(screen_y), self.w, self.h),
        )
        pygame.draw.line(
            surface, (160, 160, 200),
            (int(self.x), int(screen_y + self.h / 2)),
            (int(self.x + self.w), int(screen_y + self.h / 2)), 1,
        )


class Catnip(Item):
    kind = "catnip"

    def apply(self, player) -> int:  # noqa: ANN001
        player.invincible_timer = 5.0
        return 0

    def draw(self, surface: pygame.Surface, camera) -> None:  # noqa: ANN001
        screen_y = camera.world_to_screen_y(self.y + self.h)
        pygame.draw.polygon(
            surface, (140, 220, 140),
            [
                (int(self.x + self.w / 2), int(screen_y)),
                (int(self.x), int(screen_y + self.h)),
                (int(self.x + self.w), int(screen_y + self.h)),
            ],
        )


class Feather(Item):
    kind = "feather"

    def apply(self, player) -> int:  # noqa: ANN001
        player.jump_boost_timer = 5.0
        return 0

    def draw(self, surface: pygame.Surface, camera) -> None:  # noqa: ANN001
        screen_y = camera.world_to_screen_y(self.y + self.h)
        pygame.draw.line(
            surface, (240, 240, 240),
            (int(self.x + self.w / 2), int(screen_y)),
            (int(self.x + self.w / 2), int(screen_y + self.h)), 2,
        )


class Fish(Item):
    kind = "fish"

    def apply(self, player) -> int:  # noqa: ANN001
        if player.lives < settings.MAX_LIVES:
            player.lives += 1
        return 0

    def draw(self, surface: pygame.Surface, camera) -> None:  # noqa: ANN001
        screen_y = camera.world_to_screen_y(self.y + self.h)
        pygame.draw.ellipse(
            surface, (200, 180, 240),
            (int(self.x), int(screen_y + 4), self.w, self.h - 4),
        )


def make_item(kind: str, x: float, y: float) -> Item:
    return {"tuna": TunaCan, "catnip": Catnip, "feather": Feather, "fish": Fish}[kind](x=x, y=y)
