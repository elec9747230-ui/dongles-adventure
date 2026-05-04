"""All tunable constants for Dongle's Adventure.

Values live here so gameplay tuning never requires touching logic. Constants
are grouped into sections (Display, World units, Player physics, Camera,
Difficulty, Lives, Files, Colors, Key bindings, Derived reachability budgets).
The Derived section at the bottom is *computed* from the player physics
constants above it — change the inputs and the budgets re-balance themselves.
"""
from __future__ import annotations

# ===========================================================================
# Display
# ===========================================================================
# Native window size. 1920x1080 is the design target; the game area is
# centred and flanked by two HUD panels that share the leftover horizontal
# space.
WINDOW_WIDTH = 1920    # px, full window width
WINDOW_HEIGHT = 1080   # px, full window height

# The game logic runs on a small "internal" canvas and is then upscaled.
# Working at 360x540 internally keeps physics math in tidy small numbers
# and lets us swap the upscale factor for different display targets.
INTERNAL_WIDTH = 360   # px, gameplay canvas width
INTERNAL_HEIGHT = 540  # px, gameplay canvas height (also = chunk height)
GAME_SCALE = 2         # internal -> displayed game area (yields 720x1080)

# Computed game-area rectangle inside the window.
GAME_AREA_WIDTH = INTERNAL_WIDTH * GAME_SCALE        # 720
GAME_AREA_HEIGHT = INTERNAL_HEIGHT * GAME_SCALE      # 1080
GAME_AREA_X = (WINDOW_WIDTH - GAME_AREA_WIDTH) // 2  # 600 (centred horizontally)
GAME_AREA_Y = 0

# HUD panel rectangles flank the game area left and right.
LEFT_HUD_X = 0
LEFT_HUD_WIDTH = GAME_AREA_X                         # 600
RIGHT_HUD_X = GAME_AREA_X + GAME_AREA_WIDTH          # 1320
RIGHT_HUD_WIDTH = WINDOW_WIDTH - RIGHT_HUD_X         # 600

FPS = 60  # target framerate; physics integration uses real dt so framerate drops are tolerated

# ===========================================================================
# World units
# ===========================================================================
# Altitude conversion. The HUD shows meters; collision and rendering use
# pixels. 10 px/m makes the tower feel tall without requiring giant numbers
# in the chunk generator.
PIXELS_PER_METER = 10  # 1m altitude = 10 internal px

# ===========================================================================
# Player physics
# ===========================================================================
PLAYER_WIDTH = 32   # px, AABB width  (matches sprite hitbox, not visual silhouette)
PLAYER_HEIGHT = 32  # px, AABB height
MOVE_SPEED = 180.0          # px/s horizontal walk speed (no acceleration ramp; instantaneous)
GRAVITY = 1200.0            # px/s^2 downward acceleration; tuned so a full jump feels weighty but not floaty
JUMP_VELOCITY = 520.0       # px/s initial upward velocity from a full jump
SHORT_JUMP_CUTOFF = 240.0   # px/s; on Jump release while rising, vy is clamped to this for variable-height jumps
COYOTE_TIME = 0.08          # s; jump-still-allowed window after walking off a ledge (forgiveness)
JUMP_BUFFER = 0.10          # s; jump input pre-recorded before landing so timing-tight jumps still register

# ===========================================================================
# Camera
# ===========================================================================
# Player's vertical screen position is fixed at this offset from the top of
# the internal canvas; the world scrolls underneath. 60% of the canvas height
# leaves a long sight-line above the cat for telegraphing upcoming hazards.
PLAYER_SCREEN_OFFSET_FROM_TOP = 324  # px in internal canvas (60% of 540)

# ===========================================================================
# World generation - difficulty / altitude gates
# ===========================================================================
# Each gate is the meters-altitude at which a hazard kind is unlocked into
# the spawn pool. These were lowered from earlier playtests so the player
# meets variety within the first minute of play instead of grinding low
# floors.
HAZARD_GATE_YARN = 0      # m, always available (introductory hazard)
HAZARD_GATE_MOUSE = 20    # m, first new hazard ~early floors
HAZARD_GATE_CROW = 60     # m, mid-air threat
HAZARD_GATE_DOG = 120     # m, ground-pursuit threat
HAZARD_GATE_SPRAY = 150   # m, area-denial threat
HAZARD_GATE_VACUUM = 400  # m, end-game tier (also forces hazard_density floor)

# ===========================================================================
# Lives
# ===========================================================================
START_LIVES = 1        # one-life-default keeps early runs short and snappy
MAX_LIVES = 3          # cap on lives picked up from items so hoarding can't trivialize the climb
IFRAME_DURATION = 1.5  # s of invulnerability after a non-lethal hit; long enough to escape overlapping hazards

# ===========================================================================
# Files
# ===========================================================================
HIGHSCORE_PATH = "data/highscore.json"  # persisted best altitude (meters); created on first save

# ===========================================================================
# Colors (placeholder palette)
# ===========================================================================
# Final art will replace these; current values prioritize readability over
# style. RGB tuples in 0-255.
COLOR_BG = (24, 18, 36)         # outer window background (deep purple)
COLOR_GAME_BG = (60, 80, 130)   # gameplay-area background
COLOR_HUD_BG = (16, 12, 24)     # HUD panels (darker than BG for contrast)
COLOR_HUD_TEXT = (235, 230, 215)
COLOR_HUD_ACCENT = (255, 200, 80)
COLOR_PLATFORM = (180, 130, 90)
COLOR_PLAYER = (240, 240, 240)
COLOR_HAZARD = (220, 80, 80)
COLOR_ITEM = (120, 220, 120)

# ===========================================================================
# Key bindings
# ===========================================================================
import pygame  # noqa: E402  (import here so module top stays declarative)

KEY_LEFT = pygame.K_LEFT
KEY_RIGHT = pygame.K_RIGHT
KEY_JUMP = pygame.K_SPACE
KEY_PAUSE = pygame.K_ESCAPE
KEY_RESTART = pygame.K_r

# ===========================================================================
# Derived reachability budgets
# ===========================================================================
# These are the load-bearing invariants the chunk generator relies on. They
# are computed (not hard-coded) so a change to MOVE_SPEED / JUMP_VELOCITY /
# GRAVITY automatically keeps platform spacing inside the player's actual
# capabilities.
#
# Maximum horizontal distance covered during one full jump:
#   apex time t1 = JUMP_VELOCITY / GRAVITY
#   total airtime ~= 2 * t1 (lands back at start altitude)
#   horizontal distance = MOVE_SPEED * airtime
MAX_HORIZONTAL_JUMP_DISTANCE = MOVE_SPEED * (2 * JUMP_VELOCITY / GRAVITY)
# 70% safety margin: the player needs reaction time to align mid-flight, so
# we don't let the generator place platforms at the absolute physical limit.
HORIZONTAL_REACH_BUDGET = 0.70 * MAX_HORIZONTAL_JUMP_DISTANCE

# Vertical reach: jump apex height = vy^2 / (2*g) from kinematics.
MAX_VERTICAL_JUMP = (JUMP_VELOCITY * JUMP_VELOCITY) / (2 * GRAVITY)
# 80% safety margin: keeps the next platform's top inside the *rising* arc
# so the player actually lands on it rather than grazing the apex.
VERTICAL_REACH_BUDGET = 0.80 * MAX_VERTICAL_JUMP   # ~90 px
# Minimum vertical separation between consecutive platforms so they never
# visually stack or merge their hitboxes.
MIN_VERTICAL_GAP = 36
