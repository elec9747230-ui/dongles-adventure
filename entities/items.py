"""Pickup items.

Defines collectibles that the player overlaps to trigger an effect on the
:class:`Player` instance: tuna increments the score counter, catnip grants
temporary invincibility, feather grants a temporary jump-height boost, and
fish restores a life. The :func:`make_item` factory turns level-generator
string tags into concrete instances.

Each item bobs vertically with a sine wave for visual life and shows a soft
1-px halo so it stays readable against the busy parallax backdrop.
"""
from __future__ import annotations

import pygame

import settings
from engine.physics import Rect


class Item:
    """Base pickup. Subclasses override ``kind``, ``apply``, and ``draw``.

    Attributes:
        kind (str): Tag used by the scene to select pickup SFX/score logic.
        x (float): World-space left edge in pixels.
        y (float): World-space bottom edge in pixels (Y grows upward).
        w (int): Hitbox width in pixels.
        h (int): Hitbox height in pixels.
        dead (bool): True once consumed or culled; the scene removes it.
        _t (float): Accumulated time, drives the sine-wave bob animation.
    """

    kind: str = "base"

    def __init__(self, x: float, y: float, w: int = 24, h: int = 24) -> None:
        """Place the item and prepare its bob phase.

        Args:
            x: World X (left edge).
            y: World Y (bottom edge).
            w: Hitbox width (default 24 px — generous to keep pickups forgiving).
            h: Hitbox height (default 24 px).
        """
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.dead = False
        # Local clock for the sine bob; in seconds since spawn.
        self._t: float = 0.0

    @property
    def rect(self) -> Rect:
        """AABB used for player overlap tests."""
        return Rect(x=self.x, y=self.y, w=self.w, h=self.h)

    def update(self, dt: float, camera) -> None:  # noqa: ANN001
        """Advance the bob clock and cull when below the camera.

        Args:
            dt: Frame delta in seconds.
            camera: Scene camera; items below the viewport are freed.
        """
        self._t += dt
        if camera.is_below_screen(self.y + self.h):
            self.dead = True

    def apply(self, player) -> int:  # noqa: ANN001
        """Apply the pickup's effect to the player.

        Args:
            player: The :class:`Player` who picked the item up; subclasses may
                mutate timers/lives directly.

        Returns:
            Tuna delta to add to the scene's tuna counter (most items return 0;
            only :class:`TunaCan` returns 1).
        """
        return 0

    def _bob_offset(self) -> int:
        """Return the current vertical bob offset in pixels.

        Returns:
            An integer offset in [-2, +2] driven by ``sin(_t * 4)``.
        """
        import math
        # +/- 2 px @ ~0.64 Hz; subtle motion that doesn't disrupt collisions.
        return int(math.sin(self._t * 4.0) * 2)

    def _draw_halo(self, surface: pygame.Surface, screen_y: int, color: tuple[int, int, int]) -> None:
        """Draw a 1-px outline around the item's bounding rect.

        Args:
            surface: Render target.
            screen_y: Item's screen-space top edge in pixels.
            color: RGB outline color (subclasses tint it to match the item).
        """
        # Inflated by 2 px on each side so the outline sits just outside the
        # body and reads cleanly against any background.
        pygame.draw.rect(
            surface, color,
            (int(self.x) - 2, screen_y - 2, self.w + 4, self.h + 4), 1,
        )

    def draw(self, surface: pygame.Surface, camera) -> None:  # noqa: ANN001
        """Render a generic placeholder square (overridden by subclasses)."""
        screen_y = int(camera.world_to_screen_y(self.y + self.h)) + self._bob_offset()
        self._draw_halo(surface, screen_y, (255, 255, 255))
        pygame.draw.rect(
            surface, settings.COLOR_ITEM,
            (int(self.x), screen_y, self.w, self.h),
        )


class TunaCan(Item):
    """Score pickup. Adds +1 to the scene's tuna counter."""

    kind = "tuna"

    def apply(self, player) -> int:  # noqa: ANN001
        """Return +1 tuna; player state is unchanged."""
        return 1

    def draw(self, surface: pygame.Surface, camera) -> None:  # noqa: ANN001
        """Render a metallic can with a red lid stripe."""
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
    """Power-up. Grants 5 seconds of invincibility (no damage from hazards)."""

    kind = "catnip"

    def apply(self, player) -> int:  # noqa: ANN001
        """Set the player's 5-second invincibility timer.

        Args:
            player: Mutated in place; ``invincible_timer`` is overwritten (not
                additive) so picking up consecutive catnip caps at 5 seconds.

        Returns:
            0; catnip awards no tuna.
        """
        player.invincible_timer = 5.0
        return 0

    def draw(self, surface: pygame.Surface, camera) -> None:  # noqa: ANN001
        """Render a three-leaf catnip cluster in greens."""
        screen_y = int(camera.world_to_screen_y(self.y + self.h)) + self._bob_offset()
        self._draw_halo(surface, screen_y, (180, 255, 180))
        # Three leaves arranged around the item center.
        cx = int(self.x + self.w / 2)
        for dx, dy, color in [(-7, 4, (90, 180, 90)), (7, 4, (110, 200, 110)), (0, -4, (140, 230, 140))]:
            pygame.draw.ellipse(
                surface, color,
                (cx - 6 + dx, screen_y + 6 + dy, 12, 14),
            )


class Feather(Item):
    """Power-up. Grants 5 seconds of boosted jump velocity (1.4x in player.py)."""

    kind = "feather"

    def apply(self, player) -> int:  # noqa: ANN001
        """Set the player's 5-second jump-boost timer.

        Args:
            player: Mutated in place; ``jump_boost_timer`` is overwritten so
                back-to-back pickups do not stack.

        Returns:
            0; feather awards no tuna.
        """
        player.jump_boost_timer = 5.0
        return 0

    def draw(self, surface: pygame.Surface, camera) -> None:  # noqa: ANN001
        """Render a feather: tapered white ellipse plus a darker spine."""
        screen_y = int(camera.world_to_screen_y(self.y + self.h)) + self._bob_offset()
        self._draw_halo(surface, screen_y, (200, 230, 255))
        # Tapered ellipse body
        pygame.draw.ellipse(
            surface, (250, 250, 255),
            (int(self.x) + 3, screen_y, self.w - 6, self.h),
        )
        # Spine line down the middle
        pygame.draw.line(
            surface, (160, 180, 200),
            (int(self.x + self.w / 2), screen_y + 2),
            (int(self.x + self.w / 2), screen_y + self.h - 2), 2,
        )


class Fish(Item):
    """Heal pickup. Restores one life up to ``settings.MAX_LIVES``."""

    kind = "fish"

    def apply(self, player) -> int:  # noqa: ANN001
        """Increment lives by 1, capped at ``MAX_LIVES``.

        Args:
            player: Mutated in place; ``lives`` is bounded so collecting fish
                at full health is harmless (no overflow).

        Returns:
            0; fish awards no tuna.
        """
        # Cap-at-MAX prevents a "bank" of extra lives that would trivialize
        # later climbs.
        if player.lives < settings.MAX_LIVES:
            player.lives += 1
        return 0

    def draw(self, surface: pygame.Surface, camera) -> None:  # noqa: ANN001
        """Render a pink fish: ellipse body, triangle tail, and an eye dot."""
        screen_y = int(camera.world_to_screen_y(self.y + self.h)) + self._bob_offset()
        self._draw_halo(surface, screen_y, (255, 180, 220))
        # Fish body
        pygame.draw.ellipse(
            surface, (220, 160, 220),
            (int(self.x), screen_y + 4, self.w - 4, self.h - 8),
        )
        # Tail (triangle on the right side)
        pygame.draw.polygon(
            surface, (220, 160, 220),
            [
                (int(self.x + self.w - 4), screen_y + self.h // 2),
                (int(self.x + self.w), screen_y + 2),
                (int(self.x + self.w), screen_y + self.h - 2),
            ],
        )
        # Eye dot near the head (left side)
        pygame.draw.circle(surface, (40, 40, 60), (int(self.x) + 5, screen_y + self.h // 2), 2)


def make_item(kind: str, x: float, y: float) -> Item:
    """Construct the item subclass matching ``kind``.

    Args:
        kind: One of ``"tuna"``, ``"catnip"``, ``"feather"``, ``"fish"``.
        x: Spawn X in world coordinates.
        y: Spawn Y in world coordinates.

    Returns:
        A concrete :class:`Item` instance.

    Raises:
        KeyError: If ``kind`` is not in the dispatch table.
    """
    return {"tuna": TunaCan, "catnip": Catnip, "feather": Feather, "fish": Fish}[kind](x=x, y=y)
