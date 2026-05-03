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

# --- Derived: maximum horizontal distance covered during one full jump ---
# Using vy0 = JUMP_VELOCITY, gravity = GRAVITY, vx = MOVE_SPEED:
#   apex time t1 = vy0 / GRAVITY
#   total airtime ~ 2 * t1 (lands back at start altitude)
MAX_HORIZONTAL_JUMP_DISTANCE = MOVE_SPEED * (2 * JUMP_VELOCITY / GRAVITY)
HORIZONTAL_REACH_BUDGET = 0.70 * MAX_HORIZONTAL_JUMP_DISTANCE
