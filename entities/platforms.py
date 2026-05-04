"""Platforms - the floors Dongle lands on while climbing.

This module defines all platform variants (static, hammock, narrow rope,
swinging, disappearing, sticky) that build the procedurally generated cat
tower, plus :func:`resolve_landings` which handles one-way landing collisions.

All platforms are one-way: the player jumps THROUGH them from below and lands
ON them from above, mirroring Magical Tree's tier-based climbing where
upward motion is never blocked, only landing.
"""
from __future__ import annotations

import math
from typing import Iterable

import pygame

import settings
from engine.physics import Rect, aabb_overlap


class StandardPlatform:
    """A solid, stable cat-tower tier. One-way: jump up through, land on top.

    Attributes:
        x (float): World X (left edge).
        y (float): World Y of the platform's bottom edge (Y grows upward, so
            the surface the player stands on is ``y + h``).
        w (float): Width in pixels.
        h (float): Height (thickness) in pixels.
    """

    def __init__(self, x: float, y: float, w: float = 48.0, h: float = 8.0) -> None:
        """Construct a standard platform.

        Args:
            x: World X (left edge).
            y: World Y (bottom edge in world space).
            w: Width in pixels (default 48, matches generator's standard tier).
            h: Thickness in pixels (default 8).
        """
        self.x = x
        # Stored as bottom-y so the rect math matches the rest of the engine,
        # where world Y is positive-up. Use the `top` property for landings.
        self.y = y
        self.w = w
        self.h = h

    @property
    def top(self) -> float:
        """World-space Y of the surface the player can stand on."""
        return self.y + self.h

    @property
    def rect(self) -> Rect:
        """AABB used by the landing-resolution pass."""
        return Rect(x=self.x, y=self.y, w=self.w, h=self.h)

    def update(self, dt: float) -> None:
        """No-op for a static platform.

        Args:
            dt: Frame delta in seconds (ignored).
        """
        pass

    def on_landed(self, player) -> None:  # noqa: ANN001
        """Called the frame the player lands on this platform.

        Args:
            player: The :class:`Player` that just landed. Standard platforms
                do nothing; subclasses override to e.g. start a vanish timer
                or modify player jump state.
        """
        pass

    def draw(self, surface: pygame.Surface, camera) -> None:  # noqa: ANN001
        """Draw the default platform color block at the platform's top edge."""
        screen_y_top = camera.world_to_screen_y(self.top)
        pygame.draw.rect(
            surface, settings.COLOR_PLATFORM,
            (int(self.x), int(screen_y_top), int(self.w), int(self.h)),
        )


class HammockPlatform(StandardPlatform):
    """Visually distinct standard platform (tan with a hem line).

    Mechanically identical to :class:`StandardPlatform`; the visual difference
    just helps the player parse the tier they're aiming for. The "sway" name
    is for the planned cosmetic motion (currently inert).
    """

    def draw(self, surface: pygame.Surface, camera) -> None:  # noqa: ANN001
        """Draw a tan body with a 1-px brown line along the bottom hem."""
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
    """Narrow rope tier (24x4) requiring precise jump aim."""

    def __init__(self, x: float, y: float, w: float | None = None, h: float | None = None) -> None:
        """Construct with hard-coded 24x4 dimensions.

        Args:
            x: World X (left edge).
            y: World Y (bottom edge).
            w: Ignored; the rope is always 24 px wide.
            h: Ignored; the rope is always 4 px thick.
        """
        # Force the narrow profile — the generator may pass standard sizes,
        # but a rope is always 24x4 to make landings unambiguous.
        super().__init__(x=x, y=y, w=24.0, h=4.0)

    def draw(self, surface: pygame.Surface, camera) -> None:  # noqa: ANN001
        """Draw a thin yellow strip."""
        screen_y_top = camera.world_to_screen_y(self.top)
        pygame.draw.rect(
            surface, (200, 200, 100),
            (int(self.x), int(screen_y_top), int(self.w), int(self.h)),
        )


class SwingingPlatform(StandardPlatform):
    """Platform that swings left-right along a sine wave.

    The horizontal-motion mechanic mirrors the swinging vines / pendulums in
    Magical Tree, demanding the player time their jump to the platform's
    extreme rather than blindly mashing.

    Attributes:
        _x_center (float): Anchor X around which the sine oscillates.
        _t (float): Accumulated time since spawn.
        _amp (float): Peak horizontal displacement in pixels.
        _period (float): Full-cycle duration in seconds.
    """

    def __init__(
        self,
        x: float,
        y: float,
        w: float = 60.0,
        h: float = 8.0,
        amplitude: float = 50.0,
        period: float = 3.0,
    ) -> None:
        """Initialize the platform centered at ``x``.

        Args:
            x: World X used as the swing center.
            y: World Y (bottom edge).
            w: Width in pixels.
            h: Thickness in pixels.
            amplitude: Peak displacement from center, in pixels.
            period: Full sine cycle duration, in seconds.
        """
        super().__init__(x=x, y=y, w=w, h=h)
        self._x_center = x
        self._t = 0.0
        self._amp = amplitude
        self._period = period

    def update(self, dt: float) -> None:
        """Advance the sine phase and clamp inside the play field.

        Args:
            dt: Frame delta in seconds.
        """
        self._t += dt
        phase = (self._t / self._period) * 2 * math.pi
        self.x = self._x_center + math.sin(phase) * self._amp
        # Clamp so a wide amplitude near the edges does not push the platform
        # off-screen — the player should always have a chance to reach it.
        self.x = max(0.0, min(settings.INTERNAL_WIDTH - self.w, self.x))

    def draw(self, surface: pygame.Surface, camera) -> None:  # noqa: ANN001
        """Draw a light-blue swinging-tier block."""
        screen_y_top = camera.world_to_screen_y(self.top)
        pygame.draw.rect(
            surface, (160, 200, 220),
            (int(self.x), int(screen_y_top), int(self.w), int(self.h)),
        )


class DisappearingPlatform(StandardPlatform):
    """Platform that vanishes 1.0s after the first landing.

    Once the player touches it, a countdown starts. While ``< 0.5`` seconds
    remain it flickers red as a warning, then disappears (``gone`` set True),
    after which the landing-resolution pass skips it entirely.

    Attributes:
        _timer (float | None): Seconds remaining until vanish. ``None`` means
            the platform has not yet been landed on.
        gone (bool): True once the timer has elapsed; treated as nonexistent.
    """

    def __init__(self, x: float, y: float, w: float = 60.0, h: float = 8.0) -> None:
        """Initialize as solid; timer arms only after first landing."""
        super().__init__(x=x, y=y, w=w, h=h)
        # `None` distinguishes "never landed yet" from "0.0s remaining" so the
        # platform stays solid indefinitely until the player commits to it.
        self._timer: float | None = None
        self.gone: bool = False

    def on_landed(self, player) -> None:  # noqa: ANN001
        """Arm the 1-second vanish timer (only on the very first landing).

        Args:
            player: Unused; we just need the trigger.
        """
        # Only arm once: subsequent touches don't reset the timer.
        if self._timer is None:
            self._timer = 1.0

    def update(self, dt: float) -> None:
        """Tick the vanish timer if armed."""
        if self._timer is not None and not self.gone:
            self._timer -= dt
            if self._timer <= 0:
                self.gone = True

    def draw(self, surface: pygame.Surface, camera) -> None:  # noqa: ANN001
        """Draw grey, flickering red in the final 0.5 seconds."""
        if self.gone:
            return
        screen_y_top = camera.world_to_screen_y(self.top)
        # Flicker red in the last half-second so the player gets a clear
        # "leave now" cue before the platform disappears.
        flicker = self._timer is not None and self._timer < 0.5
        color = (200, 200, 200) if not flicker else (200, 100, 100)
        pygame.draw.rect(
            surface, color,
            (int(self.x), int(screen_y_top), int(self.w), int(self.h)),
        )


class StickyTapePlatform(StandardPlatform):
    """Sticky tape: the player CANNOT jump while standing on it.

    Steals the player's coyote-time and jump-buffer, and applies a slight
    downward velocity nudge so they slide off the edge instead of being able
    to recover with a delayed press.
    """

    def on_landed(self, player) -> None:  # noqa: ANN001
        """Disable jumping by clearing all jump-eligibility timers.

        Args:
            player: Mutated in place: coyote timer zeroed, buffered press
                drained, and a small negative ``vy`` applied so the cat slips
                downward off the platform edge.
        """
        # Forbid jumping for as long as touching this platform: zero coyote
        # window AND drain any buffered jump press so the next frame can't
        # consume an earlier press to escape.
        player._coyote_timer = 0.0
        player._jump_pressed_buffer = 0.0
        # Tiny downward nudge so the player slips off rather than being able
        # to "stick" indefinitely on the surface.
        player.vy = -10.0

    def draw(self, surface: pygame.Surface, camera) -> None:  # noqa: ANN001
        """Draw a sticky-tape yellow block."""
        screen_y_top = camera.world_to_screen_y(self.top)
        pygame.draw.rect(
            surface, (220, 180, 60),
            (int(self.x), int(screen_y_top), int(self.w), int(self.h)),
        )


def resolve_landings(player, platforms: Iterable, prev_bottom_y: float) -> None:  # noqa: ANN001
    """Snap a falling player onto the first valid one-way platform.

    Iterates platforms once and lands the player on the first whose AABB
    overlaps the player's AND whose top edge was at or below the player's
    previous bottom. The previous-frame check is what makes platforms
    one-way: the player can jump up through them from below without snagging.

    Args:
        player: The :class:`Player` to snap. Mutated: ``y``, ``vy``,
            ``grounded``, and ``just_landed`` are updated; the platform's
            ``on_landed`` hook is invoked.
        platforms: Iterable of platform instances to test.
        prev_bottom_y: Player's bottom-Y in world space at the START of the
            current frame, before integration. Required for the one-way
            condition.
    """
    # Rising: never land. Skip the whole pass.
    if player.vy > 0:
        return
    for plat in platforms:
        # Skip platforms that have already vanished (DisappearingPlatform).
        if getattr(plat, "gone", False):
            continue
        # Horizontal/vertical AABB overlap check.
        if not aabb_overlap(player.rect, plat.rect):
            continue
        # One-way landing: the player must have been at or above the platform
        # top BEFORE this frame's integration. This prevents catching the
        # player from below while they ascend through the platform.
        if prev_bottom_y < plat.top:
            continue
        # Snap the player to the platform's top surface and ground them.
        player.y = plat.top
        player.vy = 0.0
        player.grounded = True
        player.just_landed = True
        plat.on_landed(player)
        # Only land on one platform per frame to avoid double-handling
        # overlapping tiers stacked at the same height.
        break
