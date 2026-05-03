# Dongle's Adventure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> 한국어 버전: [2026-05-03-dongles-adventure.ko.md](./2026-05-03-dongles-adventure.ko.md)

**Goal:** Build a Pygame-based vertical-scrolling endless platformer where Dongle (a white Persian cat) climbs an infinite cat tower, in the spirit of MSX *Magical Tree* + Doodle Jump.

**Architecture:**
- Internal canvas of **360×540 px** rendered every frame, then 2x integer-scaled to a 720×1080 game area centered in a 1920×1080 window. 600 px wide HUD panels flank both sides.
- Scene-stack pattern (Menu / Game / GameOver), each scene implements `handle_event(e)`, `update(dt)`, `draw(surface)`.
- World uses **altitude-up positive** coordinates (`world_y` increases with height). Camera converts to screen via `screen_y = camera.y_top - world_y`. Camera's `y_top` is monotonically non-decreasing.
- World content is generated in **chunks** (one chunk = one screen height = 540 internal px) with deterministic seeding for testability.
- Entities are plain Python classes with `update(dt, world)` / `draw(surface, camera)`; physics utilities are **pure functions** for unit testability.

**Tech Stack:** Python 3.11+, Pygame 2.5+, pytest (dev). Mirrors the layout of the sibling `galaga-clone` project.

**Coordinate / unit conventions (LOCK BEFORE CODING):**
- All game logic uses internal pixel units of the 360×540 canvas.
- `world_y` is altitude in pixels (up = positive). Player starts at `world_y = 0`.
- Display altitude in meters: `meters = world_y // PIXELS_PER_METER` where `PIXELS_PER_METER = 10`. So 50m = 500 px, 500m = 5000 px.
- All hazard altitude gates in this plan use *meters* and convert via `PIXELS_PER_METER`.

---

## File Structure

Created during implementation:

```
dongles-adventure/
├── main.py                       # Entry point
├── pyproject.toml
├── README.md
├── settings.py                   # All tunable constants
├── assets/
│   ├── sprites/                  # (placeholders generated at runtime)
│   ├── sounds/                   # placeholder SFX (silent / generated tones)
│   └── music/                    # placeholder BGM
├── engine/
│   ├── __init__.py
│   ├── physics.py                # Pure functions: gravity, AABB
│   ├── camera.py                 # Camera with monotonic y_top
│   └── input.py                  # Held-key tracking helper
├── entities/
│   ├── __init__.py
│   ├── player.py                 # Dongle
│   ├── platforms.py              # Platform classes
│   ├── hazards.py                # Hazard classes
│   └── items.py                  # Pickup items
├── world/
│   ├── __init__.py
│   ├── difficulty.py             # Altitude → difficulty params
│   └── generator.py              # Chunk generation
├── scenes/
│   ├── __init__.py
│   ├── menu.py
│   ├── game.py
│   └── gameover.py
├── data/
│   └── highscore.json
└── tests/
    ├── __init__.py
    ├── test_physics.py
    ├── test_camera.py
    ├── test_player.py
    ├── test_platforms.py
    ├── test_difficulty.py
    └── test_generator.py
```

---

## Task 1: Project scaffolding + window boot

**Files:**
- Create: `pyproject.toml`
- Create: `settings.py`
- Create: `main.py`
- Create: `engine/__init__.py`, `entities/__init__.py`, `world/__init__.py`, `scenes/__init__.py`, `tests/__init__.py`
- Create: `assets/sprites/.gitkeep`, `assets/sounds/.gitkeep`, `assets/music/.gitkeep`, `data/.gitkeep`
- Create: `README.md`

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "dongles-adventure"
version = "0.1.0"
description = "Endless vertical platformer starring Dongle the white Persian cat (Magical Tree-style)"
requires-python = ">=3.11"
dependencies = [
    "pygame>=2.5.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "ruff>=0.4.0",
]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "B", "UP"]
ignore = ["E501"]

[tool.ruff.format]
quote-style = "double"

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
```

- [ ] **Step 2: Create `settings.py` with locked constants**

```python
"""All tunable constants for Dongle's Adventure.

Values live here so gameplay tuning never requires touching logic.
"""
from __future__ import annotations

# --- Display ---------------------------------------------------------------
WINDOW_WIDTH = 1920
WINDOW_HEIGHT = 1080

INTERNAL_WIDTH = 360
INTERNAL_HEIGHT = 540
GAME_SCALE = 2  # internal -> displayed game area (720x1080)

GAME_AREA_WIDTH = INTERNAL_WIDTH * GAME_SCALE        # 720
GAME_AREA_HEIGHT = INTERNAL_HEIGHT * GAME_SCALE      # 1080
GAME_AREA_X = (WINDOW_WIDTH - GAME_AREA_WIDTH) // 2  # 600
GAME_AREA_Y = 0

LEFT_HUD_X = 0
LEFT_HUD_WIDTH = GAME_AREA_X                         # 600
RIGHT_HUD_X = GAME_AREA_X + GAME_AREA_WIDTH          # 1320
RIGHT_HUD_WIDTH = WINDOW_WIDTH - RIGHT_HUD_X         # 600

FPS = 60

# --- World units -----------------------------------------------------------
PIXELS_PER_METER = 10  # 1m altitude = 10 internal px

# --- Player physics --------------------------------------------------------
PLAYER_WIDTH = 32
PLAYER_HEIGHT = 32
MOVE_SPEED = 180.0          # px/s horizontal
GRAVITY = 1200.0            # px/s^2 (downward; subtracts world_y)
JUMP_VELOCITY = 520.0       # px/s initial upward velocity (full jump)
SHORT_JUMP_CUTOFF = 240.0   # px/s; on Space release while rising, clamp upward velocity to this
COYOTE_TIME = 0.08          # seconds after leaving a platform you can still jump
JUMP_BUFFER = 0.10          # seconds before landing where Space input still triggers jump

# --- Camera ----------------------------------------------------------------
PLAYER_SCREEN_OFFSET_FROM_TOP = 324  # px in internal canvas (60% of 540)

# --- Difficulty / altitude bands ------------------------------------------
HAZARD_GATE_YARN = 0      # m
HAZARD_GATE_MOUSE = 50    # m
HAZARD_GATE_CROW = 150    # m
HAZARD_GATE_DOG = 300     # m
HAZARD_GATE_SPRAY = 300   # m
HAZARD_GATE_VACUUM = 500  # m

# --- Lives -----------------------------------------------------------------
START_LIVES = 1
MAX_LIVES = 3
IFRAME_DURATION = 1.5  # seconds after a non-lethal hit

# --- Files -----------------------------------------------------------------
HIGHSCORE_PATH = "data/highscore.json"

# --- Colors (placeholder palette) -----------------------------------------
COLOR_BG = (24, 18, 36)
COLOR_GAME_BG = (60, 80, 130)
COLOR_HUD_BG = (16, 12, 24)
COLOR_HUD_TEXT = (235, 230, 215)
COLOR_HUD_ACCENT = (255, 200, 80)
COLOR_PLATFORM = (180, 130, 90)
COLOR_PLAYER = (240, 240, 240)
COLOR_HAZARD = (220, 80, 80)
COLOR_ITEM = (120, 220, 120)

# --- Key bindings ----------------------------------------------------------
import pygame  # noqa: E402

KEY_LEFT = pygame.K_LEFT
KEY_RIGHT = pygame.K_RIGHT
KEY_JUMP = pygame.K_SPACE
KEY_PAUSE = pygame.K_ESCAPE
KEY_RESTART = pygame.K_r
```

- [ ] **Step 3: Create empty `__init__.py` files**

```bash
mkdir -p engine entities world scenes tests assets/sprites assets/sounds assets/music data
touch engine/__init__.py entities/__init__.py world/__init__.py scenes/__init__.py tests/__init__.py
touch assets/sprites/.gitkeep assets/sounds/.gitkeep assets/music/.gitkeep data/.gitkeep
```

- [ ] **Step 4: Create minimal `main.py` that opens the window**

```python
"""Dongle's Adventure - entry point."""
from __future__ import annotations

import sys

import pygame

import settings


def main() -> int:
    pygame.init()
    screen = pygame.display.set_mode((settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT))
    pygame.display.set_caption("Dongle's Adventure")
    clock = pygame.time.Clock()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False

        screen.fill(settings.COLOR_BG)
        # Game area placeholder
        pygame.draw.rect(
            screen,
            settings.COLOR_GAME_BG,
            (settings.GAME_AREA_X, settings.GAME_AREA_Y, settings.GAME_AREA_WIDTH, settings.GAME_AREA_HEIGHT),
        )
        # HUD panels
        pygame.draw.rect(
            screen, settings.COLOR_HUD_BG,
            (settings.LEFT_HUD_X, 0, settings.LEFT_HUD_WIDTH, settings.WINDOW_HEIGHT),
        )
        pygame.draw.rect(
            screen, settings.COLOR_HUD_BG,
            (settings.RIGHT_HUD_X, 0, settings.RIGHT_HUD_WIDTH, settings.WINDOW_HEIGHT),
        )

        pygame.display.flip()
        clock.tick(settings.FPS)

    pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Create `README.md`**

```markdown
# Dongle's Adventure

Endless vertical platformer starring Dongle, a white Persian cat scaling an infinite cat tower. Inspired by MSX *Magical Tree* (Konami, 1984).

## Run
```
python -m venv .venv
.venv\Scripts\activate    # Windows
pip install -e .[dev]
python main.py
```

## Controls
- ← / → : Move
- Space : Jump (hold for higher)
- Esc   : Pause / Quit
- R     : Restart on game over
```

- [ ] **Step 6: Install and smoke-test the window**

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .[dev]
python main.py
```
Expected: 1920×1080 window opens with three colored panels (left HUD, blue game area, right HUD). Closes on Esc or window-close. **Pygame may scale the window for HiDPI screens; that is fine.**

- [ ] **Step 7: Commit**

```bash
git add .
git commit -m "feat: scaffold project and boot a 1920x1080 window with HUD frame"
```

---

## Task 2: Physics primitives (TDD)

**Files:**
- Create: `engine/physics.py`
- Test: `tests/test_physics.py`

The physics module exposes pure functions only — no global state, no Pygame surfaces. Coordinates use `world_y` UP-positive. Note: gravity DECREASES `world_y` velocity over time because falling reduces altitude.

- [ ] **Step 1: Write failing tests**

`tests/test_physics.py`:
```python
from engine.physics import apply_gravity, aabb_overlap, Rect


def test_apply_gravity_decreases_vy_proportional_to_dt() -> None:
    # vy is altitude rate-of-change (up = positive). Gravity pulls altitude down.
    new_vy = apply_gravity(vy=100.0, gravity=1200.0, dt=0.5)
    assert new_vy == 100.0 - 1200.0 * 0.5  # -500.0


def test_apply_gravity_zero_dt_returns_same_vy() -> None:
    assert apply_gravity(vy=42.0, gravity=1200.0, dt=0.0) == 42.0


def test_aabb_overlap_true_when_intersecting() -> None:
    a = Rect(x=0, y=0, w=10, h=10)
    b = Rect(x=5, y=5, w=10, h=10)
    assert aabb_overlap(a, b) is True


def test_aabb_overlap_false_when_only_touching_edges() -> None:
    # Touching but not overlapping should be False (strict overlap).
    a = Rect(x=0, y=0, w=10, h=10)
    b = Rect(x=10, y=0, w=10, h=10)
    assert aabb_overlap(a, b) is False


def test_aabb_overlap_false_when_separated() -> None:
    a = Rect(x=0, y=0, w=10, h=10)
    b = Rect(x=20, y=20, w=10, h=10)
    assert aabb_overlap(a, b) is False
```

- [ ] **Step 2: Run tests to confirm failure**

```bash
pytest tests/test_physics.py -v
```
Expected: ImportError / ModuleNotFoundError (`engine.physics` doesn't exist yet).

- [ ] **Step 3: Implement `engine/physics.py`**

```python
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
```

- [ ] **Step 4: Re-run tests to confirm pass**

```bash
pytest tests/test_physics.py -v
```
Expected: all 5 pass.

- [ ] **Step 5: Commit**

```bash
git add engine/physics.py tests/test_physics.py
git commit -m "feat(engine): pure-function gravity and AABB overlap primitives"
```

---

## Task 3: Camera (TDD)

**Files:**
- Create: `engine/camera.py`
- Test: `tests/test_camera.py`

- [ ] **Step 1: Write failing tests**

`tests/test_camera.py`:
```python
from engine.camera import Camera


def test_camera_initial_y_top_is_screen_height() -> None:
    # On boot, top-of-screen world altitude equals one screen height (player at y=0
    # sits PLAYER_SCREEN_OFFSET_FROM_TOP from top).
    cam = Camera(screen_height=540, player_offset_from_top=324)
    cam.follow(player_world_y=0.0)
    assert cam.y_top == 324.0  # 0 + 324 (player's screen_y target)


def test_camera_y_top_increases_when_player_climbs() -> None:
    cam = Camera(screen_height=540, player_offset_from_top=324)
    cam.follow(player_world_y=0.0)
    cam.follow(player_world_y=200.0)
    assert cam.y_top == 524.0  # 200 + 324


def test_camera_y_top_never_decreases_when_player_falls() -> None:
    cam = Camera(screen_height=540, player_offset_from_top=324)
    cam.follow(player_world_y=500.0)  # high
    high = cam.y_top
    cam.follow(player_world_y=100.0)  # then fell
    assert cam.y_top == high


def test_world_to_screen_y_inverts_axis() -> None:
    cam = Camera(screen_height=540, player_offset_from_top=324)
    cam.follow(player_world_y=0.0)  # y_top = 324
    # World point at y=0 should be at screen y = 324 (player position)
    assert cam.world_to_screen_y(0.0) == 324.0
    # World point at y=324 should be at screen y = 0 (top of screen)
    assert cam.world_to_screen_y(324.0) == 0.0


def test_is_below_screen_when_world_y_more_than_screen_height_below_top() -> None:
    cam = Camera(screen_height=540, player_offset_from_top=324)
    cam.follow(player_world_y=0.0)  # y_top = 324; bottom at y_top - 540 = -216
    assert cam.is_below_screen(world_y=-217.0) is True
    assert cam.is_below_screen(world_y=-216.0) is False
```

- [ ] **Step 2: Run tests to confirm failure**

```bash
pytest tests/test_camera.py -v
```
Expected: ModuleNotFoundError.

- [ ] **Step 3: Implement `engine/camera.py`**

```python
"""Vertical-scroll camera for Dongle's Adventure.

The camera tracks the maximum altitude reached. It never scrolls back down.
"""
from __future__ import annotations


class Camera:
    """Tracks `y_top`: world_y altitude that maps to screen y=0."""

    def __init__(self, screen_height: int, player_offset_from_top: int) -> None:
        self.screen_height = screen_height
        self.player_offset_from_top = player_offset_from_top
        self.y_top: float = 0.0

    def follow(self, player_world_y: float) -> None:
        """Update y_top to keep player at the configured screen offset, monotonically."""
        target = player_world_y + self.player_offset_from_top
        if target > self.y_top:
            self.y_top = target

    def world_to_screen_y(self, world_y: float) -> float:
        """Convert world altitude to screen y (top-of-screen is 0; increases downward)."""
        return self.y_top - world_y

    def is_below_screen(self, world_y: float) -> bool:
        """True when a world point is below the current visible region."""
        bottom_world_y = self.y_top - self.screen_height
        return world_y < bottom_world_y
```

- [ ] **Step 4: Run tests to confirm pass**

```bash
pytest tests/test_camera.py -v
```
Expected: all 5 pass.

- [ ] **Step 5: Commit**

```bash
git add engine/camera.py tests/test_camera.py
git commit -m "feat(engine): monotonic vertical-scroll camera"
```

---

## Task 4: Player entity with jump (TDD)

**Files:**
- Create: `entities/player.py`
- Test: `tests/test_player.py`

The player owns: world position, velocity, grounded flag, lives, i-frame timer. Input handling is decoupled — the scene calls `player.set_input(left_held, right_held, jump_pressed_this_frame, jump_held)`. This keeps Pygame out of the entity for testability.

- [ ] **Step 1: Write failing tests**

`tests/test_player.py`:
```python
import pytest

from entities.player import Player


def make_player() -> Player:
    return Player(start_x=180.0, start_y=0.0)


def test_player_starts_at_initial_position_with_zero_velocity() -> None:
    p = make_player()
    assert (p.x, p.y) == (180.0, 0.0)
    assert (p.vx, p.vy) == (0.0, 0.0)


def test_player_moves_right_when_right_held() -> None:
    p = make_player()
    p.set_input(left_held=False, right_held=True, jump_pressed=False, jump_held=False)
    p.update(dt=0.1)
    assert p.x > 180.0
    assert p.vx > 0


def test_player_left_overrides_right_when_both_held() -> None:
    # Spec: holding both = move left (last direction wins is ambiguous; we pick left).
    p = make_player()
    p.set_input(left_held=True, right_held=True, jump_pressed=False, jump_held=False)
    p.update(dt=0.1)
    assert p.vx < 0


def test_player_falls_under_gravity_when_airborne() -> None:
    p = make_player()
    p.grounded = False
    p.update(dt=0.1)
    assert p.vy < 0  # falling (altitude decreasing)
    assert p.y < 0


def test_player_jumps_when_grounded_and_jump_pressed() -> None:
    p = make_player()
    p.grounded = True
    p.set_input(left_held=False, right_held=False, jump_pressed=True, jump_held=True)
    p.update(dt=1 / 60)
    assert p.vy > 0  # rising
    assert p.grounded is False


def test_player_short_jump_when_jump_released_during_ascent() -> None:
    p = make_player()
    p.grounded = True
    p.set_input(left_held=False, right_held=False, jump_pressed=True, jump_held=True)
    p.update(dt=1 / 60)
    high_vy = p.vy
    # Release jump while still rising
    p.set_input(left_held=False, right_held=False, jump_pressed=False, jump_held=False)
    p.update(dt=1 / 60)
    # vy should have been clamped to SHORT_JUMP_CUTOFF (240.0) if it was higher
    assert p.vy <= 240.0
    assert p.vy < high_vy


def test_jump_buffer_triggers_jump_when_landing_within_window() -> None:
    p = make_player()
    p.grounded = False
    # Press jump while airborne
    p.set_input(left_held=False, right_held=False, jump_pressed=True, jump_held=True)
    p.update(dt=1 / 60)
    assert p.vy <= 0 or p.vy < 520.0  # didn't fully jump because not grounded
    # Land within buffer window
    p.grounded = True
    p.set_input(left_held=False, right_held=False, jump_pressed=False, jump_held=True)
    p.update(dt=1 / 60)
    assert p.vy > 0  # buffered jump fired


def test_coyote_time_allows_jump_shortly_after_leaving_platform() -> None:
    p = make_player()
    p.grounded = True
    # Step once grounded so coyote timer resets
    p.set_input(left_held=False, right_held=False, jump_pressed=False, jump_held=False)
    p.update(dt=1 / 60)
    # Walk off
    p.grounded = False
    p.update(dt=0.05)  # within COYOTE_TIME (0.08s)
    p.set_input(left_held=False, right_held=False, jump_pressed=True, jump_held=True)
    p.update(dt=1 / 60)
    assert p.vy > 0
```

- [ ] **Step 2: Run tests to confirm failure**

```bash
pytest tests/test_player.py -v
```
Expected: ModuleNotFoundError.

- [ ] **Step 3: Implement `entities/player.py`**

```python
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
```

- [ ] **Step 4: Run tests to confirm pass**

```bash
pytest tests/test_player.py -v
```
Expected: all 8 pass.

- [ ] **Step 5: Commit**

```bash
git add entities/player.py tests/test_player.py
git commit -m "feat(player): horizontal control, gravity, variable jump, coyote, buffer"
```

---

## Task 5: Platforms + landing collision (TDD)

**Files:**
- Create: `entities/platforms.py`
- Test: `tests/test_platforms.py`

This task ships the **Standard** platform only. Variant types come in Task 11.

The collision rule for landing: a player is considered to have landed on a platform this frame if (a) AABBs overlap after movement, (b) `vy <= 0` (descending or stationary), and (c) the player's bottom in the **previous** frame was at or above the platform's top. On a successful landing, snap player.y to platform.top, set vy=0, set grounded=True.

- [ ] **Step 1: Write failing tests**

`tests/test_platforms.py`:
```python
from entities.platforms import StandardPlatform, resolve_landings
from entities.player import Player


def test_player_falling_lands_on_platform_below() -> None:
    p = Player(start_x=100.0, start_y=20.0)  # bottom at y=20
    p.vy = -100.0  # descending
    p.grounded = False
    plat = StandardPlatform(x=80.0, y=10.0, w=60.0, h=8.0)  # top at y=18
    # Move player down: prev_bottom=20, new_bottom < 18
    prev_bottom = p.y
    p.y = 15.0  # moved down past platform top
    resolve_landings(p, [plat], prev_bottom_y=prev_bottom)
    assert p.grounded is True
    assert p.vy == 0.0
    assert p.y == plat.top  # snapped


def test_player_rising_through_platform_does_not_land() -> None:
    # One-way platforms: player can pass upward through them.
    p = Player(start_x=100.0, start_y=12.0)
    p.vy = 200.0  # rising
    p.grounded = False
    plat = StandardPlatform(x=80.0, y=10.0, w=60.0, h=8.0)  # top at 18
    prev_bottom = p.y
    p.y = 20.0
    resolve_landings(p, [plat], prev_bottom_y=prev_bottom)
    assert p.grounded is False


def test_player_misses_platform_when_offset_horizontally() -> None:
    p = Player(start_x=300.0, start_y=20.0)
    p.vy = -100.0
    p.grounded = False
    plat = StandardPlatform(x=80.0, y=10.0, w=60.0, h=8.0)
    prev_bottom = p.y
    p.y = 15.0
    resolve_landings(p, [plat], prev_bottom_y=prev_bottom)
    assert p.grounded is False
```

- [ ] **Step 2: Run tests to confirm failure**

```bash
pytest tests/test_platforms.py -v
```
Expected: ModuleNotFoundError.

- [ ] **Step 3: Implement `entities/platforms.py`**

```python
"""Platforms - the floors Dongle lands on while climbing."""
from __future__ import annotations

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
        pygame.draw.rect(surface, settings.COLOR_PLATFORM, (int(self.x), int(screen_y_top), int(self.w), int(self.h)))


def resolve_landings(player, platforms: Iterable, prev_bottom_y: float) -> None:  # noqa: ANN001
    """Detect downward landings against one-way platforms and snap the player.

    `prev_bottom_y` is the player's y BEFORE this frame's movement (one-way condition).
    """
    if player.vy > 0:  # rising
        return
    for plat in platforms:
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
        plat.on_landed(player)
        break
```

- [ ] **Step 4: Run tests to confirm pass**

```bash
pytest tests/test_platforms.py -v
```
Expected: all 3 pass.

- [ ] **Step 5: Commit**

```bash
git add entities/platforms.py tests/test_platforms.py
git commit -m "feat(platforms): standard platform with one-way landing"
```

---

## Task 6: Game scene with rendering pipeline

**Files:**
- Create: `scenes/__init__.py` (already created in Task 1, leave empty)
- Create: `scenes/game.py`
- Create: `engine/input.py`
- Modify: `main.py`

This task wires player + a hardcoded set of platforms inside the game scene. The internal 360×540 surface is rendered each frame and `pygame.transform.scale` blits it to the 720×1080 game area inside the 1920×1080 window.

- [ ] **Step 1: Create `engine/input.py`**

```python
"""Per-frame input snapshot helper.

Tracks which keys went DOWN this frame in addition to held state, so callers
can distinguish "jump just pressed" from "jump still held".
"""
from __future__ import annotations

import pygame


class InputState:
    def __init__(self) -> None:
        self._pressed_this_frame: set[int] = set()
        self._held: set[int] = set()

    def begin_frame(self) -> None:
        self._pressed_this_frame.clear()

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            self._pressed_this_frame.add(event.key)
            self._held.add(event.key)
        elif event.type == pygame.KEYUP:
            self._held.discard(event.key)

    def is_held(self, key: int) -> bool:
        return key in self._held

    def was_pressed(self, key: int) -> bool:
        return key in self._pressed_this_frame
```

- [ ] **Step 2: Create `scenes/game.py`**

```python
"""Main game scene - climb the cat tower."""
from __future__ import annotations

import pygame

import settings
from engine.camera import Camera
from engine.input import InputState
from entities.platforms import StandardPlatform, resolve_landings
from entities.player import Player


class GameScene:
    def __init__(self) -> None:
        self.player = Player(
            start_x=settings.INTERNAL_WIDTH / 2 - settings.PLAYER_WIDTH / 2,
            start_y=20.0,
        )
        self.player.grounded = True
        self.camera = Camera(
            screen_height=settings.INTERNAL_HEIGHT,
            player_offset_from_top=settings.PLAYER_SCREEN_OFFSET_FROM_TOP,
        )
        # Hardcoded platforms for this task; replaced by generator in Task 10.
        self.platforms: list[StandardPlatform] = [
            StandardPlatform(x=0.0, y=0.0, w=settings.INTERNAL_WIDTH, h=20.0),  # ground
            StandardPlatform(x=40.0, y=80.0, w=80.0, h=8.0),
            StandardPlatform(x=200.0, y=140.0, w=80.0, h=8.0),
            StandardPlatform(x=80.0, y=220.0, w=80.0, h=8.0),
            StandardPlatform(x=220.0, y=300.0, w=80.0, h=8.0),
            StandardPlatform(x=60.0, y=400.0, w=80.0, h=8.0),
        ]
        self.input = InputState()
        self._internal = pygame.Surface((settings.INTERNAL_WIDTH, settings.INTERNAL_HEIGHT))

    # ---------------- API ----------------

    def handle_event(self, event: pygame.event.Event) -> None:
        self.input.handle_event(event)

    def begin_frame(self) -> None:
        self.input.begin_frame()

    def update(self, dt: float) -> None:
        # Feed player input
        self.player.set_input(
            left_held=self.input.is_held(settings.KEY_LEFT),
            right_held=self.input.is_held(settings.KEY_RIGHT),
            jump_pressed=self.input.was_pressed(settings.KEY_JUMP),
            jump_held=self.input.is_held(settings.KEY_JUMP),
        )

        prev_bottom = self.player.y
        # If player was grounded last frame and didn't just jump, gravity will pull them off;
        # mark airborne so gravity applies, then resolve landings to re-ground if appropriate.
        self.player.grounded = False
        self.player.update(dt)
        resolve_landings(self.player, self.platforms, prev_bottom_y=prev_bottom)

        for plat in self.platforms:
            plat.update(dt)

        self.camera.follow(self.player.y)

    def draw(self, window: pygame.Surface) -> None:
        # 1. Clear internal canvas with sky color
        self._internal.fill(settings.COLOR_GAME_BG)
        # 2. Draw platforms
        for plat in self.platforms:
            plat.draw(self._internal, self.camera)
        # 3. Draw player
        screen_y = self.camera.world_to_screen_y(self.player.y + settings.PLAYER_HEIGHT)
        pygame.draw.rect(
            self._internal,
            settings.COLOR_PLAYER,
            (int(self.player.x), int(screen_y), settings.PLAYER_WIDTH, settings.PLAYER_HEIGHT),
        )
        # 4. Scale up onto window game area
        scaled = pygame.transform.scale(self._internal, (settings.GAME_AREA_WIDTH, settings.GAME_AREA_HEIGHT))
        window.blit(scaled, (settings.GAME_AREA_X, settings.GAME_AREA_Y))
```

- [ ] **Step 3: Update `main.py` to host the scene**

Replace the body of `main()` with:

```python
def main() -> int:
    pygame.init()
    screen = pygame.display.set_mode((settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT))
    pygame.display.set_caption("Dongle's Adventure")
    clock = pygame.time.Clock()

    from scenes.game import GameScene
    scene = GameScene()

    running = True
    while running:
        scene.begin_frame()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            else:
                scene.handle_event(event)

        dt = clock.tick(settings.FPS) / 1000.0
        scene.update(dt)

        screen.fill(settings.COLOR_BG)
        pygame.draw.rect(screen, settings.COLOR_HUD_BG,
                         (settings.LEFT_HUD_X, 0, settings.LEFT_HUD_WIDTH, settings.WINDOW_HEIGHT))
        pygame.draw.rect(screen, settings.COLOR_HUD_BG,
                         (settings.RIGHT_HUD_X, 0, settings.RIGHT_HUD_WIDTH, settings.WINDOW_HEIGHT))
        scene.draw(screen)

        pygame.display.flip()

    pygame.quit()
    return 0
```

- [ ] **Step 4: Manual smoke test**

```bash
python main.py
```
Expected: Player (white square) sits on the floor; ← / → moves; Space jumps; player can land on the higher hardcoded platforms; camera scrolls up as you climb. If the player goes below screen they keep falling forever (Task 8 will handle game over).

- [ ] **Step 5: Commit**

```bash
git add scenes/game.py engine/input.py main.py
git commit -m "feat(game): wire player+platforms into a scaled-render game scene"
```

---

## Task 7: HUD layout placeholder text

**Files:**
- Create: `scenes/_hud.py`
- Modify: `main.py`

A minimal HUD module renders the panels' static frame and labels. Live values come in Task 19; this task just locks the layout.

- [ ] **Step 1: Create `scenes/_hud.py`**

```python
"""Side HUD rendering for the 1920x1080 layout."""
from __future__ import annotations

import pygame

import settings


class Hud:
    def __init__(self) -> None:
        self.font_large = pygame.font.SysFont("consolas", 48, bold=True)
        self.font_med = pygame.font.SysFont("consolas", 28)
        self.font_small = pygame.font.SysFont("consolas", 20)

    def draw(self, window: pygame.Surface, *, altitude_m: int, best_m: int, lives: int,
             tuna: int, next_hazard_label: str, next_hazard_m: int) -> None:
        self._draw_left(window, altitude_m=altitude_m, best_m=best_m, lives=lives)
        self._draw_right(window, altitude_m=altitude_m, tuna=tuna,
                         next_hazard_label=next_hazard_label, next_hazard_m=next_hazard_m)

    # ---------------------------------------------------------------- left

    def _draw_left(self, window: pygame.Surface, *, altitude_m: int, best_m: int, lives: int) -> None:
        x0 = settings.LEFT_HUD_X + 40
        # ALTITUDE
        label = self.font_small.render("ALTITUDE", True, settings.COLOR_HUD_TEXT)
        window.blit(label, (x0, 60))
        value = self.font_large.render(f"{altitude_m} m", True, settings.COLOR_HUD_ACCENT)
        window.blit(value, (x0, 90))
        # BEST
        best = self.font_med.render(f"BEST  {best_m} m", True, settings.COLOR_HUD_TEXT)
        window.blit(best, (x0, 170))
        # LIVES
        lbl = self.font_small.render("LIVES", True, settings.COLOR_HUD_TEXT)
        window.blit(lbl, (x0, 240))
        for i in range(settings.MAX_LIVES):
            color = settings.COLOR_HUD_ACCENT if i < lives else (60, 60, 60)
            pygame.draw.circle(window, color, (x0 + 20 + i * 50, 290), 18)
        # CONTROLS
        ctl_y = 900
        for line in ["CONTROLS", "  <- ->  Move", "  SPACE  Jump", "  ESC    Pause"]:
            txt = self.font_small.render(line, True, settings.COLOR_HUD_TEXT)
            window.blit(txt, (x0, ctl_y))
            ctl_y += 30

    # ---------------------------------------------------------------- right

    def _draw_right(self, window: pygame.Surface, *, altitude_m: int, tuna: int,
                    next_hazard_label: str, next_hazard_m: int) -> None:
        x0 = settings.RIGHT_HUD_X + 40
        # ALTITUDE SCALE: vertical line with marks at 50/150/300/500m and arrow at current
        scale_top_y = 100
        scale_bot_y = 800
        scale_top_m = 600  # show 0..600m scale
        pygame.draw.line(window, settings.COLOR_HUD_TEXT,
                         (x0 + 60, scale_top_y), (x0 + 60, scale_bot_y), 2)
        for mark_m in (50, 150, 300, 500):
            ratio = mark_m / scale_top_m
            y = int(scale_bot_y - (scale_bot_y - scale_top_y) * ratio)
            pygame.draw.line(window, settings.COLOR_HUD_TEXT, (x0 + 50, y), (x0 + 70, y), 2)
            txt = self.font_small.render(f"{mark_m}m", True, settings.COLOR_HUD_TEXT)
            window.blit(txt, (x0 + 80, y - 12))
        # YOU arrow
        you_ratio = min(1.0, altitude_m / scale_top_m)
        you_y = int(scale_bot_y - (scale_bot_y - scale_top_y) * you_ratio)
        pygame.draw.polygon(
            window, settings.COLOR_HUD_ACCENT,
            [(x0 + 30, you_y - 8), (x0 + 30, you_y + 8), (x0 + 50, you_y)],
        )
        you = self.font_small.render(f"YOU {altitude_m}m", True, settings.COLOR_HUD_ACCENT)
        window.blit(you, (x0 - 20, you_y + 14))

        # NEXT HAZARD
        nh = self.font_small.render(f"NEXT  {next_hazard_label} @ {next_hazard_m}m",
                                     True, settings.COLOR_HUD_TEXT)
        window.blit(nh, (x0, 850))
        # TUNA
        tn = self.font_med.render(f"TUNA  {tuna}", True, settings.COLOR_HUD_TEXT)
        window.blit(tn, (x0, 900))
        # HINT
        hint = self.font_small.render("R: Restart", True, settings.COLOR_HUD_TEXT)
        window.blit(hint, (x0, 970))
```

- [ ] **Step 2: Wire HUD into `main.py`**

Replace the per-frame draw section so it calls the HUD with placeholder data sourced from the player. Find the `screen.fill(settings.COLOR_BG)` block and replace through `scene.draw(screen)` with:

```python
        screen.fill(settings.COLOR_BG)
        scene.draw(screen)
        hud.draw(
            screen,
            altitude_m=scene.player.altitude_m,
            best_m=0,
            lives=scene.player.lives,
            tuna=0,
            next_hazard_label="Yarn",
            next_hazard_m=0,
        )
```

And add at the top of `main()` after `clock = pygame.time.Clock()`:

```python
    pygame.font.init()
    from scenes._hud import Hud
    hud = Hud()
```

- [ ] **Step 3: Manual smoke test**

```bash
python main.py
```
Expected: HUD panels show static labels and an empty altitude scale with a YOU arrow tracking the player's current meters.

- [ ] **Step 4: Commit**

```bash
git add scenes/_hud.py main.py
git commit -m "feat(hud): side panels with altitude, lives, and altitude scale"
```

---

## Task 8: Fall death + Game Over scene + Restart

**Files:**
- Create: `scenes/gameover.py`
- Modify: `scenes/game.py`
- Modify: `main.py`

The Game Over flow uses a tiny scene-stack: the main loop holds `current_scene` and switches on a callback returned from `update`.

- [ ] **Step 1: Add a "dead" signal to `GameScene`**

Modify `scenes/game.py` `update()` so that after `camera.follow`, it checks if the player has fallen below the visible region:

Append at end of `update`:
```python
        # Death by fall: player below screen bottom
        if self.camera.is_below_screen(self.player.y + settings.PLAYER_HEIGHT):
            self.dead = True
```

Add `self.dead = False` in `__init__`.

- [ ] **Step 2: Create `scenes/gameover.py`**

```python
"""Game Over scene - shows result and waits for restart."""
from __future__ import annotations

import pygame

import settings


class GameOverScene:
    def __init__(self, *, altitude_m: int, best_m: int, new_record: bool) -> None:
        self.altitude_m = altitude_m
        self.best_m = best_m
        self.new_record = new_record
        self.restart_requested = False
        pygame.font.init()
        self.font_huge = pygame.font.SysFont("consolas", 72, bold=True)
        self.font_med = pygame.font.SysFont("consolas", 32)

    def begin_frame(self) -> None:
        pass

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == settings.KEY_RESTART:
            self.restart_requested = True

    def update(self, dt: float) -> None:
        pass

    def draw(self, window: pygame.Surface) -> None:
        # Dim the game area
        overlay = pygame.Surface((settings.GAME_AREA_WIDTH, settings.GAME_AREA_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        window.blit(overlay, (settings.GAME_AREA_X, settings.GAME_AREA_Y))

        cx = settings.GAME_AREA_X + settings.GAME_AREA_WIDTH // 2
        cy = settings.GAME_AREA_Y + settings.GAME_AREA_HEIGHT // 2

        title = self.font_huge.render("GAME OVER", True, settings.COLOR_HUD_ACCENT)
        window.blit(title, title.get_rect(center=(cx, cy - 100)))

        result = self.font_med.render(f"You reached {self.altitude_m} m", True, settings.COLOR_HUD_TEXT)
        window.blit(result, result.get_rect(center=(cx, cy - 20)))

        if self.new_record:
            rec = self.font_med.render(f"NEW RECORD!", True, settings.COLOR_HUD_ACCENT)
            window.blit(rec, rec.get_rect(center=(cx, cy + 20)))
        else:
            best = self.font_med.render(f"Best: {self.best_m} m", True, settings.COLOR_HUD_TEXT)
            window.blit(best, best.get_rect(center=(cx, cy + 20)))

        hint = self.font_med.render("Press R to restart", True, settings.COLOR_HUD_TEXT)
        window.blit(hint, hint.get_rect(center=(cx, cy + 100)))
```

- [ ] **Step 3: Update `main.py` for scene switching**

Replace the main loop body so it manages `scene` and `gameover`:

```python
    from scenes.game import GameScene
    from scenes.gameover import GameOverScene

    scene = GameScene()
    gameover: GameOverScene | None = None

    running = True
    while running:
        scene.begin_frame()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            else:
                if gameover is not None:
                    gameover.handle_event(event)
                else:
                    scene.handle_event(event)

        dt = clock.tick(settings.FPS) / 1000.0
        if gameover is None:
            scene.update(dt)
            if scene.dead:
                gameover = GameOverScene(altitude_m=scene.player.altitude_m, best_m=0, new_record=False)
        else:
            gameover.update(dt)
            if gameover.restart_requested:
                scene = GameScene()
                gameover = None

        screen.fill(settings.COLOR_BG)
        scene.draw(screen)
        hud.draw(screen,
                 altitude_m=scene.player.altitude_m, best_m=0, lives=scene.player.lives,
                 tuna=0, next_hazard_label="Yarn", next_hazard_m=0)
        if gameover is not None:
            gameover.draw(screen)

        pygame.display.flip()
```

- [ ] **Step 4: Manual smoke test**

```bash
python main.py
```
Expected: Walk off the bottom or jump and miss → "GAME OVER" overlay appears with reached altitude. Pressing R starts a fresh run.

- [ ] **Step 5: Commit**

```bash
git add scenes/game.py scenes/gameover.py main.py
git commit -m "feat(scenes): fall death and Game Over with R-to-restart"
```

---

## Task 9: Difficulty curve (TDD)

**Files:**
- Create: `world/difficulty.py`
- Test: `tests/test_difficulty.py`

The difficulty function maps altitude (in meters) to generation parameters used by the chunk generator and hazard scheduler.

- [ ] **Step 1: Write failing tests**

`tests/test_difficulty.py`:
```python
from world.difficulty import difficulty_for_altitude


def test_starting_altitude_uses_easy_params() -> None:
    p = difficulty_for_altitude(altitude_m=0)
    assert p.platforms_per_chunk >= 5
    assert p.hazard_density == 0.0
    assert "yarn" in p.hazard_pool


def test_50m_unlocks_mouse() -> None:
    p = difficulty_for_altitude(altitude_m=50)
    assert "mouse" in p.hazard_pool


def test_150m_unlocks_crow() -> None:
    p = difficulty_for_altitude(altitude_m=150)
    assert "crow" in p.hazard_pool


def test_300m_unlocks_dog_and_spray() -> None:
    p = difficulty_for_altitude(altitude_m=300)
    assert "dog" in p.hazard_pool and "spray" in p.hazard_pool


def test_500m_unlocks_vacuum_and_max_density() -> None:
    p = difficulty_for_altitude(altitude_m=500)
    assert "vacuum" in p.hazard_pool
    assert p.hazard_density >= 0.5


def test_platforms_per_chunk_decreases_monotonically() -> None:
    counts = [difficulty_for_altitude(m).platforms_per_chunk for m in range(0, 600, 50)]
    assert all(b <= a for a, b in zip(counts, counts[1:]))


def test_hazard_density_increases_monotonically() -> None:
    densities = [difficulty_for_altitude(m).hazard_density for m in range(0, 600, 50)]
    assert all(b >= a for a, b in zip(densities, densities[1:]))
```

- [ ] **Step 2: Run tests to confirm failure**

```bash
pytest tests/test_difficulty.py -v
```

- [ ] **Step 3: Implement `world/difficulty.py`**

```python
"""Altitude -> generation parameter mapping."""
from __future__ import annotations

from dataclasses import dataclass

import settings


@dataclass(frozen=True)
class DifficultyParams:
    platforms_per_chunk: int     # how many platforms to place in one chunk
    risky_platform_ratio: float  # 0..1: fraction of placed platforms that are non-standard
    hazard_density: float        # 0..1: probability that a hazard spawns in a chunk
    hazard_pool: tuple[str, ...] # which hazard kinds are eligible


def difficulty_for_altitude(altitude_m: int) -> DifficultyParams:
    pool: list[str] = ["yarn"]
    if altitude_m >= settings.HAZARD_GATE_MOUSE:
        pool.append("mouse")
    if altitude_m >= settings.HAZARD_GATE_CROW:
        pool.append("crow")
    if altitude_m >= settings.HAZARD_GATE_DOG:
        pool.append("dog")
    if altitude_m >= settings.HAZARD_GATE_SPRAY:
        pool.append("spray")
    if altitude_m >= settings.HAZARD_GATE_VACUUM:
        pool.append("vacuum")

    # Linear interpolation across 0..500m, clamped beyond.
    t = min(1.0, altitude_m / 500.0)

    platforms_per_chunk = round(7 - 2 * t)            # 7 -> 5
    risky_ratio = 0.0 + 0.6 * t                        # 0.0 -> 0.6
    hazard_density = 0.0 + 0.6 * t                     # 0.0 -> 0.6

    # 500m+ guarantees vacuum hazard density floor of 0.5
    if altitude_m >= settings.HAZARD_GATE_VACUUM:
        hazard_density = max(hazard_density, 0.5)

    return DifficultyParams(
        platforms_per_chunk=platforms_per_chunk,
        risky_platform_ratio=risky_ratio,
        hazard_density=hazard_density,
        hazard_pool=tuple(pool),
    )
```

- [ ] **Step 4: Run tests to confirm pass**

```bash
pytest tests/test_difficulty.py -v
```

- [ ] **Step 5: Commit**

```bash
git add world/difficulty.py tests/test_difficulty.py
git commit -m "feat(world): altitude->difficulty params with hazard gates"
```

---

## Task 10: Procedural chunk generator (TDD)

**Files:**
- Create: `world/generator.py`
- Test: `tests/test_generator.py`

A **chunk** is a vertical slice the height of one screen (`INTERNAL_HEIGHT = 540` px) that contains some platforms and zero or more hazard spawn requests. The generator MUST guarantee a *reachable* path: each platform's horizontal distance to the next platform above is ≤ 70% of max horizontal jump distance.

`MAX_HORIZONTAL_JUMP_DISTANCE` is computed analytically from physics constants and added as a derived constant in this task.

- [ ] **Step 1: Add derived jump-distance constant to `settings.py`**

Append to `settings.py`:
```python
# --- Derived: maximum horizontal distance covered during one full jump ---
# Using vy0 = JUMP_VELOCITY, gravity = GRAVITY, vx = MOVE_SPEED:
#   apex time t1 = vy0 / GRAVITY
#   total airtime ~ 2 * t1 (lands back at start altitude). For an UPWARD jump
#   that lands on a higher platform, distance is shorter; this is the airborne max.
# We pick airtime conservatively (full apex-to-floor trip) for design budget.
MAX_HORIZONTAL_JUMP_DISTANCE = MOVE_SPEED * (2 * JUMP_VELOCITY / GRAVITY)
HORIZONTAL_REACH_BUDGET = 0.70 * MAX_HORIZONTAL_JUMP_DISTANCE
```

- [ ] **Step 2: Write failing tests**

`tests/test_generator.py`:
```python
import random

import settings
from world.difficulty import difficulty_for_altitude
from world.generator import Chunk, generate_chunk


def test_chunk_is_one_screen_tall() -> None:
    chunk = generate_chunk(y_start=0, difficulty=difficulty_for_altitude(0), rng=random.Random(1))
    assert chunk.y_start == 0
    assert chunk.y_end == settings.INTERNAL_HEIGHT


def test_chunk_has_correct_number_of_platforms() -> None:
    diff = difficulty_for_altitude(0)
    chunk = generate_chunk(y_start=0, difficulty=diff, rng=random.Random(1))
    assert len(chunk.platforms) == diff.platforms_per_chunk


def test_chunk_platforms_are_within_chunk_bounds() -> None:
    chunk = generate_chunk(y_start=540, difficulty=difficulty_for_altitude(50), rng=random.Random(2))
    for plat in chunk.platforms:
        assert 540 <= plat.y < 1080
        assert 0 <= plat.x
        assert plat.x + plat.w <= settings.INTERNAL_WIDTH


def test_chunk_platforms_are_reachable_from_one_below() -> None:
    chunk = generate_chunk(y_start=0, difficulty=difficulty_for_altitude(0), rng=random.Random(3))
    sorted_plats = sorted(chunk.platforms, key=lambda p: p.y)
    for lower, upper in zip(sorted_plats, sorted_plats[1:]):
        # Closest horizontal distance between lower's edge and upper's edge
        dx = max(0.0, max(lower.x - (upper.x + upper.w), upper.x - (lower.x + lower.w)))
        assert dx <= settings.HORIZONTAL_REACH_BUDGET, (
            f"Platforms unreachable: lower y={lower.y} upper y={upper.y} dx={dx}"
        )


def test_chunk_generation_is_deterministic_with_same_seed() -> None:
    diff = difficulty_for_altitude(100)
    a = generate_chunk(y_start=0, difficulty=diff, rng=random.Random(42))
    b = generate_chunk(y_start=0, difficulty=diff, rng=random.Random(42))
    assert [(p.x, p.y) for p in a.platforms] == [(p.x, p.y) for p in b.platforms]


def test_chunk_can_emit_hazard_request_when_density_positive() -> None:
    diff = difficulty_for_altitude(500)  # high density
    rng = random.Random(7)
    seen_hazard = False
    for _ in range(20):
        chunk = generate_chunk(y_start=0, difficulty=diff, rng=rng)
        if chunk.hazard_requests:
            seen_hazard = True
            kind, y = chunk.hazard_requests[0]
            assert kind in diff.hazard_pool
            assert 0 <= y < settings.INTERNAL_HEIGHT
            break
    assert seen_hazard
```

- [ ] **Step 3: Run tests to confirm failure**

```bash
pytest tests/test_generator.py -v
```

- [ ] **Step 4: Implement `world/generator.py`**

```python
"""Procedural chunk generation for the cat tower."""
from __future__ import annotations

import random
from dataclasses import dataclass, field

import settings
from entities.platforms import StandardPlatform
from world.difficulty import DifficultyParams


@dataclass
class Chunk:
    y_start: int
    y_end: int
    platforms: list[StandardPlatform] = field(default_factory=list)
    hazard_requests: list[tuple[str, float]] = field(default_factory=list)  # (kind, world_y)


def generate_chunk(*, y_start: int, difficulty: DifficultyParams, rng: random.Random) -> Chunk:
    """Generate one chunk above y_start. Guarantees reachable platforms."""
    y_end = y_start + settings.INTERNAL_HEIGHT
    chunk = Chunk(y_start=y_start, y_end=y_end)

    n = max(2, difficulty.platforms_per_chunk)
    # Distribute Y positions evenly within the chunk (with jitter)
    band_h = settings.INTERNAL_HEIGHT / n
    plat_w = 60
    last_x: float | None = None

    for i in range(n):
        # Y inside the chunk
        y_local = i * band_h + rng.uniform(0.2 * band_h, 0.8 * band_h)
        y = y_start + y_local

        # X chosen with reachability constraint relative to last_x
        if last_x is None:
            x = rng.uniform(0, settings.INTERNAL_WIDTH - plat_w)
        else:
            min_x = max(0.0, last_x - settings.HORIZONTAL_REACH_BUDGET)
            max_x = min(settings.INTERNAL_WIDTH - plat_w, last_x + settings.HORIZONTAL_REACH_BUDGET)
            if max_x < min_x:  # safety net
                min_x, max_x = 0.0, float(settings.INTERNAL_WIDTH - plat_w)
            x = rng.uniform(min_x, max_x)

        chunk.platforms.append(StandardPlatform(x=x, y=y, w=plat_w, h=8.0))
        last_x = x

    # Hazard rolling
    if difficulty.hazard_pool and rng.random() < difficulty.hazard_density:
        kind = rng.choice(difficulty.hazard_pool)
        y = rng.uniform(y_start + 50, y_end - 50)
        chunk.hazard_requests.append((kind, y))

    return chunk
```

- [ ] **Step 5: Run tests to confirm pass**

```bash
pytest tests/test_generator.py -v
```

- [ ] **Step 6: Commit**

```bash
git add settings.py world/generator.py tests/test_generator.py
git commit -m "feat(world): seeded chunk generator with reachability invariant"
```

---

## Task 11: Chunk lifecycle in game scene

**Files:**
- Modify: `scenes/game.py`

Replace the hardcoded platforms with a chunk pipeline: keep a sliding window of chunks, spawn the next one when the player crosses the midpoint of the current top chunk, despawn chunks fully below the camera.

- [ ] **Step 1: Wire chunks into `GameScene`**

Replace the `__init__` and `update` of `scenes/game.py`:

```python
import random

import settings
from engine.camera import Camera
from engine.input import InputState
from entities.platforms import StandardPlatform, resolve_landings
from entities.player import Player
from world.difficulty import difficulty_for_altitude
from world.generator import Chunk, generate_chunk

import pygame


class GameScene:
    def __init__(self, *, seed: int | None = None) -> None:
        self.rng = random.Random(seed)

        self.player = Player(
            start_x=settings.INTERNAL_WIDTH / 2 - settings.PLAYER_WIDTH / 2,
            start_y=20.0,
        )
        self.player.grounded = True
        self.camera = Camera(
            screen_height=settings.INTERNAL_HEIGHT,
            player_offset_from_top=settings.PLAYER_SCREEN_OFFSET_FROM_TOP,
        )
        self.dead = False

        # Ground chunk: a single full-width platform at y=0, and a generated one above.
        ground = StandardPlatform(x=0.0, y=0.0, w=settings.INTERNAL_WIDTH, h=20.0)
        self.chunks: list[Chunk] = [
            Chunk(y_start=0, y_end=settings.INTERNAL_HEIGHT, platforms=[ground]),
        ]
        self._spawn_next_chunk()

        self.input = InputState()
        self._internal = pygame.Surface((settings.INTERNAL_WIDTH, settings.INTERNAL_HEIGHT))

    def _spawn_next_chunk(self) -> None:
        top = self.chunks[-1]
        diff = difficulty_for_altitude(top.y_end // settings.PIXELS_PER_METER)
        new_chunk = generate_chunk(y_start=top.y_end, difficulty=diff, rng=self.rng)
        self.chunks.append(new_chunk)

    def begin_frame(self) -> None:
        self.input.begin_frame()

    def handle_event(self, event: pygame.event.Event) -> None:
        self.input.handle_event(event)

    def update(self, dt: float) -> None:
        self.player.set_input(
            left_held=self.input.is_held(settings.KEY_LEFT),
            right_held=self.input.is_held(settings.KEY_RIGHT),
            jump_pressed=self.input.was_pressed(settings.KEY_JUMP),
            jump_held=self.input.is_held(settings.KEY_JUMP),
        )
        prev_bottom = self.player.y
        self.player.grounded = False
        self.player.update(dt)

        all_plats: list = []
        for ch in self.chunks:
            all_plats.extend(ch.platforms)
        resolve_landings(self.player, all_plats, prev_bottom_y=prev_bottom)
        for plat in all_plats:
            plat.update(dt)

        self.camera.follow(self.player.y)

        # Spawn-ahead: if player is past midpoint of current top chunk, spawn next
        top = self.chunks[-1]
        midpoint = (top.y_start + top.y_end) / 2
        if self.player.y > midpoint:
            self._spawn_next_chunk()

        # Despawn-behind: drop chunks fully below the screen
        self.chunks = [
            ch for ch in self.chunks if not self.camera.is_below_screen(ch.y_end)
        ]

        # Death by fall
        if self.camera.is_below_screen(self.player.y + settings.PLAYER_HEIGHT):
            self.dead = True

    def draw(self, window: pygame.Surface) -> None:
        self._internal.fill(settings.COLOR_GAME_BG)
        for ch in self.chunks:
            for plat in ch.platforms:
                plat.draw(self._internal, self.camera)
        screen_y = self.camera.world_to_screen_y(self.player.y + settings.PLAYER_HEIGHT)
        pygame.draw.rect(
            self._internal,
            settings.COLOR_PLAYER,
            (int(self.player.x), int(screen_y), settings.PLAYER_WIDTH, settings.PLAYER_HEIGHT),
        )
        scaled = pygame.transform.scale(self._internal, (settings.GAME_AREA_WIDTH, settings.GAME_AREA_HEIGHT))
        window.blit(scaled, (settings.GAME_AREA_X, settings.GAME_AREA_Y))
```

- [ ] **Step 2: Manual smoke test**

```bash
python main.py
```
Expected: Endless platforms appear above as the player climbs; older platforms below the screen disappear; can climb without ever running out of platforms.

- [ ] **Step 3: Commit**

```bash
git add scenes/game.py
git commit -m "feat(game): endless chunk pipeline with spawn-ahead and despawn-behind"
```

---

## Task 12: Variant platforms (Hammock, Rope, Swinging, Disappearing, Sticky)

**Files:**
- Modify: `entities/platforms.py`
- Modify: `world/generator.py`

Each variant follows the same `update / draw / on_landed / rect / top` interface as `StandardPlatform` and is selected by the generator according to `risky_platform_ratio` and altitude gates.

Altitude gates (m): Hammock 0, Rope 50, Swinging 100, Disappearing 200, Sticky 300.

- [ ] **Step 1: Add variant classes to `entities/platforms.py`**

Append to `entities/platforms.py`:

```python
class HammockPlatform(StandardPlatform):
    """Stable, slight visual sway (purely cosmetic for now)."""

    def draw(self, surface: pygame.Surface, camera) -> None:  # noqa: ANN001
        screen_y_top = camera.world_to_screen_y(self.top)
        # Two-tone pixel: a curve impression
        pygame.draw.rect(surface, (210, 180, 150), (int(self.x), int(screen_y_top), int(self.w), int(self.h)))
        pygame.draw.line(surface, (140, 100, 70),
                         (int(self.x), int(screen_y_top + self.h - 1)),
                         (int(self.x + self.w), int(screen_y_top + self.h - 1)), 1)


class RopePlatform(StandardPlatform):
    """Narrow platform: precise jumps required."""

    def __init__(self, x: float, y: float) -> None:
        super().__init__(x=x, y=y, w=24.0, h=4.0)

    def draw(self, surface: pygame.Surface, camera) -> None:  # noqa: ANN001
        screen_y_top = camera.world_to_screen_y(self.top)
        pygame.draw.rect(surface, (200, 200, 100), (int(self.x), int(screen_y_top), int(self.w), int(self.h)))


class SwingingPlatform(StandardPlatform):
    """Drifts left-right with sinusoidal motion."""

    def __init__(self, x: float, y: float, w: float = 60.0, h: float = 8.0,
                 amplitude: float = 50.0, period: float = 3.0) -> None:
        super().__init__(x=x, y=y, w=w, h=h)
        self._x_center = x
        self._t = 0.0
        self._amp = amplitude
        self._period = period

    def update(self, dt: float) -> None:
        import math
        self._t += dt
        phase = (self._t / self._period) * 2 * math.pi
        self.x = self._x_center + math.sin(phase) * self._amp
        # Clamp inside the playfield
        self.x = max(0.0, min(settings.INTERNAL_WIDTH - self.w, self.x))

    def draw(self, surface: pygame.Surface, camera) -> None:  # noqa: ANN001
        screen_y_top = camera.world_to_screen_y(self.top)
        pygame.draw.rect(surface, (160, 200, 220), (int(self.x), int(screen_y_top), int(self.w), int(self.h)))


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
        flicker = (self._timer is not None and self._timer < 0.5)
        color = (200, 200, 200) if not flicker else (200, 100, 100)
        pygame.draw.rect(surface, color, (int(self.x), int(screen_y_top), int(self.w), int(self.h)))


class StickyTapePlatform(StandardPlatform):
    """Cannot jump from here; sets player vy to a small negative on land."""

    def on_landed(self, player) -> None:  # noqa: ANN001
        # Forbid jumping for as long as touching this platform: zero coyote, drain buffer.
        player._coyote_timer = 0.0
        player._jump_pressed_buffer = 0.0
        player.vy = -10.0  # nudge down so they slip off

    def draw(self, surface: pygame.Surface, camera) -> None:  # noqa: ANN001
        screen_y_top = camera.world_to_screen_y(self.top)
        pygame.draw.rect(surface, (220, 180, 60), (int(self.x), int(screen_y_top), int(self.w), int(self.h)))
```

Also update `resolve_landings` to skip platforms with `gone=True`. Replace the loop guard:
```python
        if getattr(plat, "gone", False):
            continue
```
inside the existing `for plat in platforms:` loop, before the AABB check.

- [ ] **Step 2: Update generator to pick variants**

Modify `world/generator.py`:

```python
from entities.platforms import (
    StandardPlatform, HammockPlatform, RopePlatform, SwingingPlatform,
    DisappearingPlatform, StickyTapePlatform,
)


def _pick_platform_class(altitude_m: int, rng: random.Random):
    candidates = [(StandardPlatform, 0), (HammockPlatform, 0)]
    if altitude_m >= 50:
        candidates.append((RopePlatform, 50))
    if altitude_m >= 100:
        candidates.append((SwingingPlatform, 100))
    if altitude_m >= 200:
        candidates.append((DisappearingPlatform, 200))
    if altitude_m >= 300:
        candidates.append((StickyTapePlatform, 300))
    return rng.choice(candidates)[0]
```

Then replace the platform construction inside `generate_chunk` so risky variants are sometimes chosen:

```python
    altitude_m = y_start // settings.PIXELS_PER_METER
    risky_count = round(n * difficulty.risky_platform_ratio)
    risky_indices = set(rng.sample(range(n), risky_count)) if risky_count else set()

    for i in range(n):
        y_local = i * band_h + rng.uniform(0.2 * band_h, 0.8 * band_h)
        y = y_start + y_local

        if last_x is None:
            x = rng.uniform(0, settings.INTERNAL_WIDTH - plat_w)
        else:
            min_x = max(0.0, last_x - settings.HORIZONTAL_REACH_BUDGET)
            max_x = min(settings.INTERNAL_WIDTH - plat_w, last_x + settings.HORIZONTAL_REACH_BUDGET)
            if max_x < min_x:
                min_x, max_x = 0.0, float(settings.INTERNAL_WIDTH - plat_w)
            x = rng.uniform(min_x, max_x)

        cls = _pick_platform_class(altitude_m, rng) if i in risky_indices else StandardPlatform
        if cls is RopePlatform:
            plat = RopePlatform(x=x, y=y)
        else:
            plat = cls(x=x, y=y, w=plat_w, h=8.0)
        chunk.platforms.append(plat)
        last_x = x
```

(Be sure the existing reachability test still passes — RopePlatform's narrower `w` still fits the budget.)

- [ ] **Step 3: Re-run tests**

```bash
pytest tests/ -v
```
Expected: all green. Manually test by climbing past 100m, 200m, 300m.

- [ ] **Step 4: Commit**

```bash
git add entities/platforms.py world/generator.py
git commit -m "feat(platforms): hammock, rope, swinging, disappearing, sticky variants"
```

---

## Task 13: Hazard base + Lives + I-frames + first hazard (yarn ball)

**Files:**
- Create: `entities/hazards.py`
- Modify: `entities/player.py`
- Modify: `scenes/game.py`

Hazards share a tiny interface: `update(dt, world)`, `draw(surface, camera)`, `rect`, `kind` (string), `dead` (bool, true when fully off-screen below or finished). The scene owns a `hazards` list and hands them to a unified collision step.

- [ ] **Step 1: Add `take_hit` to player**

Append to `entities/player.py`:

```python
    def take_hit(self) -> None:
        if self.iframe_timer > 0 or self.invincible_timer > 0:
            return
        self.lives -= 1
        self.iframe_timer = settings.IFRAME_DURATION

    @property
    def is_alive(self) -> bool:
        return self.lives >= 0
```

- [ ] **Step 2: Create `entities/hazards.py` with base + yarn**

```python
"""Hazards that try to ruin Dongle's day."""
from __future__ import annotations

import pygame

import settings
from engine.physics import Rect, aabb_overlap, apply_gravity


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
        pygame.draw.rect(surface, settings.COLOR_HAZARD, (int(self.x), int(screen_y), int(self.w), int(self.h)))


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


def make_hazard(kind: str, x: float, y: float) -> Hazard:
    if kind == "yarn":
        return YarnBall(x=x, y=y)
    raise ValueError(f"Unknown hazard kind: {kind}")  # later tasks register more
```

- [ ] **Step 3: Wire hazards into `GameScene`**

Modify `scenes/game.py`:

In `__init__` add:
```python
        self.hazards: list = []
        self._processed_hazard_keys: set[int] = set()
```

In `update`, after spawning chunks, pull hazard requests from any chunk we haven't processed yet:

```python
        for ch in self.chunks:
            key = id(ch)
            if key in self._processed_hazard_keys:
                continue
            for kind, world_y in ch.hazard_requests:
                from entities.hazards import make_hazard
                x = self.rng.uniform(0, settings.INTERNAL_WIDTH - 14)
                self.hazards.append(make_hazard(kind, x=x, y=world_y))
            self._processed_hazard_keys.add(key)

        for h in self.hazards:
            h.update(dt, self.camera)
        # Cull
        self.hazards = [h for h in self.hazards if not h.dead]

        # Hazard collision against player
        from engine.physics import aabb_overlap
        for h in self.hazards:
            if aabb_overlap(self.player.rect, h.rect):
                if h.lethal:
                    self.dead = True
                else:
                    self.player.take_hit()
                    if not self.player.is_alive:
                        self.dead = True
```

In `draw`, after platforms, before player:
```python
        for h in self.hazards:
            h.draw(self._internal, self.camera)
```

- [ ] **Step 4: Manual smoke test**

```bash
python main.py
```
Expected: Yarn balls (pink circles) occasionally fall from above past 0m. Touching one decrements lives and grants 1.5s i-frames. With START_LIVES=1, a single hit kills.

- [ ] **Step 5: Commit**

```bash
git add entities/player.py entities/hazards.py scenes/game.py
git commit -m "feat(hazards): base class + yarn ball + lives/i-frame system"
```

---

## Task 14: Mouse hazard (50m+)

**Files:**
- Modify: `entities/hazards.py`

The mouse runs left-right along a fixed altitude band. It bounces off the play area edges.

- [ ] **Step 1: Add `Mouse` class**

Append to `entities/hazards.py`:

```python
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
        pygame.draw.ellipse(surface, (140, 130, 120),
                            (int(self.x), int(screen_y), int(self.w), int(self.h)))
```

Update `make_hazard`:
```python
    if kind == "mouse":
        return Mouse(x=x, y=y)
```

- [ ] **Step 2: Manual smoke test**

Climb past 50m. Expect grey ellipse mice running side-to-side and damaging on contact.

- [ ] **Step 3: Commit**

```bash
git add entities/hazards.py
git commit -m "feat(hazards): mouse runs and bounces at 50m+"
```

---

## Task 15: Crow hazard (150m+)

**Files:**
- Modify: `entities/hazards.py`

The crow oscillates vertically while drifting horizontally — sinusoidal flight.

- [ ] **Step 1: Add `Crow` class**

```python
import math


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
        pygame.draw.polygon(surface, (40, 40, 40), [
            (int(self.x + self.w / 2), int(screen_y)),
            (int(self.x), int(screen_y + self.h)),
            (int(self.x + self.w), int(screen_y + self.h)),
        ])
```

Register in `make_hazard`:
```python
    if kind == "crow":
        return Crow(x=x, y=y)
```

- [ ] **Step 2: Manual smoke test** (climb past 150m)

- [ ] **Step 3: Commit**

```bash
git add entities/hazards.py
git commit -m "feat(hazards): sinusoidal crow at 150m+"
```

---

## Task 16: Dog (300m+) and Spray bottle (300m+)

**Files:**
- Modify: `entities/hazards.py`

The Dog sits on top of a generated platform-like area and barks (no movement, area damage). The Spray fires a horizontal water arc that sweeps once across the play area.

- [ ] **Step 1: Add `Dog` and `SprayWater` classes**

```python
class Dog(Hazard):
    """Stationary; large damage rectangle that the player should jump over."""
    kind = "dog"

    def __init__(self, x: float, y: float) -> None:
        super().__init__(x=x, y=y, w=44, h=24)

    def draw(self, surface: pygame.Surface, camera) -> None:  # noqa: ANN001
        screen_y = camera.world_to_screen_y(self.y + self.h)
        pygame.draw.rect(surface, (180, 140, 70), (int(self.x), int(screen_y), int(self.w), int(self.h)))
        pygame.draw.circle(surface, (60, 30, 10),
                           (int(self.x + self.w - 6), int(screen_y + 6)), 4)


class SprayWater(Hazard):
    """Single horizontal sweep across the play area at constant vy=0, vx fast."""
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
        pygame.draw.rect(surface, (100, 180, 230), (int(self.x), int(screen_y), int(self.w), int(self.h)))
```

Register in `make_hazard`:
```python
    if kind == "dog":
        return Dog(x=x, y=y)
    if kind == "spray":
        return SprayWater(x=x, y=y)
```

- [ ] **Step 2: Manual smoke test** (climb past 300m)

- [ ] **Step 3: Commit**

```bash
git add entities/hazards.py
git commit -m "feat(hazards): stationary dog and sweeping spray at 300m+"
```

---

## Task 17: Vacuum hazard (500m+) — permanent rising chase

**Files:**
- Modify: `entities/hazards.py`
- Modify: `scenes/game.py`

The vacuum is special: only ONE exists per game, and once spawned it rises at a constant world_y velocity from the camera bottom. It is `lethal = True`.

- [ ] **Step 1: Add `Vacuum` class**

```python
class Vacuum(Hazard):
    """Rises at constant speed from the bottom of the camera. Lethal on touch."""
    kind = "vacuum"

    SPEED = 60.0  # px/s upward (worldY-positive)

    def __init__(self, y: float) -> None:
        super().__init__(x=0, y=y, w=settings.INTERNAL_WIDTH, h=24)
        self.lethal = True

    def update(self, dt: float, camera) -> None:  # noqa: ANN001
        self.y += self.SPEED * dt
        # Never cull the vacuum

    def draw(self, surface: pygame.Surface, camera) -> None:  # noqa: ANN001
        screen_y = camera.world_to_screen_y(self.y + self.h)
        if 0 <= screen_y <= settings.INTERNAL_HEIGHT:
            pygame.draw.rect(surface, (60, 60, 80), (0, int(screen_y), settings.INTERNAL_WIDTH, int(self.h)))
            for i in range(0, settings.INTERNAL_WIDTH, 16):
                pygame.draw.rect(surface, (200, 200, 220), (i, int(screen_y - 4), 8, 6))
```

Note: `Vacuum.__init__` deliberately omits the `x` parameter from the standard hazard contract. Update `make_hazard`:
```python
    if kind == "vacuum":
        return Vacuum(y=y)
```

- [ ] **Step 2: Make vacuum spawn once per run, not per chunk**

In `scenes/game.py`:

Add to `__init__`:
```python
        self._vacuum_spawned: bool = False
```

In the chunk-hazard processing loop, special-case vacuum:
```python
            for kind, world_y in ch.hazard_requests:
                from entities.hazards import make_hazard
                if kind == "vacuum":
                    if self._vacuum_spawned:
                        continue
                    # Spawn from camera bottom regardless of generator's y
                    spawn_y = self.camera.y_top - settings.INTERNAL_HEIGHT
                    self.hazards.append(make_hazard("vacuum", x=0, y=spawn_y))
                    self._vacuum_spawned = True
                else:
                    x = self.rng.uniform(0, settings.INTERNAL_WIDTH - 14)
                    self.hazards.append(make_hazard(kind, x=x, y=world_y))
```

(The `x=0` in the `make_hazard("vacuum", ...)` call is ignored by `Vacuum.__init__`. Edit `make_hazard` to accept and discard:)
```python
    if kind == "vacuum":
        return Vacuum(y=y)
```
This already works — Python kwargs allow `make_hazard("vacuum", x=0, y=spawn_y)` because `make_hazard`'s signature accepts `x, y` even though `Vacuum` only uses `y`.

- [ ] **Step 3: Manual smoke test** (climb past 500m, see the vacuum rise)

- [ ] **Step 4: Commit**

```bash
git add entities/hazards.py scenes/game.py
git commit -m "feat(hazards): permanent rising vacuum at 500m+"
```

---

## Task 18: Items (Tuna, Catnip, Feather, Fish)

**Files:**
- Create: `entities/items.py`
- Modify: `world/generator.py`
- Modify: `scenes/game.py`

Items are passive: they sit at a world position until the player overlaps them. Spawn rate ~ one item per 2 chunks on average, weighted by rarity.

- [ ] **Step 1: Create `entities/items.py`**

```python
"""Pickup items."""
from __future__ import annotations

import pygame

import settings
from engine.physics import Rect, aabb_overlap


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
        pygame.draw.rect(surface, settings.COLOR_ITEM, (int(self.x), int(screen_y), self.w, self.h))


class TunaCan(Item):
    kind = "tuna"

    def apply(self, player) -> int:  # noqa: ANN001
        return 1  # tuna count++

    def draw(self, surface: pygame.Surface, camera) -> None:  # noqa: ANN001
        screen_y = camera.world_to_screen_y(self.y + self.h)
        pygame.draw.rect(surface, (210, 210, 230), (int(self.x), int(screen_y), self.w, self.h))
        pygame.draw.line(surface, (160, 160, 200),
                         (int(self.x), int(screen_y + self.h / 2)),
                         (int(self.x + self.w), int(screen_y + self.h / 2)), 1)


class Catnip(Item):
    kind = "catnip"

    def apply(self, player) -> int:  # noqa: ANN001
        player.invincible_timer = 5.0
        return 0

    def draw(self, surface: pygame.Surface, camera) -> None:  # noqa: ANN001
        screen_y = camera.world_to_screen_y(self.y + self.h)
        pygame.draw.polygon(surface, (140, 220, 140), [
            (int(self.x + self.w / 2), int(screen_y)),
            (int(self.x), int(screen_y + self.h)),
            (int(self.x + self.w), int(screen_y + self.h)),
        ])


class Feather(Item):
    kind = "feather"

    def apply(self, player) -> int:  # noqa: ANN001
        player.jump_boost_timer = 5.0
        return 0

    def draw(self, surface: pygame.Surface, camera) -> None:  # noqa: ANN001
        screen_y = camera.world_to_screen_y(self.y + self.h)
        pygame.draw.line(surface, (240, 240, 240),
                         (int(self.x + self.w / 2), int(screen_y)),
                         (int(self.x + self.w / 2), int(screen_y + self.h)), 2)


class Fish(Item):
    kind = "fish"

    def apply(self, player) -> int:  # noqa: ANN001
        if player.lives < settings.MAX_LIVES:
            player.lives += 1
        return 0

    def draw(self, surface: pygame.Surface, camera) -> None:  # noqa: ANN001
        screen_y = camera.world_to_screen_y(self.y + self.h)
        pygame.draw.ellipse(surface, (200, 180, 240),
                            (int(self.x), int(screen_y + 4), self.w, self.h - 4))


def make_item(kind: str, x: float, y: float) -> Item:
    return {"tuna": TunaCan, "catnip": Catnip, "feather": Feather, "fish": Fish}[kind](x=x, y=y)
```

- [ ] **Step 2: Add item rolling to `world/generator.py`**

Add to the `Chunk` dataclass:
```python
    item_requests: list[tuple[str, float, float]] = field(default_factory=list)  # (kind, x, y)
```

After hazard rolling in `generate_chunk`, append:
```python
    # Items: ~50% chance per chunk to drop one item
    if rng.random() < 0.5:
        kind = rng.choices(
            population=["tuna", "feather", "catnip", "fish"],
            weights=[0.6, 0.2, 0.15, 0.05],
            k=1,
        )[0]
        x = rng.uniform(0, settings.INTERNAL_WIDTH - 14)
        y = rng.uniform(y_start + 50, y_end - 50)
        chunk.item_requests.append((kind, x, y))
```

- [ ] **Step 3: Wire items into `GameScene`**

Add to `__init__`:
```python
        self.items: list = []
        self.tuna_count: int = 0
```

In the chunk-processing loop (alongside hazard processing — same `_processed_hazard_keys` flag covers both because each chunk is processed once):

```python
            for ikind, ix, iy in ch.item_requests:
                from entities.items import make_item
                self.items.append(make_item(ikind, x=ix, y=iy))
```

After the hazard collision loop, add:
```python
        for it in self.items:
            it.update(dt, self.camera)
        self.items = [it for it in self.items if not it.dead]
        for it in list(self.items):
            if aabb_overlap(self.player.rect, it.rect):
                self.tuna_count += it.apply(self.player)
                it.dead = True
        self.items = [it for it in self.items if not it.dead]
```

In `draw` (after platforms, before hazards):
```python
        for it in self.items:
            it.draw(self._internal, self.camera)
```

- [ ] **Step 4: Manual smoke test**

Pickups appear; tuna increments visibly (will be wired to HUD in Task 19), catnip grants invincibility, feather makes jumps higher, fish restores a life if below MAX_LIVES.

- [ ] **Step 5: Commit**

```bash
git add entities/items.py world/generator.py scenes/game.py
git commit -m "feat(items): tuna/catnip/feather/fish pickups with effects"
```

---

## Task 19: HUD live values (left + right) and "next hazard" computation

**Files:**
- Modify: `main.py`
- Create: `world/next_hazard.py`

The HUD needs the next-upcoming hazard label/altitude. A small helper computes it from the current altitude using the gate constants.

- [ ] **Step 1: Create `world/next_hazard.py`**

```python
"""Compute the next upcoming hazard above the current altitude."""
from __future__ import annotations

import settings

_HAZARDS = [
    (settings.HAZARD_GATE_YARN, "Yarn"),
    (settings.HAZARD_GATE_MOUSE, "Mouse"),
    (settings.HAZARD_GATE_CROW, "Crow"),
    (settings.HAZARD_GATE_DOG, "Dog"),
    (settings.HAZARD_GATE_VACUUM, "Vacuum"),
]


def next_hazard(altitude_m: int) -> tuple[str, int]:
    """Return (label, altitude_m) of the next hazard not yet unlocked.

    If all hazards are unlocked, returns ("All", -1).
    """
    for gate_m, label in _HAZARDS:
        if altitude_m < gate_m:
            return (label, gate_m)
    return ("All", -1)
```

- [ ] **Step 2: Wire HUD with live values in `main.py`**

Replace the `hud.draw(...)` call with:
```python
        from world.next_hazard import next_hazard
        nh_label, nh_m = next_hazard(scene.player.altitude_m)
        hud.draw(
            screen,
            altitude_m=scene.player.altitude_m,
            best_m=best_m,  # see Task 20
            lives=scene.player.lives,
            tuna=scene.tuna_count,
            next_hazard_label=nh_label,
            next_hazard_m=nh_m if nh_m >= 0 else 0,
        )
```

For now define `best_m = 0` near the top of `main()` (Task 20 replaces it):
```python
    best_m = 0
```

- [ ] **Step 3: Manual smoke test**

Lives change visibly when hit. Tuna count climbs. The "NEXT" HUD label switches as you cross each gate (Mouse → Crow → Dog → Vacuum → All).

- [ ] **Step 4: Commit**

```bash
git add world/next_hazard.py main.py
git commit -m "feat(hud): live altitude/lives/tuna and next-hazard preview"
```

---

## Task 20: Menu scene + High score persistence

**Files:**
- Create: `scenes/menu.py`
- Create: `data/highscore_io.py` (small JSON helper, kept out of `data/` since `data/` is for runtime files)
- Move helper to: `engine/highscore.py` (proper location)
- Modify: `main.py`

- [ ] **Step 1: Create `engine/highscore.py`**

```python
"""Read/write the high score JSON file."""
from __future__ import annotations

import json
import os

import settings


def load_high_score() -> int:
    if not os.path.exists(settings.HIGHSCORE_PATH):
        return 0
    try:
        with open(settings.HIGHSCORE_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return int(data.get("high_score_m", 0))
    except (OSError, ValueError, json.JSONDecodeError):
        return 0


def save_high_score(score_m: int) -> None:
    os.makedirs(os.path.dirname(settings.HIGHSCORE_PATH), exist_ok=True)
    with open(settings.HIGHSCORE_PATH, "w", encoding="utf-8") as f:
        json.dump({"high_score_m": int(score_m)}, f)
```

- [ ] **Step 2: Create `scenes/menu.py`**

```python
"""Title / menu scene."""
from __future__ import annotations

import pygame

import settings


class MenuScene:
    def __init__(self, *, best_m: int) -> None:
        self.best_m = best_m
        self.start_requested = False
        pygame.font.init()
        self.font_title = pygame.font.SysFont("consolas", 80, bold=True)
        self.font_med = pygame.font.SysFont("consolas", 32)

    def begin_frame(self) -> None:
        pass

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE):
            self.start_requested = True

    def update(self, dt: float) -> None:
        pass

    def draw(self, window: pygame.Surface) -> None:
        cx = settings.GAME_AREA_X + settings.GAME_AREA_WIDTH // 2
        cy = settings.GAME_AREA_Y + settings.GAME_AREA_HEIGHT // 2
        title = self.font_title.render("DONGLE'S", True, settings.COLOR_HUD_ACCENT)
        title2 = self.font_title.render("ADVENTURE", True, settings.COLOR_HUD_ACCENT)
        window.blit(title, title.get_rect(center=(cx, cy - 200)))
        window.blit(title2, title2.get_rect(center=(cx, cy - 110)))

        best = self.font_med.render(f"BEST  {self.best_m} m", True, settings.COLOR_HUD_TEXT)
        window.blit(best, best.get_rect(center=(cx, cy + 20)))

        prompt = self.font_med.render("Press SPACE / ENTER to start", True, settings.COLOR_HUD_TEXT)
        window.blit(prompt, prompt.get_rect(center=(cx, cy + 100)))
```

- [ ] **Step 3: Restructure `main.py` for full scene flow**

Replace `main()`:

```python
def main() -> int:
    pygame.init()
    pygame.font.init()
    screen = pygame.display.set_mode((settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT))
    pygame.display.set_caption("Dongle's Adventure")
    clock = pygame.time.Clock()

    from engine.highscore import load_high_score, save_high_score
    from scenes._hud import Hud
    from scenes.game import GameScene
    from scenes.gameover import GameOverScene
    from scenes.menu import MenuScene
    from world.next_hazard import next_hazard

    hud = Hud()
    best_m = load_high_score()
    state = "menu"  # menu | game | gameover
    menu = MenuScene(best_m=best_m)
    scene: GameScene | None = None
    gameover: GameOverScene | None = None

    running = True
    while running:
        if state == "game":
            scene.begin_frame()
        else:
            menu.begin_frame() if state == "menu" else gameover.begin_frame()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                continue
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
                continue
            if state == "menu":
                menu.handle_event(event)
            elif state == "game":
                scene.handle_event(event)
            else:
                gameover.handle_event(event)

        dt = clock.tick(settings.FPS) / 1000.0
        if state == "menu":
            menu.update(dt)
            if menu.start_requested:
                scene = GameScene()
                state = "game"
        elif state == "game":
            scene.update(dt)
            if scene.dead:
                final_m = scene.player.altitude_m
                new_record = final_m > best_m
                if new_record:
                    best_m = final_m
                    save_high_score(best_m)
                gameover = GameOverScene(altitude_m=final_m, best_m=best_m, new_record=new_record)
                state = "gameover"
        else:  # gameover
            gameover.update(dt)
            if gameover.restart_requested:
                scene = GameScene()
                gameover = None
                state = "game"

        screen.fill(settings.COLOR_BG)
        if state == "menu":
            # Draw an empty game area background behind the menu
            pygame.draw.rect(screen, settings.COLOR_GAME_BG,
                             (settings.GAME_AREA_X, settings.GAME_AREA_Y,
                              settings.GAME_AREA_WIDTH, settings.GAME_AREA_HEIGHT))
            menu.draw(screen)
            hud.draw(screen, altitude_m=0, best_m=best_m, lives=settings.START_LIVES,
                     tuna=0, next_hazard_label="Yarn", next_hazard_m=0)
        else:
            scene.draw(screen)
            nh_label, nh_m = next_hazard(scene.player.altitude_m)
            hud.draw(screen,
                     altitude_m=scene.player.altitude_m, best_m=best_m,
                     lives=scene.player.lives, tuna=scene.tuna_count,
                     next_hazard_label=nh_label, next_hazard_m=nh_m if nh_m >= 0 else 0)
            if state == "gameover":
                gameover.draw(screen)

        pygame.display.flip()

    pygame.quit()
    return 0
```

- [ ] **Step 4: Manual smoke test**

Menu appears first; SPACE starts. Death shows GameOver with "NEW RECORD!" only when score exceeded. Restart → Game. New `data/highscore.json` is written when a record is broken.

- [ ] **Step 5: Commit**

```bash
git add scenes/menu.py engine/highscore.py main.py
git commit -m "feat(scenes): menu + high-score persistence wired into scene flow"
```

---

## Task 21: Sound system with placeholder assets

**Files:**
- Create: `engine/audio.py`
- Create: `assets/sounds/jump.wav`, `land.wav`, `pickup.wav`, `hit.wav`, `gameover.wav` (generated tones)
- Create: `assets/music/bgm_loop.ogg` (placeholder — generated chord loop or silent)
- Modify: `entities/player.py`, `scenes/game.py`, `main.py`

The audio module exposes `play(name)` and `start_bgm()`. Asset generation uses `numpy`-free pygame sndarray: skip and just use silent files? No — better: generate small WAV files via Python's `wave` + `struct` so the engineer doesn't need an art pipeline.

- [ ] **Step 1: Create `engine/audio.py`**

```python
"""Audio playback wrapper. Lazy-loads on init."""
from __future__ import annotations

import os

import pygame


_SFX: dict[str, pygame.mixer.Sound] = {}
_BGM_PATH: str | None = None


def init() -> None:
    global _BGM_PATH
    pygame.mixer.init()
    base = "assets/sounds"
    for name in ("jump", "land", "pickup", "hit", "gameover"):
        path = os.path.join(base, f"{name}.wav")
        if os.path.exists(path):
            _SFX[name] = pygame.mixer.Sound(path)
    bgm = os.path.join("assets", "music", "bgm_loop.ogg")
    _BGM_PATH = bgm if os.path.exists(bgm) else None


def play(name: str) -> None:
    s = _SFX.get(name)
    if s is not None:
        s.set_volume(0.5)
        s.play()


def start_bgm(volume: float = 0.4) -> None:
    if _BGM_PATH is None:
        return
    pygame.mixer.music.load(_BGM_PATH)
    pygame.mixer.music.set_volume(volume)
    pygame.mixer.music.play(loops=-1)
```

- [ ] **Step 2: Create a tiny tone generator script**

Create `tools/generate_placeholder_sfx.py`:

```python
"""Generate placeholder SFX as 8-bit WAV files."""
from __future__ import annotations

import math
import os
import struct
import wave


def write_tone(path: str, freq: float, duration: float, volume: float = 0.6, sample_rate: int = 22050) -> None:
    n_frames = int(sample_rate * duration)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(1)  # 8-bit
        w.setframerate(sample_rate)
        for i in range(n_frames):
            # Simple decay envelope
            env = max(0.0, 1.0 - i / n_frames)
            v = math.sin(2 * math.pi * freq * i / sample_rate) * env * volume
            byte = int((v + 1.0) * 127.5)
            w.writeframes(struct.pack("B", byte))


def main() -> None:
    out = "assets/sounds"
    os.makedirs(out, exist_ok=True)
    write_tone(f"{out}/jump.wav", 660, 0.10)
    write_tone(f"{out}/land.wav", 220, 0.08)
    write_tone(f"{out}/pickup.wav", 880, 0.10)
    write_tone(f"{out}/hit.wav", 110, 0.20)
    write_tone(f"{out}/gameover.wav", 80, 0.50)
    print("Wrote placeholder SFX to", out)


if __name__ == "__main__":
    main()
```

Run it:
```bash
python tools/generate_placeholder_sfx.py
```

- [ ] **Step 3: Provide a placeholder BGM (silent file)**

```bash
python -c "import wave, struct; w=wave.open('assets/music/bgm_loop.ogg','wb')" 2>/dev/null || true
```
Actually `wave` cannot write OGG. Simplest: leave `assets/music/bgm_loop.ogg` absent so `audio.start_bgm` becomes a no-op until a real BGM file is dropped in. Document this in `assets/music/README.md`:

```markdown
# BGM placeholder

Drop a 16-bit chiptune-style OGG file here named `bgm_loop.ogg`. Until then BGM is silent.
```

- [ ] **Step 4: Wire SFX hooks**

In `scenes/game.py`, near the top:
```python
from engine import audio
```

After a successful jump (you can detect this by comparing player vy before/after), simpler: just call after `player.update`:
```python
        if self.player.grounded is False and prev_bottom == self.player.y - 0:
            pass
```
Cleaner approach — give the player a flag:

In `entities/player.py`, in the jump-trigger branch:
```python
            self.just_jumped = True
```
Add `self.just_jumped: bool = False` in `__init__` and reset at the top of `update`:
```python
        self.just_jumped = False
```
Also expose a landing flag — set `just_landed=True` in `resolve_landings` (in `entities/platforms.py`) right before `break`:
```python
        player.just_landed = True
```
Add `self.just_landed: bool = False` in player `__init__`, reset at top of `update`.

Then in `scenes/game.py` `update`, after `resolve_landings`:
```python
        if self.player.just_jumped:
            audio.play("jump")
        if self.player.just_landed:
            audio.play("land")
```
After hazard hit (in the hazard collision loop), call `audio.play("hit")` (or `"gameover"` if `not self.player.is_alive`).

After item apply:
```python
                audio.play("pickup")
```

In `main.py`, after `pygame.init()`:
```python
    from engine import audio
    audio.init()
    audio.start_bgm()
```

- [ ] **Step 5: Manual smoke test** — sound effects play; BGM is silent until `assets/music/bgm_loop.ogg` exists.

- [ ] **Step 6: Commit**

```bash
git add engine/audio.py tools/generate_placeholder_sfx.py assets/sounds/ assets/music/README.md \
        entities/player.py entities/platforms.py scenes/game.py main.py
git commit -m "feat(audio): SFX wrapper + placeholder tones; BGM hook is no-op until file present"
```

---

## Task 22: Visual polish — sky, player animation states, i-frame blink

**Files:**
- Modify: `scenes/game.py`
- Create: `entities/player_render.py`

Two things ship in this task:
1. Sky color transitions by altitude band + starfield in space.
2. Player has visible *state* via shape/color: idle / run / jump / fall / hurt. Final pixel-art sprites remain placeholder-style (drawn primitives at the 32×32 footprint) and can be swapped later by replacing `entities/player_render.py` with a sprite-blit version.

Out of scope for this task (and the v1 plan): bespoke pixel-art sprite sheets, particle systems, screen shake.

- [ ] **Step 1: Create `entities/player_render.py`**

```python
"""Draws Dongle's body in one of five states: idle / run / jump / fall / hurt.

This file is the single seam that swaps placeholder primitives for real
sprite sheets later. All callers go through `draw_player`.
"""
from __future__ import annotations

import math

import pygame

import settings


def _state(player) -> str:  # noqa: ANN001
    if player.iframe_timer > 0:
        return "hurt"
    if not player.grounded:
        return "jump" if player.vy > 0 else "fall"
    if abs(player.vx) > 0.1:
        return "run"
    return "idle"


def draw_player(surface: pygame.Surface, player, camera) -> None:  # noqa: ANN001
    state = _state(player)

    # i-frame blink: skip drawing every other 0.1s window
    if state == "hurt":
        blink_phase = int(player.iframe_timer * 10) % 2
        if blink_phase == 0:
            return

    # Squash/stretch hint for jump/fall
    w = settings.PLAYER_WIDTH
    h = settings.PLAYER_HEIGHT
    if state == "jump":
        w = int(w * 0.85)
        h = int(h * 1.15)
    elif state == "fall":
        w = int(w * 1.10)
        h = int(h * 0.90)

    # Anchor at player.x, player.y (bottom-left); recompute screen position from new size
    screen_y_top = camera.world_to_screen_y(player.y + h)
    rect_x = int(player.x + (settings.PLAYER_WIDTH - w) / 2)

    # Body: white Persian cat (rounded body)
    body = pygame.Rect(rect_x, int(screen_y_top), w, h)
    pygame.draw.ellipse(surface, settings.COLOR_PLAYER, body)
    # Inner shadow
    pygame.draw.ellipse(surface, (210, 210, 210), body.inflate(-6, -6))

    # Two ear triangles
    ear_h = h // 4
    pygame.draw.polygon(surface, settings.COLOR_PLAYER, [
        (rect_x + 4, int(screen_y_top + 6)),
        (rect_x + 4, int(screen_y_top - ear_h + 6)),
        (rect_x + 4 + ear_h, int(screen_y_top + 6)),
    ])
    pygame.draw.polygon(surface, settings.COLOR_PLAYER, [
        (rect_x + w - 4, int(screen_y_top + 6)),
        (rect_x + w - 4, int(screen_y_top - ear_h + 6)),
        (rect_x + w - 4 - ear_h, int(screen_y_top + 6)),
    ])

    # Eyes (two dots) — facing direction reflected by horizontal velocity
    eye_offset = 4 if player.vx >= 0 else -4
    eye_y = int(screen_y_top + h // 3)
    pygame.draw.circle(surface, (40, 40, 60), (rect_x + w // 2 - 5 + eye_offset, eye_y), 2)
    pygame.draw.circle(surface, (40, 40, 60), (rect_x + w // 2 + 5 + eye_offset, eye_y), 2)

    # Run animation: tiny vertical bob using time
    if state == "run":
        bob = int(math.sin(pygame.time.get_ticks() / 80) * 1)
        # Re-blit body shifted by bob (simple visual feedback)
        pygame.draw.line(
            surface, (180, 180, 180),
            (rect_x, int(screen_y_top + h - 1 + bob)),
            (rect_x + w, int(screen_y_top + h - 1 + bob)), 1,
        )
```

- [ ] **Step 2: Replace player drawing in `scenes/game.py`**

In `GameScene.draw`, find the existing player draw lines:
```python
        screen_y = self.camera.world_to_screen_y(self.player.y + settings.PLAYER_HEIGHT)
        pygame.draw.rect(
            self._internal,
            settings.COLOR_PLAYER,
            (int(self.player.x), int(screen_y), settings.PLAYER_WIDTH, settings.PLAYER_HEIGHT),
        )
```
Replace with:
```python
        from entities.player_render import draw_player
        draw_player(self._internal, self.player, self.camera)
```

- [ ] **Step 3: Add sky color and starfield**

Add to `scenes/game.py`:

```python
def _sky_color(altitude_m: int) -> tuple[int, int, int]:
    if altitude_m < 150:
        return (60, 130, 200)    # day
    if altitude_m < 350:
        return (210, 110, 60)    # sunset
    if altitude_m < 500:
        return (50, 30, 80)      # night
    return (8, 8, 20)            # space
```

In `GameScene.draw`, replace `self._internal.fill(settings.COLOR_GAME_BG)` with:
```python
        sky = _sky_color(self.player.altitude_m)
        self._internal.fill(sky)
        if self.player.altitude_m >= 500:
            import random
            star_rng = random.Random(int(self.camera.y_top) // 50)
            for _ in range(40):
                sx = star_rng.randint(0, settings.INTERNAL_WIDTH - 1)
                sy = star_rng.randint(0, settings.INTERNAL_HEIGHT - 1)
                self._internal.set_at((sx, sy), (240, 240, 240))
```

- [ ] **Step 4: Manual smoke test**

- Player visibly squashes when rising, stretches when falling, blinks during i-frames.
- Sky transitions from day → sunset → night → space as you climb.
- Eye direction flips left/right with movement.

- [ ] **Step 5: Commit**

```bash
git add scenes/game.py entities/player_render.py
git commit -m "feat(visuals): player state animations + altitude-banded sky/stars"
```

---

## Final Verification

- [ ] **Run the full test suite**

```bash
pytest -v
```
Expected: all tests pass.

- [ ] **Manual end-to-end run**

```bash
python main.py
```
Expected:
1. Menu shows. SPACE starts a run.
2. Player jumps, lands, climbs through procedurally generated platforms.
3. At 50m mice appear; at 150m crows; at 300m dogs/spray; at 500m vacuum rises and sky goes to space.
4. Picking up tuna increments HUD; catnip flashes invincibility (no-hit window); feather increases jump height; fish restores a life.
5. Falling off the bottom or losing all lives → Game Over with reached altitude.
6. New record persists across runs (`data/highscore.json` exists).
7. Side HUDs continuously show ALTITUDE / BEST / LIVES / NEXT HAZARD / TUNA.

- [ ] **Final commit** if any final polish was added during verification.

---

## Plan complete

Save location: `docs/superpowers/plans/2026-05-03-dongles-adventure.md`
