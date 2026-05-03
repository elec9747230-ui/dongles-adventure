"""Audio playback wrapper. Lazy-loads on init."""
from __future__ import annotations

import os

import pygame


_SFX: dict[str, pygame.mixer.Sound] = {}
_BGM_PATH: str | None = None


def init() -> None:
    global _BGM_PATH
    try:
        pygame.mixer.init()
    except pygame.error:
        # No audio device — game still runs silently.
        return
    base = "assets/sounds"
    for name in ("jump", "land", "pickup", "hit", "gameover"):
        path = os.path.join(base, f"{name}.wav")
        if os.path.exists(path):
            try:
                _SFX[name] = pygame.mixer.Sound(path)
            except pygame.error:
                pass
    for ext in ("ogg", "wav", "mp3"):
        candidate = os.path.join("assets", "music", f"bgm_loop.{ext}")
        if os.path.exists(candidate):
            _BGM_PATH = candidate
            break


def play(name: str) -> None:
    s = _SFX.get(name)
    if s is not None:
        s.set_volume(0.5)
        s.play()


def start_bgm(volume: float = 0.4) -> None:
    if _BGM_PATH is None:
        return
    try:
        pygame.mixer.music.load(_BGM_PATH)
        pygame.mixer.music.set_volume(volume)
        pygame.mixer.music.play(loops=-1)
    except pygame.error:
        pass
