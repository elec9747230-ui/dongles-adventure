"""Dongle the Persian cat - player entity."""
from __future__ import annotations

import settings
from engine.physics import Rect, apply_gravity


class Player:
    def __init__(self, start_x: float, start_y: float) -> None:
        self.x: float = start_x
        self.y: float = start_y
        self.vx: float = 0.0
        self.vy: float = 0.0
        self.grounded: bool = False

        # Lives / damage
        self.lives: int = settings.START_LIVES
        self.iframe_timer: float = 0.0

        # Input state
        self._left_held: bool = False
        self._right_held: bool = False
        self._jump_pressed_buffer: float = 0.0  # remaining seconds of buffered press
        self._jump_held: bool = False
        self._coyote_timer: float = 0.0  # remaining seconds of coyote window

        # Powerups
        self.jump_boost_timer: float = 0.0
        self.invincible_timer: float = 0.0

        # Per-frame event flags (consumed by scene for SFX/animation)
        self.just_jumped: bool = False
        self.just_landed: bool = False

    # ---------------------------------------------------------------- input

    def set_input(
        self,
        *,
        left_held: bool,
        right_held: bool,
        jump_pressed: bool,
        jump_held: bool,
    ) -> None:
        self._left_held = left_held
        self._right_held = right_held
        self._jump_held = jump_held
        if jump_pressed:
            self._jump_pressed_buffer = settings.JUMP_BUFFER

    # ---------------------------------------------------------------- update

    def update(self, dt: float) -> None:
        # Reset per-frame flags
        self.just_jumped = False
        self.just_landed = False

        # Horizontal: left has priority when both held.
        if self._left_held:
            self.vx = -settings.MOVE_SPEED
        elif self._right_held:
            self.vx = settings.MOVE_SPEED
        else:
            self.vx = 0.0

        # Decay timers
        self._jump_pressed_buffer = max(0.0, self._jump_pressed_buffer - dt)
        self.iframe_timer = max(0.0, self.iframe_timer - dt)
        self.jump_boost_timer = max(0.0, self.jump_boost_timer - dt)
        self.invincible_timer = max(0.0, self.invincible_timer - dt)

        # Coyote: refill while grounded; tick down while airborne
        if self.grounded:
            self._coyote_timer = settings.COYOTE_TIME
        else:
            self._coyote_timer = max(0.0, self._coyote_timer - dt)

        # Jump trigger: requires buffered press AND (grounded OR coyote-time available)
        if self._jump_pressed_buffer > 0.0 and (self.grounded or self._coyote_timer > 0.0):
            jump_v = settings.JUMP_VELOCITY
            if self.jump_boost_timer > 0.0:
                jump_v *= 1.4
            self.vy = jump_v
            self.grounded = False
            self._jump_pressed_buffer = 0.0
            self._coyote_timer = 0.0
            self.just_jumped = True

        # Variable jump height: on jump release while still rising, clamp upward velocity
        if not self._jump_held and self.vy > settings.SHORT_JUMP_CUTOFF:
            self.vy = settings.SHORT_JUMP_CUTOFF

        # Gravity (always; collision step zeroes vy and re-grounds where appropriate)
        if not self.grounded:
            self.vy = apply_gravity(self.vy, settings.GRAVITY, dt)

        # Integrate position
        self.x += self.vx * dt
        self.y += self.vy * dt

        # Horizontal wrap inside the play area
        if self.x < 0:
            self.x = 0.0
        if self.x + settings.PLAYER_WIDTH > settings.INTERNAL_WIDTH:
            self.x = settings.INTERNAL_WIDTH - settings.PLAYER_WIDTH

    # ---------------------------------------------------------------- helpers

    @property
    def rect(self) -> Rect:
        return Rect(x=self.x, y=self.y, w=settings.PLAYER_WIDTH, h=settings.PLAYER_HEIGHT)

    @property
    def altitude_m(self) -> int:
        return max(0, int(self.y) // settings.PIXELS_PER_METER)

    def take_hit(self) -> None:
        if self.iframe_timer > 0 or self.invincible_timer > 0:
            return
        self.lives -= 1
        self.iframe_timer = settings.IFRAME_DURATION

    @property
    def is_alive(self) -> bool:
        return self.lives >= 0
