"""Pickup items."""
from __future__ import annotations

import pygame

import settings
from engine.physics import Rect


class Item:
    kind: str = "base"

    def __init__(self, x: float, y: float, w: int = 24, h: int = 24) -> None:
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.dead = False
        self._t: float = 0.0  # used for the bob animation

    @property
    def rect(self) -> Rect:
        return Rect(x=self.x, y=self.y, w=self.w, h=self.h)

    def update(self, dt: float, camera) -> None:  # noqa: ANN001
        self._t += dt
        if camera.is_below_screen(self.y + self.h):
            self.dead = True

    def apply(self, player) -> int:  # noqa: ANN001
        """Apply effect; return tuna delta to add to scene's tuna counter."""
        return 0

    def _bob_offset(self) -> int:
        import math
        return int(math.sin(self._t * 4.0) * 2)

    def _draw_halo(self, surface: pygame.Surface, screen_y: int, color: tuple[int, int, int]) -> None:
        # Soft outline so items pop against busy backgrounds
        pygame.draw.rect(
            surface, color,
            (int(self.x) - 2, screen_y - 2, self.w + 4, self.h + 4), 1,
        )

    def draw(self, surface: pygame.Surface, camera) -> None:  # noqa: ANN001
        screen_y = int(camera.world_to_screen_y(self.y + self.h)) + self._bob_offset()
        self._draw_halo(surface, screen_y, (255, 255, 255))
        pygame.draw.rect(
            surface, settings.COLOR_ITEM,
            (int(self.x), screen_y, self.w, self.h),
        )


class TunaCan(Item):
    kind = "tuna"

    def apply(self, player) -> int:  # noqa: ANN001
        return 1

    def draw(self, surface: pygame.Surface, camera) -> None:  # noqa: ANN001
        screen_y = int(camera.world_to_screen_y(self.y + self.h)) + self._bob_offset()
        self._draw_halo(surface, screen_y, (255, 220, 120))
        # Can body
        pygame.draw.rect(
            surface, (220, 220, 240),
            (int(self.x), screen_y + 4, self.w, self.h - 8),
        )
        # Lid stripe
        pygame.draw.rect(
            surface, (180, 60, 60),
            (int(self.x), screen_y + self.h // 2 - 2, self.w, 4),
        )


class Catnip(Item):
    kind = "catnip"

    def apply(self, player) -> int:  # noqa: ANN001
        player.invincible_timer = 5.0
        return 0

    def draw(self, surface: pygame.Surface, camera) -> None:  # noqa: ANN001
        screen_y = int(camera.world_to_screen_y(self.y + self.h)) + self._bob_offset()
        self._draw_halo(surface, screen_y, (180, 255, 180))
        # Three leaves
        cx = int(self.x + self.w / 2)
        for dx, dy, color in [(-7, 4, (90, 180, 90)), (7, 4, (110, 200, 110)), (0, -4, (140, 230, 140))]:
            pygame.draw.ellipse(
                surface, color,
                (cx - 6 + dx, screen_y + 6 + dy, 12, 14),
            )


class Feather(Item):
    kind = "feather"

    def apply(self, player) -> int:  # noqa: ANN001
        player.jump_boost_timer = 5.0
        return 0

    def draw(self, surface: pygame.Surface, camera) -> None:  # noqa: ANN001
        screen_y = int(camera.world_to_screen_y(self.y + self.h)) + self._bob_offset()
        self._draw_halo(surface, screen_y, (200, 230, 255))
        # Feather: tapered ellipse + spine
        pygame.draw.ellipse(
            surface, (250, 250, 255),
            (int(self.x) + 3, screen_y, self.w - 6, self.h),
        )
        pygame.draw.line(
            surface, (160, 180, 200),
            (int(self.x + self.w / 2), screen_y + 2),
            (int(self.x + self.w / 2), screen_y + self.h - 2), 2,
        )


class Fish(Item):
    kind = "fish"

    def apply(self, player) -> int:  # noqa: ANN001
        if player.lives < settings.MAX_LIVES:
            player.lives += 1
        return 0

    def draw(self, surface: pygame.Surface, camera) -> None:  # noqa: ANN001
        screen_y = int(camera.world_to_screen_y(self.y + self.h)) + self._bob_offset()
        self._draw_halo(surface, screen_y, (255, 180, 220))
        # Fish body
        pygame.draw.ellipse(
            surface, (220, 160, 220),
            (int(self.x), screen_y + 4, self.w - 4, self.h - 8),
        )
        # Tail
        pygame.draw.polygon(
            surface, (220, 160, 220),
            [
                (int(self.x + self.w - 4), screen_y + self.h // 2),
                (int(self.x + self.w), screen_y + 2),
                (int(self.x + self.w), screen_y + self.h - 2),
            ],
        )
        # Eye
        pygame.draw.circle(surface, (40, 40, 60), (int(self.x) + 5, screen_y + self.h // 2), 2)


def make_item(kind: str, x: float, y: float) -> Item:
    return {"tuna": TunaCan, "catnip": Catnip, "feather": Feather, "fish": Fish}[kind](x=x, y=y)
