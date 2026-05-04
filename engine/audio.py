"""Audio playback wrapper for Dongle's Adventure.

This module is a thin facade over ``pygame.mixer`` that lazily loads short
sound effects (SFX) from ``assets/sounds`` and a single looping background
music track (BGM) from ``assets/music``. SFX are kept in an in-memory dict
of ``pygame.mixer.Sound`` objects (decoded once, played many times), while
BGM is streamed via ``pygame.mixer.music`` so we never load a long track
fully into RAM.

Design decisions:
- The mixer is initialized inside :func:`init` rather than at import time so
  the game still launches on machines without an audio device (we silently
  swallow ``pygame.error`` and operate in mute mode).
- SFX and BGM use *separate* pygame channels by design: ``mixer.Sound`` plays
  on dynamically-allocated SFX channels, while ``mixer.music`` is a dedicated
  streaming channel. This guarantees a loud SFX (e.g. "hit") never preempts
  the looping BGM, and lets us tune their volumes independently.
"""
from __future__ import annotations

import os

import pygame


# Module-level caches. We keep these as globals (rather than wrapping them in
# a class) because the audio system is a process-wide singleton — pygame.mixer
# itself is global, so adding our own object layer would be ceremony only.
_SFX: dict[str, pygame.mixer.Sound] = {}
_BGM_PATH: str | None = None


def init() -> None:
    """Initialize the mixer and preload all available SFX / locate BGM.

    Scans ``assets/sounds`` for a fixed set of named WAV effects and
    ``assets/music`` for a ``bgm_loop.{ogg,wav,mp3}`` track (first match wins,
    in that preference order — OGG first because it is small and seamlessly
    loopable, MP3 last because some builds of SDL_mixer have gapless-loop
    issues with MP3).

    Returns:
        None.

    Raises:
        Never. All pygame errors are swallowed so the game can run in mute
        mode on systems without an audio device or codec.
    """
    global _BGM_PATH
    try:
        # Default mixer params (frequency=44100, size=-16, channels=2, buffer=512)
        # are fine for short SFX; we deliberately do not pre_init() so users on
        # exotic hardware can override via env vars before calling init().
        pygame.mixer.init()
    except pygame.error:
        # No audio device — game still runs silently.
        return
    base = "assets/sounds"
    # Hard-coded effect roster: any missing file is simply skipped, so the
    # game degrades gracefully if an artist hasn't delivered a sound yet.
    for name in ("jump", "land", "pickup", "hit", "gameover"):
        path = os.path.join(base, f"{name}.wav")
        if os.path.exists(path):
            try:
                _SFX[name] = pygame.mixer.Sound(path)
            except pygame.error:
                # Corrupt or unsupported file — leave it out of the dict so
                # play() becomes a no-op for that name.
                pass
    # Probe extensions in order of preference; stop at first hit.
    for ext in ("ogg", "wav", "mp3"):
        candidate = os.path.join("assets", "music", f"bgm_loop.{ext}")
        if os.path.exists(candidate):
            _BGM_PATH = candidate
            break


def play(name: str) -> None:
    """Play a one-shot sound effect by logical name.

    Args:
        name: Logical SFX key, e.g. ``"jump"`` or ``"hit"``. Must match a name
            preloaded by :func:`init`. Unknown names are silently ignored
            (this lets gameplay code call ``play("foo")`` without guarding
            for missing assets).

    Returns:
        None.
    """
    s = _SFX.get(name)
    if s is not None:
        # 0.5 keeps SFX clearly audible but well below the BGM ceiling so
        # stacked effects never clip the master output.
        s.set_volume(0.5)
        s.play()


def start_bgm(volume: float = 0.4) -> None:
    """Begin (or restart) the looping background music track.

    Args:
        volume: Linear gain in [0.0, 1.0]. Default 0.4 sits below the SFX
            volume so dialogue/effects always cut through.

    Returns:
        None.
    """
    if _BGM_PATH is None:
        return
    try:
        pygame.mixer.music.load(_BGM_PATH)
        pygame.mixer.music.set_volume(volume)
        # loops=-1 means "loop forever". The streaming music channel is
        # independent from the SFX channels, so this never starves play().
        pygame.mixer.music.play(loops=-1)
    except pygame.error:
        # Codec missing at runtime, etc. — fall back to silence.
        pass
