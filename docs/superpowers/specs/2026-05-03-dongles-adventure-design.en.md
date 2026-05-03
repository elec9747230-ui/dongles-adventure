# Dongle's Adventure — Design Document

- **Date**: 2026-05-03
- **Status**: Awaiting approval (under user review)
- **Target deliverable**: Python + Pygame desktop game

> Korean version: [2026-05-03-dongles-adventure-design.md](./2026-05-03-dongles-adventure-design.md)

## 1. Concept

**Dongle**, a white Persian cat, climbs an infinitely tall cat tower via jumping in this vertical-scrolling platformer. Combines the climb / fall-to-death mechanics of the MSX classic *Magical Tree (Konami, 1984)* with endless procedural generation.

### 1.1 One-line pitch
"Magical Tree's jump-climb + Doodle Jump's endless ascent + a white cat theme."

### 1.2 Core design values
- **Short sessions, instant restart**: 1–5 minutes per run; one key to retry.
- **Clear progression**: height = score.
- **Gradual environmental shift**: hazards, visuals, and audio all evolve with altitude.

## 2. Core gameplay

### 2.1 Goal
Climb as high as possible. Beat your **personal best altitude**.

### 2.2 Controls
- `←` `→`: Move left/right
- `Space`: Jump (tap = short jump, hold = high jump — variable jump height)
- `Esc`: Pause
- `R`: Restart (on game over)

### 2.3 Camera
Smooth vertical scrolling that keeps the player around the lower-middle (~60% from top) of the screen. The camera tracks the **maximum altitude reached** and never scrolls back down (Doodle Jump style). Once a platform exits the bottom of the screen, you cannot return to it; falling off the bottom = instant death.

### 2.4 Death conditions
- Falling off the bottom of the screen
- Colliding with a hazard while not invincible

### 2.5 Session flow
Menu → Game → Game Over (score shown) → Restart or back to Menu.

## 3. Platforms (procedurally generated)

### 3.1 Platform types
| Type | Behavior | First appearance |
|---|---|---|
| Standard cat-tower tier | Stable, baseline | 0m |
| Cloth hammock | Stable, slight sway | 0m |
| Rope | Narrow platform; precise jump required | 50m |
| Swinging platform | Drifts left/right slowly | 100m |
| Disappearing platform | Vanishes 1s after landing | 200m |
| Sticky tape | Cannot jump from it; immediate fall | 300m |

### 3.2 Generation rules
- Generated in **chunks** (one chunk = one screen height).
- The next chunk spawns when the player crosses the midpoint of the current chunk.
- Each chunk contains 4–7 platforms; horizontal spacing never exceeds 70% of max jump distance — a reachable next platform is always guaranteed.
- As altitude increases:
  - Vertical gap between platforms ↑
  - Hazardous platform ratio ↑
  - Stable platform ratio ↓

## 4. Hazards

### 4.1 Altitude introduction table
| Altitude band | Hazards added |
|---|---|
| 0–50m | (Tutorial) Falling yarn balls |
| 50–150m | + Mice (run quickly left/right) |
| 150–300m | + Crows (curved horizontal flight) |
| 300–500m | + Dog (barks on certain platforms, blocks jumping); spray bottle (horizontal water jet) |
| 500m+ | + Vacuum cleaner (rises from the bottom of the screen at constant speed; instant death on contact) |

### 4.2 Behavior rules
- All hazards are active only within ±1 chunk of the camera (performance).
- The vacuum spawns the moment the player crosses 500m and rises at constant speed regardless of player movement → permanent pressure.

## 5. Items / power-ups

| Item | Effect | Spawn rate |
|---|---|---|
| Tuna can | +50 score | Frequent |
| Catnip | 5s invincibility (pass through enemies; falling still kills) | Rare |
| Feather toy | 5s jump-power boost | Moderate |
| Fish | +1 life (cap of 3 carried) | Very rare |

The player starts with 1 life. Touching a hazard removes 1 life and grants **1.5s i-frames** (prevents chain hits); going below 0 ends the run. Falling kills regardless of remaining lives.

## 6. Resolution / screen layout / HUD

### 6.1 Resolution
- **Window size**: 1920×1080 (Full HD; both windowed and fullscreen supported)
- **Internal render resolution**: 360×540 → displayed at 720×1080 via **2x integer scaling** (keeps pixel art crisp)
- All game logic uses internal coordinates → identical behavior in any window mode

### 6.2 Screen partition
| Region | Position | Size (px) |
|---|---|---|
| Left HUD | x=0 | 600×1080 |
| Game area | x=600 | 720×1080 |
| Right HUD | x=1320 | 600×1080 |

### 6.3 Left HUD (game state)
- **ALTITUDE**: Current altitude (large, emphasized)
- **BEST**: Personal best
- **LIVES**: Fish icons, 0–3
- **POWERUPS**: Active power-ups + remaining time (e.g., "🌿 catnip 4.2s")
- **CONTROLS**: Always-on control reminder (← → move, Space jump)

### 6.4 Right HUD (progression info)
- **ALTITUDE SCALE**: Vertical lines at hazard-introduction altitudes (50m, 150m, 300m, 500m), with the current altitude marked by an arrow → previews upcoming challenges visually
- **NEXT HAZARD**: Icon + altitude of the next hazard to appear (e.g., "🐦 Crows @ 150m")
- **TUNA**: Total tuna cans collected
- **HINT**: "Esc: Pause", "R: Restart"

### 6.5 In-game overlays
- **Pause**: Translucent banner centered in the game area + "PAUSED — Press Esc to resume"
- **Game over**: Large result panel centered in the game area (altitude reached, new-record flag, "Press R to restart")

## 7. Visual style

- **16-bit pixel art** (matches the BGM tone)
- Dongle sprite: 32×32 px
- Animation states: idle, run, jump (ascending), fall (descending), hurt
- Background: cat tower interior + view through a window:
  - 0–150m: Daylight (blue sky)
  - 150–350m: Sunset (orange)
  - 350–500m: Night (deep purple)
  - 500m+: Space (black backdrop with stars)

## 8. Sound

- **BGM**: Upbeat 16-bit chiptune (placeholder track during development; the final BGM is chosen at the polish stage — option D).
- **SFX**: Jump, land, item pickup, hit, game over (placeholders are fine).
- Pygame `mixer` module; OGG preferred.

## 9. Data persistence

- Only the high score is stored locally (`data/highscore.json`).
- Format: `{"high_score_m": <int>}`
- Saved immediately on game over if a new record is set.

## 10. Technical structure

### 10.1 Stack
- Python 3.11+
- Pygame 2.5+
- Dependency management: `pyproject.toml` (mirrors sibling project `galaga-clone`).

### 10.2 Directory layout
```
dongles-adventure/
├── main.py                   # Entry point
├── pyproject.toml
├── README.md
├── settings.py               # Screen size, FPS, colors, key bindings, physics constants
├── assets/
│   ├── sprites/              # Dongle, hazards, platforms, items, backgrounds
│   ├── sounds/               # SFX
│   └── music/                # BGM (placeholder)
├── engine/
│   ├── __init__.py
│   ├── camera.py             # Vertical-scroll camera
│   ├── physics.py            # Gravity, jump, collision
│   └── input.py              # Key input handling
├── entities/
│   ├── __init__.py
│   ├── player.py             # Dongle
│   ├── platforms.py          # Platform classes by type
│   ├── hazards.py            # Hazards (yarn, mouse, crow, dog, spray, vacuum)
│   └── items.py              # Items (tuna can, catnip, feather, fish)
├── world/
│   ├── __init__.py
│   ├── generator.py          # Procedural chunk generation
│   └── difficulty.py         # Altitude → difficulty parameters
├── scenes/
│   ├── __init__.py
│   ├── menu.py
│   ├── game.py
│   └── gameover.py
├── data/
│   └── highscore.json
└── tests/
    ├── test_physics.py
    ├── test_generator.py
    └── test_difficulty.py
```

### 10.3 Module responsibilities
- **engine/physics.py**: Gravity, jump impulse, AABB collision. Mostly stateless pure functions.
- **engine/camera.py**: World ↔ screen coordinate conversion. The camera tracks only `y_top`.
- **world/generator.py**: Chunk creation / disposal. `generate_chunk(y_start, difficulty) -> Chunk`.
- **world/difficulty.py**: Maps altitude to difficulty parameters (table-driven).
- **entities/\***: Each exposes `update(dt, world)` and `draw(screen, camera)`.
- **scenes/\***: Scene-stack pattern. Each scene implements `handle_event`, `update`, `draw`.

## 11. Test strategy

- Unit tests (pytest): physics (gravity, collision), generator (chunk invariant — "a reachable platform always exists"), difficulty mapping.
- Pygame-dependent (rendering) parts are not unit-tested directly — verified via manual playtesting.
- The procedural generator is tested with fixed seeds for determinism.

## 12. Development phases (will be broken into discrete steps in the implementation plan)

1. Project scaffolding (`pyproject.toml`, directories, Pygame window)
2. Dongle + static platforms + jump + collision
3. Camera + fall death + game over + restart
4. Procedural platform generation + chunk management
5. Hazards added one type at a time (with altitude gating)
6. Items + HUD + lives system
7. Menu / high-score persistence
8. Sound / BGM wiring (placeholder)
9. Visual polish (animation, background transitions, effects)

## 13. Out of scope

- Multiplayer / networking
- Mobile builds
- Original BGM composition (placeholder only)
- Story cutscenes
- Character customization
- IAP / ads
- Cloud-based score leaderboard
