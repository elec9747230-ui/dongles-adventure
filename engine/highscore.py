"""High-score persistence for Dongle's Adventure.

Persists the player's best altitude (in metres) as a tiny JSON document on
disk so it survives between runs. The format is deliberately minimal —
``{"high_score_m": <int>}`` — to keep the file forward/backward compatible
and trivial to inspect or hand-edit.

Robustness notes:

- :func:`load_high_score` treats ANY failure (missing file, malformed JSON,
  bad type, I/O error) as "no previous score" and returns ``0``. We never
  want a corrupt save file to crash the launcher.
- :func:`save_high_score` ensures the parent directory exists before writing.
  The write itself is a single short ``json.dump`` so partial writes are
  unlikely in practice; a full atomic rename (write-temp + ``os.replace``)
  could be added later if torn writes ever appear in the wild.
"""
from __future__ import annotations

import json
import os

import settings


def load_high_score() -> int:
    """Load the persisted high score from disk.

    Returns:
        The stored high score in metres, or ``0`` if no valid save exists.

    Why swallow every error: a fresh install has no file, and a corrupt file
    on a player's machine should not block them from playing — it should just
    reset their record. We catch ``OSError`` (permissions, disk), ``ValueError``
    (``int()`` of non-numeric content) and ``json.JSONDecodeError`` (malformed
    JSON) and treat them all as "start from 0".
    """
    if not os.path.exists(settings.HIGHSCORE_PATH):
        return 0
    try:
        with open(settings.HIGHSCORE_PATH, encoding="utf-8") as f:
            data = json.load(f)
        # ``.get`` with a default keeps us safe if a future version of the file
        # ever drops the field; ``int()`` coerces stray floats/strings.
        return int(data.get("high_score_m", 0))
    except (OSError, ValueError, json.JSONDecodeError):
        return 0


def save_high_score(score_m: int) -> None:
    """Persist the high score to disk, creating parent directories as needed.

    Args:
        score_m: New high-score value in metres. Coerced to ``int`` so the
            on-disk format always stores a whole number, regardless of how
            the caller computed the score (e.g. from a float altitude).

    Returns:
        None.

    Note:
        This writes the file in-place rather than using a write-then-rename
        atomic swap. The payload is a few bytes and is written in a single
        ``json.dump`` call, so the window for a torn write is essentially
        the OS-level fwrite buffer flush — small enough that we accept the
        risk for now. If save corruption becomes a real-world issue, switch
        to writing ``settings.HIGHSCORE_PATH + ".tmp"`` and calling
        :func:`os.replace` to commit.
    """
    # ``exist_ok=True`` makes this idempotent — fresh install AND repeat saves
    # both work without an explicit "first run" branch.
    os.makedirs(os.path.dirname(settings.HIGHSCORE_PATH), exist_ok=True)
    with open(settings.HIGHSCORE_PATH, "w", encoding="utf-8") as f:
        json.dump({"high_score_m": int(score_m)}, f)
