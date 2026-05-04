"""Hazards that try to ruin Dongle's day.

This module defines all enemy/obstacle entities the player must avoid while
climbing the cat tower. Each hazard exposes a uniform interface (``rect``,
``update``, ``draw``, ``dead``, ``lethal``) so the scene can iterate them
generically. The ``make_hazard`` factory translates string kinds emitted by
the level generator into concrete instances.

Most hazards deal a single point of damage on contact (handled by the scene's
collision pass via :py:meth:`Player.take_hit`). The vacuum is the sole
instant-death hazard, modelled after the rising death floor in Magical Tree:
falling behind the camera means game over.
"""
from __future__ import annotations

import math

import pygame

import settings
from engine.physics import Rect, apply_gravity


class Hazard:
    """Base hazard. Subclasses override ``update``/``draw``/``kind``.

    Attributes:
        kind (str): Tag identifying the hazard type, used by SFX/score logic.
        x (float): World-space left edge in pixels.
        y (float): World-space bottom edge in pixels (Y grows upward).
        w (float): Collision-box width in pixels.
        h (float): Collision-box height in pixels.
        dead (bool): When True, the scene removes this hazard next tick.
        lethal (bool): When True, contact bypasses i-frames and ends the run.
    """

    kind: str = "base"

    def __init__(self, x: float, y: float, w: float, h: float) -> None:
        """Store position and AABB dimensions; mark as alive and non-lethal.

        Args:
            x: World-space left edge.
            y: World-space bottom edge.
            w: Hitbox width.
            h: Hitbox height.
        """
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.dead = False
        # Only the rising vacuum sets this to True; all other hazards just
        # subtract a life and respect the player's i-frame window.
        self.lethal = False

    @property
    def rect(self) -> Rect:
        """Return the AABB used by the collision system."""
        return Rect(x=self.x, y=self.y, w=self.w, h=self.h)

    def update(self, dt: float, camera) -> None:  # noqa: ANN001
        """Default per-frame tick: cull hazards once they trail off-screen.

        Args:
            dt: Frame delta in seconds.
            camera: Scene camera; used to detect when this hazard has been
                left behind below the visible area so it can be freed.
        """
        # Cull hazards that drift below the camera viewport so the active list
        # stays small as the player climbs higher.
        if camera.is_below_screen(self.y + self.h):
            self.dead = True

    def draw(self, surface: pygame.Surface, camera) -> None:  # noqa: ANN001
        """Render a generic red hazard rectangle as a placeholder.

        Args:
            surface: Target render surface (internal-resolution buffer).
            camera: Camera providing the world-to-screen Y mapping.
        """
        screen_y = camera.world_to_screen_y(self.y + self.h)
        pygame.draw.rect(
            surface, settings.COLOR_HAZARD,
            (int(self.x), int(screen_y), int(self.w), int(self.h)),
        )


class YarnBall(Hazard):
    """Yarn ball that falls straight down under reduced gravity.

    Spawned high above the player, it drops as a vertical projectile reminiscent
    of Magical Tree's falling apples. A 0.6x gravity multiplier keeps the
    descent slow enough to dodge by side-stepping.

    Attributes:
        vy (float): Current vertical velocity (negative = falling, since Y is
            up in world space).
    """

    kind = "yarn"

    def __init__(self, x: float, y: float) -> None:
        """Spawn a 14x14 yarn projectile at rest.

        Args:
            x: World X of the spawn column.
            y: World Y of the spawn altitude (typically above the camera top).
        """
        super().__init__(x=x, y=y, w=14, h=14)
        self.vy: float = 0.0

    def update(self, dt: float, camera) -> None:  # noqa: ANN001
        """Apply gravity, integrate, then run base culling.

        Args:
            dt: Frame delta in seconds.
            camera: Scene camera for cull checks.
        """
        # 0.6x gravity gives a longer hang time than the player's so the ball
        # is dodgeable on reaction.
        self.vy = apply_gravity(self.vy, settings.GRAVITY * 0.6, dt)
        self.y += self.vy * dt
        super().update(dt, camera)

    def draw(self, surface: pygame.Surface, camera) -> None:  # noqa: ANN001
        """Draw a pink yarn-ball circle at the current world position."""
        screen_y = camera.world_to_screen_y(self.y + self.h)
        pygame.draw.circle(
            surface, (220, 100, 140),
            (int(self.x + self.w / 2), int(screen_y + self.h / 2)),
            int(self.w / 2),
        )


class Mouse(Hazard):
    """Mouse that scurries horizontally and bounces at the play-area edges.

    Spawn-side determines initial direction: spawning on the left half makes it
    head right, and vice versa, so a Mouse always enters the play area rather
    than running off it on frame 1.

    Attributes:
        vx (float): Horizontal velocity in px/s; sign flips on wall contact.
    """

    kind = "mouse"

    def __init__(self, x: float, y: float) -> None:
        """Spawn a 20x10 mouse facing inward toward the screen center."""
        super().__init__(x=x, y=y, w=20, h=10)
        # Direction depends on spawn side so the mouse always traverses the
        # play area instead of immediately leaving it.
        self.vx: float = 120.0 if x < settings.INTERNAL_WIDTH / 2 else -120.0

    def update(self, dt: float, camera) -> None:  # noqa: ANN001
        """Move horizontally and bounce off the world edges.

        Args:
            dt: Frame delta in seconds.
            camera: Scene camera for cull checks.
        """
        self.x += self.vx * dt
        if self.x <= 0 or self.x + self.w >= settings.INTERNAL_WIDTH:
            # Reverse and clamp inside bounds so we never get stuck overlapping
            # the wall (which would cause a perpetual flip).
            self.vx = -self.vx
            self.x = max(0.0, min(settings.INTERNAL_WIDTH - self.w, self.x))
        super().update(dt, camera)

    def draw(self, surface: pygame.Surface, camera) -> None:  # noqa: ANN001
        """Draw a small grey ellipse for the mouse body."""
        screen_y = camera.world_to_screen_y(self.y + self.h)
        pygame.draw.ellipse(
            surface, (140, 130, 120),
            (int(self.x), int(screen_y), int(self.w), int(self.h)),
        )


class Crow(Hazard):
    """Crow that flies horizontally and bobs vertically on a sine wave.

    The bobbing motion is the airborne analogue of Magical Tree's flying-bird
    enemies: the player must time their jump so the sine trough does not align
    with the platform they are aiming for.

    Attributes:
        vx (float): Horizontal velocity in px/s.
        _t (float): Accumulated time used to drive the sine bob.
        _y_center (float): Mean Y of the sinusoidal bob (the spawn altitude).
    """

    kind = "crow"

    def __init__(self, x: float, y: float) -> None:
        """Spawn a 22x14 crow facing the center of the play area."""
        super().__init__(x=x, y=y, w=22, h=14)
        self.vx: float = 90.0 if x < settings.INTERNAL_WIDTH / 2 else -90.0
        self._t: float = 0.0
        self._y_center: float = y

    def update(self, dt: float, camera) -> None:  # noqa: ANN001
        """Advance horizontal motion and update the sinusoidal Y bob."""
        self._t += dt
        self.x += self.vx * dt
        if self.x <= 0 or self.x + self.w >= settings.INTERNAL_WIDTH:
            self.vx = -self.vx
            self.x = max(0.0, min(settings.INTERNAL_WIDTH - self.w, self.x))
        # Bob 18 px around the spawn altitude at ~0.32 Hz (omega = 2.0 rad/s).
        self.y = self._y_center + math.sin(self._t * 2.0) * 18.0
        super().update(dt, camera)

    def draw(self, surface: pygame.Surface, camera) -> None:  # noqa: ANN001
        """Draw a black triangle, evoking a silhouetted bird."""
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
    """Stationary dog with an oversized damage rectangle.

    Acts as a wide ground hazard placed on a platform: the player must commit
    to a high jump (or use a feather power-up) to clear it. No movement.
    """

    kind = "dog"

    def __init__(self, x: float, y: float) -> None:
        """Spawn a 44x24 dog at the given platform-adjacent position."""
        # 44 px wide is wider than the player can walk through casually; the
        # box extends 24 px tall so it requires a real jump arc to clear.
        super().__init__(x=x, y=y, w=44, h=24)

    def draw(self, surface: pygame.Surface, camera) -> None:  # noqa: ANN001
        """Draw a tan rectangle with a dark circle for the eye."""
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
    """A water-spray hazard that sweeps once across the play area.

    Unlike the Mouse, the spray does NOT bounce; it self-destructs once it
    fully exits either side, making it a single-pass projectile. Useful for
    forcing the player to reposition mid-air.

    Attributes:
        vx (float): Horizontal velocity in px/s; constant once spawned.
    """

    kind = "spray"

    def __init__(self, x: float, y: float) -> None:
        """Spawn an 18x6 sliver of water heading toward screen center."""
        super().__init__(x=x, y=y, w=18, h=6)
        self.vx: float = 220.0 if x < settings.INTERNAL_WIDTH / 2 else -220.0

    def update(self, dt: float, camera) -> None:  # noqa: ANN001
        """Translate horizontally and self-kill when fully off-screen."""
        self.x += self.vx * dt
        # One-shot projectile: don't bounce, just disappear after exiting.
        if self.x + self.w < 0 or self.x > settings.INTERNAL_WIDTH:
            self.dead = True
        super().update(dt, camera)

    def draw(self, surface: pygame.Surface, camera) -> None:  # noqa: ANN001
        """Draw a light-blue water sliver."""
        screen_y = camera.world_to_screen_y(self.y + self.h)
        pygame.draw.rect(
            surface, (100, 180, 230),
            (int(self.x), int(screen_y), int(self.w), int(self.h)),
        )


class Vacuum(Hazard):
    """Full-width vacuum that rises at a constant speed. Instant death.

    Mirrors the rising death floor / lava in Magical Tree: it gives steady,
    predictable upward pressure so the player cannot hesitate on a platform.
    Marked ``lethal`` so the scene ends the run on any contact regardless of
    i-frames or invincibility.

    Attributes:
        SPEED (float): Class constant; constant upward speed in px/s.
    """

    kind = "vacuum"

    SPEED = 60.0  # px/s upward (worldY-positive)

    def __init__(self, y: float, **_kwargs) -> None:
        """Span the full play width at altitude ``y``.

        Args:
            y: World Y at which the vacuum starts (typically just below the
                initial camera viewport).
            **_kwargs: Absorb ``x`` from the generic ``make_hazard`` signature.
        """
        # `x` from make_hazard is irrelevant — the vacuum is full-width, so
        # discard it via **_kwargs and pin x=0.
        super().__init__(x=0, y=y, w=settings.INTERNAL_WIDTH, h=24)
        self.lethal = True

    def update(self, dt: float, camera) -> None:  # noqa: ANN001
        """Rise at a constant rate. Intentionally never marked dead.

        Args:
            dt: Frame delta in seconds.
            camera: Unused; the vacuum follows the player up regardless.
        """
        self.y += self.SPEED * dt
        # Deliberately do NOT call super().update: the vacuum must persist for
        # the entire run so the rising-doom pressure never lets up.

    def draw(self, surface: pygame.Surface, camera) -> None:  # noqa: ANN001
        """Render a dark band with bristles when within the viewport."""
        screen_y = camera.world_to_screen_y(self.y + self.h)
        # Cheap visibility check: only draw when actually overlapping the
        # viewport. Avoids needless overdraw when the player is far above.
        if -self.h <= screen_y <= settings.INTERNAL_HEIGHT:
            pygame.draw.rect(
                surface, (60, 60, 80),
                (0, int(screen_y), settings.INTERNAL_WIDTH, int(self.h)),
            )
            # Bristles along the top edge so the player visually reads the
            # surface as menacing rather than as a passable floor.
            for i in range(0, settings.INTERNAL_WIDTH, 16):
                pygame.draw.rect(
                    surface, (200, 200, 220),
                    (i, int(screen_y - 4), 8, 6),
                )


def make_hazard(kind: str, x: float, y: float) -> Hazard:
    """Construct the hazard subclass matching ``kind``.

    Args:
        kind: String tag from the level generator
            (``"yarn"``, ``"mouse"``, ``"crow"``, ``"dog"``, ``"spray"``,
            ``"vacuum"``).
        x: Spawn X in world coordinates.
        y: Spawn Y in world coordinates.

    Returns:
        A concrete :class:`Hazard` instance.

    Raises:
        ValueError: If ``kind`` is not a known hazard tag.
    """
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
        # Vacuum ignores X; pass only Y to the constructor.
        return Vacuum(y=y)
    raise ValueError(f"Unknown hazard kind: {kind}")
