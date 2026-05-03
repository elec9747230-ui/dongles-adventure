# 동글이의 모험 구현 계획

> **에이전틱 워커 안내:** 필수 서브 스킬: superpowers:subagent-driven-development (권장) 또는 superpowers:executing-plans 를 사용해 태스크 단위로 구현하세요. 각 단계는 체크박스(`- [ ]`) 문법으로 진행 상황을 추적합니다.

> English version: [2026-05-03-dongles-adventure.md](./2026-05-03-dongles-adventure.md)

**목표:** 흰 페르시안 고양이 동글이가 무한 캣타워를 등반하는 Pygame 기반 세로 스크롤 엔드리스 플랫포머 — MSX *요술나무* + Doodle Jump 컨셉.

**아키텍처:**
- **360×540 px** 내부 캔버스에 매 프레임 렌더링 → 2x 정수 스케일로 1920×1080 윈도우 가운데 배치된 720×1080 게임 영역에 표시. 양 옆 600 px 폭은 HUD 패널.
- 씬 스택 패턴 (Menu / Game / GameOver), 각 씬은 `handle_event(e)`, `update(dt)`, `draw(surface)` 구현.
- 월드는 **위 방향이 양의 y** 좌표계 (`world_y` 가 클수록 높은 고도). 카메라는 `screen_y = camera.y_top - world_y` 로 변환. `y_top` 은 단조 비감소.
- 월드 콘텐츠는 **청크** 단위로 생성 (1청크 = 1화면 높이 = 540 내부 px), 결정론적 시드 사용으로 테스트 가능.
- 엔티티는 `update(dt, world)` / `draw(surface, camera)` 인터페이스의 단순 Python 클래스. 물리 유틸리티는 단위 테스트 가능한 **순수 함수**.

**기술 스택:** Python 3.11+, Pygame 2.5+, pytest (개발용). 자매 프로젝트 `galaga-clone` 의 구조를 참고.

**좌표/단위 규약 (코딩 전 확정):**
- 모든 게임 로직은 360×540 내부 캔버스의 픽셀 단위.
- `world_y` = 픽셀 단위 고도 (위 = 양수). 플레이어 시작 위치 `world_y = 0`.
- 표시용 미터 단위: `meters = world_y // PIXELS_PER_METER`, `PIXELS_PER_METER = 10`. 즉 50m = 500 px, 500m = 5000 px.
- 본 계획서의 모든 위협 등장 고도는 *미터* 기준이며 `PIXELS_PER_METER` 로 변환.

---

## 파일 구조

구현 중 생성될 파일:

```
dongles-adventure/
├── main.py                       # 진입점
├── pyproject.toml
├── README.md
├── settings.py                   # 모든 튜닝 상수
├── assets/
│   ├── sprites/                  # (런타임 생성 placeholder)
│   ├── sounds/                   # placeholder SFX (생성된 톤)
│   └── music/                    # placeholder BGM
├── engine/
│   ├── __init__.py
│   ├── physics.py                # 순수 함수: 중력, AABB
│   ├── camera.py                 # 단조 y_top 카메라
│   └── input.py                  # held-key 추적 헬퍼
├── entities/
│   ├── __init__.py
│   ├── player.py                 # 동글이
│   ├── platforms.py              # 발판 클래스들
│   ├── hazards.py                # 적/유해물 클래스들
│   └── items.py                  # 아이템
├── world/
│   ├── __init__.py
│   ├── difficulty.py             # 고도 → 난이도 파라미터
│   └── generator.py              # 청크 생성
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

> **중요:** 본 한국어 버전의 단계별 코드 블록과 셸 명령은 영문 마스터([2026-05-03-dongles-adventure.md](./2026-05-03-dongles-adventure.md)) 와 100% 동일합니다. 실제 코드/명령은 영문본을 1차 소스로 사용하세요. 본 한국어본은 의도/근거/한국어 안내 + 동일한 코드를 함께 제공합니다.

---

## Task 1: 프로젝트 스캐폴딩 + 윈도우 부팅

**파일:**
- 생성: `pyproject.toml`
- 생성: `settings.py`
- 생성: `main.py`
- 생성: `engine/__init__.py`, `entities/__init__.py`, `world/__init__.py`, `scenes/__init__.py`, `tests/__init__.py`
- 생성: `assets/sprites/.gitkeep`, `assets/sounds/.gitkeep`, `assets/music/.gitkeep`, `data/.gitkeep`
- 생성: `README.md`

- [ ] **Step 1: `pyproject.toml` 생성**

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

- [ ] **Step 2: 잠긴 상수가 들어간 `settings.py` 생성**

게임 튜닝이 로직 수정 없이 가능하도록 모든 상수는 이 파일에 둡니다.

```python
"""All tunable constants for Dongle's Adventure."""
from __future__ import annotations

# --- Display ---------------------------------------------------------------
WINDOW_WIDTH = 1920
WINDOW_HEIGHT = 1080

INTERNAL_WIDTH = 360
INTERNAL_HEIGHT = 540
GAME_SCALE = 2

GAME_AREA_WIDTH = INTERNAL_WIDTH * GAME_SCALE
GAME_AREA_HEIGHT = INTERNAL_HEIGHT * GAME_SCALE
GAME_AREA_X = (WINDOW_WIDTH - GAME_AREA_WIDTH) // 2
GAME_AREA_Y = 0

LEFT_HUD_X = 0
LEFT_HUD_WIDTH = GAME_AREA_X
RIGHT_HUD_X = GAME_AREA_X + GAME_AREA_WIDTH
RIGHT_HUD_WIDTH = WINDOW_WIDTH - RIGHT_HUD_X

FPS = 60

# --- World units -----------------------------------------------------------
PIXELS_PER_METER = 10

# --- Player physics --------------------------------------------------------
PLAYER_WIDTH = 32
PLAYER_HEIGHT = 32
MOVE_SPEED = 180.0
GRAVITY = 1200.0
JUMP_VELOCITY = 520.0
SHORT_JUMP_CUTOFF = 240.0
COYOTE_TIME = 0.08
JUMP_BUFFER = 0.10

# --- Camera ----------------------------------------------------------------
PLAYER_SCREEN_OFFSET_FROM_TOP = 324

# --- Difficulty / altitude bands ------------------------------------------
HAZARD_GATE_YARN = 0
HAZARD_GATE_MOUSE = 50
HAZARD_GATE_CROW = 150
HAZARD_GATE_DOG = 300
HAZARD_GATE_SPRAY = 300
HAZARD_GATE_VACUUM = 500

# --- Lives -----------------------------------------------------------------
START_LIVES = 1
MAX_LIVES = 3
IFRAME_DURATION = 1.5

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

- [ ] **Step 3: 빈 `__init__.py` 파일 생성**

```bash
mkdir -p engine entities world scenes tests assets/sprites assets/sounds assets/music data
touch engine/__init__.py entities/__init__.py world/__init__.py scenes/__init__.py tests/__init__.py
touch assets/sprites/.gitkeep assets/sounds/.gitkeep assets/music/.gitkeep data/.gitkeep
```

- [ ] **Step 4: 윈도우만 띄우는 최소 `main.py` 생성**

영문본 Task 1 Step 4 의 코드를 그대로 사용. 1920×1080 윈도우에 좌우 HUD + 가운데 게임 영역 사각형이 보여야 함.

- [ ] **Step 5: `README.md` 생성** (영문본과 동일)

- [ ] **Step 6: 설치 + 윈도우 스모크 테스트**

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .[dev]
python main.py
```
기대 결과: 1920×1080 윈도우 오픈, 좌우 HUD 패널과 파란색 게임 영역. Esc 또는 창 닫기로 종료.

- [ ] **Step 7: 커밋**

```bash
git add .
git commit -m "feat: scaffold project and boot a 1920x1080 window with HUD frame"
```

---

## Task 2: 물리 기본 함수 (TDD)

**파일:**
- 생성: `engine/physics.py`
- 테스트: `tests/test_physics.py`

물리 모듈은 순수 함수만 노출 — 전역 상태 없음, Pygame surface 의존 없음. `world_y` 위 방향 양수 좌표계. **중력은 위 방향 양수 좌표계이므로 vy 를 시간이 지날수록 감소시킴.**

- [ ] **Step 1: 실패 테스트 작성** — 영문본 동일
- [ ] **Step 2: 테스트 실패 확인**: `pytest tests/test_physics.py -v` (ImportError 예상)
- [ ] **Step 3: `engine/physics.py` 구현** — 영문본 동일 (Rect dataclass + apply_gravity + aabb_overlap)
- [ ] **Step 4: 테스트 통과 확인**: 5개 모두 PASS
- [ ] **Step 5: 커밋**: `feat(engine): pure-function gravity and AABB overlap primitives`

---

## Task 3: 카메라 (TDD)

**파일:**
- 생성: `engine/camera.py`
- 테스트: `tests/test_camera.py`

`Camera` 는 `y_top` (스크린 y=0 에 매핑되는 월드 고도) 를 추적. 플레이어가 도달한 최대 고도를 단조 추적, 플레이어가 떨어져도 카메라는 내려가지 않음 (Doodle Jump 식).

- [ ] **Step 1-5**: 영문본 Task 3 동일. 핵심 메서드: `follow(player_world_y)`, `world_to_screen_y(world_y)`, `is_below_screen(world_y)`.
- 커밋 메시지: `feat(engine): monotonic vertical-scroll camera`

---

## Task 4: 점프 가능한 플레이어 엔티티 (TDD)

**파일:**
- 생성: `entities/player.py`
- 테스트: `tests/test_player.py`

플레이어가 보유: 월드 좌표, 속도, grounded 플래그, 목숨, i-frame 타이머. 입력 처리는 디커플링 — 씬이 매 프레임 `player.set_input(left_held, right_held, jump_pressed_this_frame, jump_held)` 호출. Pygame 의존성을 엔티티 밖으로 빼서 테스트 가능.

**구현 핵심:**
- 좌우 동시 누름 → 왼쪽 우선
- 가변 점프 높이 (Space release 시 상승 중인 vy 를 SHORT_JUMP_CUTOFF 로 클램프)
- 코요테 타임 (발판 떠난 후 0.08s 점프 가능)
- 점프 버퍼 (착지 직전 0.10s 입력 보존)

- [ ] **Step 1-5**: 영문본 Task 4 의 8개 테스트 + 구현. 모든 테스트 통과 확인 후 커밋.
- 커밋 메시지: `feat(player): horizontal control, gravity, variable jump, coyote, buffer`

---

## Task 5: 발판 + 착지 충돌 (TDD)

**파일:**
- 생성: `entities/platforms.py`
- 테스트: `tests/test_platforms.py`

이번 태스크는 **표준** 발판만. 변종 발판은 Task 12 에서 추가.

**착지 규칙 (one-way):**
- (a) 이동 후 AABB 가 겹치고
- (b) `vy <= 0` (하강 또는 정지)
- (c) **이전 프레임** 플레이어 바닥이 발판 윗면 이상이었을 것

성공 시: `player.y` 를 `platform.top` 으로 스냅, `vy=0`, `grounded=True`. **위로 점프해서 발판 통과는 가능**.

- [ ] **Step 1-5**: 영문본 Task 5 동일. `StandardPlatform` + `resolve_landings(player, platforms, prev_bottom_y)`.
- 커밋 메시지: `feat(platforms): standard platform with one-way landing`

---

## Task 6: 렌더링 파이프라인 + Game 씬

**파일:**
- 생성: `scenes/game.py`
- 생성: `engine/input.py`
- 수정: `main.py`

플레이어 + 하드코딩된 발판 몇 개를 게임 씬에 연결. 360×540 내부 surface 에 매 프레임 그린 뒤 `pygame.transform.scale` 로 720×1080 게임 영역에 blit.

- [ ] **Step 1**: `engine/input.py` — 매 프레임 입력 스냅샷 헬퍼 (영문본 동일)
- [ ] **Step 2**: `scenes/game.py` — `GameScene` 클래스 (영문본 동일)
- [ ] **Step 3**: `main.py` 갱신해서 씬 호스팅
- [ ] **Step 4**: 수동 스모크 테스트 — 흰색 사각형(플레이어)가 바닥에 서있고, ←/→ 이동, Space 점프, 상위 발판 착지, 카메라가 따라옴.
- [ ] **Step 5**: 커밋: `feat(game): wire player+platforms into a scaled-render game scene`

---

## Task 7: HUD 레이아웃 placeholder

**파일:**
- 생성: `scenes/_hud.py`
- 수정: `main.py`

패널 프레임 + 라벨만 렌더링. 라이브 값은 Task 19에서 연결.

- [ ] **Step 1-4**: 영문본 동일. 좌측: ALTITUDE / BEST / LIVES / CONTROLS. 우측: ALTITUDE SCALE (50/150/300/500m 마크 + YOU 화살표) / NEXT HAZARD / TUNA / HINT.
- 커밋 메시지: `feat(hud): side panels with altitude, lives, and altitude scale`

---

## Task 8: 추락사 + Game Over 씬 + 재시작

**파일:**
- 생성: `scenes/gameover.py`
- 수정: `scenes/game.py`, `main.py`

게임 오버 플로우는 작은 씬 스택. 메인 루프가 `current_scene` 보유, `update` 가 반환하는 콜백으로 전환.

- [ ] **Step 1-5**: 영문본 동일. `GameScene.dead` 플래그, 카메라 하단 추락 검출, GameOver 오버레이, R 키 재시작.
- 커밋 메시지: `feat(scenes): fall death and Game Over with R-to-restart`

---

## Task 9: 난이도 곡선 (TDD)

**파일:**
- 생성: `world/difficulty.py`
- 테스트: `tests/test_difficulty.py`

`difficulty_for_altitude(altitude_m: int) -> DifficultyParams` — 청크 생성기와 위협 스케줄러가 사용할 파라미터를 매핑.

**파라미터 곡선:**
- `platforms_per_chunk`: 7 → 5 (고도가 오르면 발판 수 감소)
- `risky_platform_ratio`: 0.0 → 0.6
- `hazard_density`: 0.0 → 0.6 (500m+ 는 0.5 floor)
- `hazard_pool`: 고도 게이트에 따라 ["yarn"], ["yarn", "mouse"], ... 누적

- [ ] **Step 1-5**: 영문본 동일. 7개 테스트 (게이트별 1개 + 단조성 2개).
- 커밋 메시지: `feat(world): altitude->difficulty params with hazard gates`

---

## Task 10: 절차적 청크 생성기 (TDD)

**파일:**
- 생성: `world/generator.py`
- 테스트: `tests/test_generator.py`

**청크** = 한 화면 높이(540 px) 슬라이스, 발판 + 위협 스폰 요청 포함. 생성기는 **도달 가능성**을 보장: 인접한 발판 사이 수평 거리가 최대 점프 거리의 70% 이하.

`MAX_HORIZONTAL_JUMP_DISTANCE` 는 물리 상수에서 해석적으로 계산해 settings 파생 상수로 추가.

- [ ] **Step 1**: settings.py 에 파생 상수 추가
- [ ] **Step 2-5**: 영문본 동일. 6개 테스트 (높이 / 발판 수 / 경계 / 도달 가능성 / 결정론 / 위협 스폰).
- [ ] **Step 6**: 커밋: `feat(world): seeded chunk generator with reachability invariant`

---

## Task 11: Game 씬에 청크 라이프사이클 통합

**파일:**
- 수정: `scenes/game.py`

하드코딩 발판을 청크 파이프라인으로 교체:
- 슬라이딩 윈도우로 청크 보유
- 플레이어가 최상위 청크 중간점 통과 시 다음 청크 스폰
- 화면 아래로 완전히 빠진 청크 제거

- [ ] **Step 1**: `GameScene.__init__` + `update` 재작성, `_spawn_next_chunk` 헬퍼 추가
- [ ] **Step 2**: 수동 스모크 테스트 — 무한 발판 등장
- [ ] **Step 3**: 커밋: `feat(game): endless chunk pipeline with spawn-ahead and despawn-behind`

---

## Task 12: 변종 발판 (해먹/로프/흔들리는/사라지는/끈끈이)

**파일:**
- 수정: `entities/platforms.py`, `world/generator.py`

각 변종은 `StandardPlatform` 과 동일 인터페이스 (`update`/`draw`/`on_landed`/`rect`/`top`). 생성기가 `risky_platform_ratio` + 고도 게이트로 선택.

**고도 게이트 (m):** Hammock 0, Rope 50, Swinging 100, Disappearing 200, Sticky 300.

**Sticky 동작:** 착지 시 player 의 coyote/jump_buffer 를 0 으로, vy 를 작은 음수로 → 곧장 미끄러져 떨어짐.

**Disappearing 동작:** 첫 착지 후 1.0s 뒤 사라짐 (gone=True). `resolve_landings` 가 gone 발판 스킵.

- [ ] **Step 1-4**: 영문본 동일.
- 커밋 메시지: `feat(platforms): hammock, rope, swinging, disappearing, sticky variants`

---

## Task 13: 적 베이스 + 목숨/i-frame + 첫 적 (털실 뭉치)

**파일:**
- 생성: `entities/hazards.py`
- 수정: `entities/player.py`, `scenes/game.py`

적은 작은 인터페이스 공유: `update(dt, world)`, `draw(surface, camera)`, `rect`, `kind`(string), `dead`(bool), `lethal`(bool).

**플레이어 추가:** `take_hit()` (i-frame 또는 무적 중이면 무시), `is_alive` 프로퍼티.

**털실 뭉치 (yarn):** 중력의 60%로 자유낙하하는 분홍색 원.

- [ ] **Step 1-5**: 영문본 동일.
- 커밋 메시지: `feat(hazards): base class + yarn ball + lives/i-frame system`

---

## Task 14: 쥐 (50m+)

**파일:** 수정 `entities/hazards.py`

좌우로 달리며 가장자리에서 튕김. `Mouse(Hazard)` 클래스.

- [ ] **Step 1-3**: 영문본 동일.
- 커밋 메시지: `feat(hazards): mouse runs and bounces at 50m+`

---

## Task 15: 까마귀 (150m+)

**파일:** 수정 `entities/hazards.py`

수평 이동 + 사인파 수직 진동 (곡선 비행). `Crow(Hazard)` 클래스.

- [ ] **Step 1-3**: 영문본 동일.
- 커밋 메시지: `feat(hazards): sinusoidal crow at 150m+`

---

## Task 16: 강아지 + 분무기 (300m+)

**파일:** 수정 `entities/hazards.py`

- **Dog**: 정지형 큰 박스 (점프로 넘어야 함)
- **SprayWater**: 한 번 가로지르는 물줄기

- [ ] **Step 1-3**: 영문본 동일.
- 커밋 메시지: `feat(hazards): stationary dog and sweeping spray at 300m+`

---

## Task 17: 청소기 (500m+) — 영구 추격

**파일:** 수정 `entities/hazards.py`, `scenes/game.py`

청소기는 특별: 게임당 **단 하나만** 존재, 카메라 하단부터 일정 속도(60 px/s)로 상승, `lethal = True`. 한번 스폰되면 멈추지 않음.

- [ ] **Step 1**: `Vacuum(Hazard)` 클래스 추가
- [ ] **Step 2**: GameScene 에 `_vacuum_spawned` 플래그, 청소기 종류는 카메라 하단에 직접 스폰 + 1회 제한
- [ ] **Step 3-4**: 스모크 테스트 + 커밋
- 커밋 메시지: `feat(hazards): permanent rising vacuum at 500m+`

---

## Task 18: 아이템 (참치캔 / 개다래 / 깃털 / 물고기)

**파일:**
- 생성: `entities/items.py`
- 수정: `world/generator.py`, `scenes/game.py`

아이템은 패시브: 플레이어가 겹치면 효과 발동. 청크당 50% 확률로 1개 스폰, 희소성에 따라 가중치 (tuna 0.6, feather 0.2, catnip 0.15, fish 0.05).

**효과:**
- TunaCan: tuna 카운터 +1
- Catnip: `invincible_timer = 5.0`
- Feather: `jump_boost_timer = 5.0` (점프 속도 1.4x)
- Fish: 목숨 +1 (MAX_LIVES 미만일 때만)

- [ ] **Step 1-5**: 영문본 동일.
- 커밋 메시지: `feat(items): tuna/catnip/feather/fish pickups with effects`

---

## Task 19: HUD 라이브 값 + "다음 위협" 계산

**파일:**
- 생성: `world/next_hazard.py`
- 수정: `main.py`

`next_hazard(altitude_m) -> (label, altitude_m)` 헬퍼가 다음 미해금 위협을 반환.

- [ ] **Step 1-4**: 영문본 동일.
- 커밋 메시지: `feat(hud): live altitude/lives/tuna and next-hazard preview`

---

## Task 20: 메뉴 씬 + 최고점수 영속화

**파일:**
- 생성: `scenes/menu.py`, `engine/highscore.py`
- 수정: `main.py`

`engine/highscore.py`: `load_high_score()`, `save_high_score(score_m)` 두 함수. JSON 형식 `{"high_score_m": <int>}`.

`scenes/menu.py`: 타이틀 + BEST + "Press SPACE/ENTER to start".

`main.py`: 씬 상태 머신 (menu → game → gameover). 게임오버 시 신기록이면 `data/highscore.json` 에 즉시 저장.

- [ ] **Step 1-5**: 영문본 동일.
- 커밋 메시지: `feat(scenes): menu + high-score persistence wired into scene flow`

---

## Task 21: 사운드 시스템 + placeholder 에셋

**파일:**
- 생성: `engine/audio.py`, `tools/generate_placeholder_sfx.py`, `assets/sounds/*.wav`
- 수정: `entities/player.py`, `entities/platforms.py`, `scenes/game.py`, `main.py`

`engine/audio.py`: `init()`, `play(name)`, `start_bgm(volume)` API.

`tools/generate_placeholder_sfx.py`: 8-bit WAV 톤을 `wave` + `struct` 로 생성 (jump/land/pickup/hit/gameover). 외부 에셋 파이프라인 불필요.

BGM은 `assets/music/bgm_loop.ogg` 가 있을 때만 재생, 없으면 no-op (D안 = 마무리 단계에 본 BGM 결정).

**player/platforms 에 `just_jumped`, `just_landed` 플래그 추가** → 씬이 매 프레임 확인하고 사운드 트리거.

- [ ] **Step 1-6**: 영문본 동일.
- 커밋 메시지: `feat(audio): SFX wrapper + placeholder tones; BGM hook is no-op until file present`

---

## Task 22: 시각 폴리싱 — 하늘 / 플레이어 애니메이션 / i-frame 깜빡임

**파일:**
- 생성: `entities/player_render.py`
- 수정: `scenes/game.py`

두 가지 출시:
1. 고도별 하늘색 전환 + 우주 별빛
2. 플레이어 5개 상태 시각화: idle / run / jump / fall / hurt

**`entities/player_render.py`:** 향후 sprite sheet 로 교체할 수 있는 단일 seam. 현재는 primitives (타원 몸통 + 귀 삼각형 + 눈 점) 로 32×32 footprint 그림.

**상태별 표현:**
- jump: 가로 0.85x, 세로 1.15x squash/stretch
- fall: 가로 1.10x, 세로 0.90x
- hurt: i-frame 동안 0.1s 주기로 점멸
- run: 미세한 사인 진동
- 눈 위치: vx 부호에 따라 좌/우로 시선 변경

**하늘 색 곡선:**
- 0~150m: 푸른 낮
- 150~350m: 주황 노을
- 350~500m: 짙은 보라 밤
- 500m+: 검은 우주 + 별 (카메라 위치 시드 결정론)

- [ ] **Step 1-5**: 영문본 동일.
- 커밋 메시지: `feat(visuals): player state animations + altitude-banded sky/stars`

---

## 최종 검증

- [ ] **전체 테스트 스위트 실행**
```bash
pytest -v
```
모두 통과 기대.

- [ ] **수동 E2E 실행**
```bash
python main.py
```
체크리스트:
1. 메뉴 → SPACE 시작
2. 점프/착지/등반 (절차 생성 발판)
3. 50m 쥐, 150m 까마귀, 300m 강아지/분무기, 500m 청소기 + 우주 하늘
4. 참치캔 카운트, 개다래 무적, 깃털 점프 부스트, 물고기 목숨 회복
5. 추락 또는 목숨 0 → Game Over, 도달 고도 표시
6. 신기록 시 `data/highscore.json` 갱신
7. 사이드 HUD 가 ALTITUDE / BEST / LIVES / NEXT HAZARD / TUNA 지속 표시

- [ ] **검증 중 추가 폴리싱이 있다면 마지막 커밋**

---

## Plan 완료

저장 위치: `docs/superpowers/plans/2026-05-03-dongles-adventure.ko.md`
