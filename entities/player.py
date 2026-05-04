"""Dongle the Persian cat - player entity.

Implements Dongle's physics: gravity, jumping (with coyote-time, jump buffer,
and variable jump height), powerup timers, lives, and i-frames after damage.
The :class:`Player` exposes a simple input API (:meth:`Player.set_input`) and
an integration step (:meth:`Player.update`); the scene runs platform-landing
resolution between frames to settle ``y`` and ``grounded``.

The control feel borrows from Magical Tree's deliberate jump arcs while
adding modern platforming niceties (coyote-time, buffered jump, short-hop)
to keep the climb forgiving.
"""
from __future__ import annotations

import settings
from engine.physics import Rect, apply_gravity


class Player:
    """Dongle's physics, input handling, lives, and powerup state.

    Attributes:
        x (float): World X (left edge).
        y (float): World Y (bottom edge); positive grows upward.
        vx (float): Horizontal velocity in px/s.
        vy (float): Vertical velocity in px/s (positive = rising).
        grounded (bool): True iff the previous landing pass placed the player
            on a platform; cleared when a jump is initiated.
        lives (int): Remaining lives. The run ends when this drops below 0.
        iframe_timer (float): Seconds of damage immunity after a hit.
        _left_held (bool): Last-known left-input state.
        _right_held (bool): Last-known right-input state.
        _jump_pressed_buffer (float): Seconds of remaining buffered jump press
            (allows pressing slightly before landing and still jumping).
        _jump_held (bool): Whether jump is currently held (for variable jump).
        _coyote_timer (float): Seconds remaining in the post-ledge jump grace
            window (allows jumping shortly after walking off a platform).
        jump_boost_timer (float): Seconds of feather power-up remaining.
        invincible_timer (float): Seconds of catnip invincibility remaining.
        just_jumped (bool): True for the single frame a jump was triggered.
        just_landed (bool): True for the single frame a landing was resolved.
    """

    def __init__(self, start_x: float, start_y: float) -> None:
        """Spawn Dongle at the given world position with default state.

        Args:
            start_x: Initial world X.
            start_y: Initial world Y.
        """
        self.x: float = start_x
        self.y: float = start_y
        self.vx: float = 0.0
        self.vy: float = 0.0
        self.grounded: bool = False

        # Lives / damage
        self.lives: int = settings.START_LIVES
        # Brief damage immunity after a hit, prevents instant double-hits when
        # standing inside a hazard's box for multiple frames.
        self.iframe_timer: float = 0.0

        # Input state
        self._left_held: bool = False
        self._right_held: bool = False
        # Jump buffer: presses queued when airborne are honored if the player
        # lands within JUMP_BUFFER seconds.
        self._jump_pressed_buffer: float = 0.0
        self._jump_held: bool = False
        # Coyote time: jump is still allowed for COYOTE_TIME seconds after
        # walking off a platform; mitigates 1-frame timing failures.
        self._coyote_timer: float = 0.0

        # Powerups
        self.jump_boost_timer: float = 0.0
        self.invincible_timer: float = 0.0

        # Per-frame event flags (consumed by scene for SFX/animation cues
        # and reset at the top of each update()).
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
        """Forward this frame's input state into the player.

        Args:
            left_held: True if left is currently held.
            right_held: True if right is currently held.
            jump_pressed: True for the single frame jump was newly pressed
                (a rising edge); refills the jump buffer.
            jump_held: True while the jump button is held; gates variable
                jump height in :meth:`update`.
        """
        self._left_held = left_held
        self._right_held = right_held
        self._jump_held = jump_held
        if jump_pressed:
            # Refill the buffer on every fresh press so a press just before
            # landing still triggers a jump shortly after touchdown.
            self._jump_pressed_buffer = settings.JUMP_BUFFER

    # ---------------------------------------------------------------- update

    def update(self, dt: float) -> None:
        """Advance physics by ``dt`` seconds.

        Implements the player state machine implicitly via velocity/grounded:
        idle (grounded, |vx|~0), run (grounded, |vx|>0), jump (airborne,
        vy>0), fall (airborne, vy<=0). Powerup and i-frame timers tick down,
        the jump trigger consumes the buffered press, gravity integrates, and
        the position is clamped horizontally inside the play area.

        Args:
            dt: Frame delta in seconds.
        """
        # Per-frame event flags reset every tick; the scene reads them between
        # set_input/update calls.
        self.just_jumped = False
        self.just_landed = False

        # Horizontal velocity from input. Left wins when both are held — keeps
        # the controls deterministic when keys are mashed simultaneously.
        if self._left_held:
            self.vx = -settings.MOVE_SPEED
        elif self._right_held:
            self.vx = settings.MOVE_SPEED
        else:
            self.vx = 0.0

        # Decay timers; clamp to zero so we never go negative.
        self._jump_pressed_buffer = max(0.0, self._jump_pressed_buffer - dt)
        self.iframe_timer = max(0.0, self.iframe_timer - dt)
        self.jump_boost_timer = max(0.0, self.jump_boost_timer - dt)
        self.invincible_timer = max(0.0, self.invincible_timer - dt)

        # Coyote-time bookkeeping: refill to full while grounded, tick down
        # while airborne. Lets the player jump for a few frames after stepping
        # off a ledge without explicit input timing.
        if self.grounded:
            self._coyote_timer = settings.COYOTE_TIME
        else:
            self._coyote_timer = max(0.0, self._coyote_timer - dt)

        # Jump trigger: requires a recent press (buffered) AND eligibility
        # (currently grounded OR within coyote window).
        if self._jump_pressed_buffer > 0.0 and (self.grounded or self._coyote_timer > 0.0):
            jump_v = settings.JUMP_VELOCITY
            # Feather power-up multiplies launch velocity by 1.4x (not the
            # whole jump curve); short-hop cutoff still applies.
            if self.jump_boost_timer > 0.0:
                jump_v *= 1.4
            self.vy = jump_v
            self.grounded = False
            # Consume both timers so a single press never produces two jumps.
            self._jump_pressed_buffer = 0.0
            self._coyote_timer = 0.0
            self.just_jumped = True

        # Variable jump height: if the jump button has been released while
        # the player is still rising fast, clamp upward velocity to the
        # short-jump ceiling. Holding longer = higher arc; tap = small hop.
        if not self._jump_held and self.vy > settings.SHORT_JUMP_CUTOFF:
            self.vy = settings.SHORT_JUMP_CUTOFF

        # Apply gravity only while airborne. Landing resolution (run after
        # this update by the scene) zeroes vy and re-flags grounded as needed.
        if not self.grounded:
            self.vy = apply_gravity(self.vy, settings.GRAVITY, dt)

        # Semi-implicit Euler integration of position.
        self.x += self.vx * dt
        self.y += self.vy * dt

        # Clamp horizontally so the player can't leave the play column.
        # No wrap here — the cat tower has rigid side walls.
        if self.x < 0:
            self.x = 0.0
        if self.x + settings.PLAYER_WIDTH > settings.INTERNAL_WIDTH:
            self.x = settings.INTERNAL_WIDTH - settings.PLAYER_WIDTH

    # ---------------------------------------------------------------- helpers

    @property
    def rect(self) -> Rect:
        """Player AABB used for landing and pickup/hazard tests."""
        return Rect(x=self.x, y=self.y, w=settings.PLAYER_WIDTH, h=settings.PLAYER_HEIGHT)

    @property
    def altitude_m(self) -> int:
        """Current climb altitude in meters (display-only).

        Returns:
            Floor of ``y / PIXELS_PER_METER``, clamped to >= 0.
        """
        return max(0, int(self.y) // settings.PIXELS_PER_METER)

    def take_hit(self) -> None:
        """Apply one point of damage unless invulnerable.

        I-frames AND catnip invincibility both block damage. After a
        successful hit, ``iframe_timer`` is set to provide a brief
        post-damage window so the player can disengage from the hazard
        without immediately taking another hit (a "hit-stop" of sorts).
        """
        # Skip the hit entirely if either immunity timer is active.
        if self.iframe_timer > 0 or self.invincible_timer > 0:
            return
        self.lives -= 1
        self.iframe_timer = settings.IFRAME_DURATION

    @property
    def is_alive(self) -> bool:
        """True while the player has any lives left.

        Returns:
            True if ``lives >= 0``. Note this allows the very last hit to
            still render as alive at lives == 0; the run ends only once
            lives go negative.
        """
        return self.lives >= 0
