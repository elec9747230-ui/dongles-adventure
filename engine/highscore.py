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
