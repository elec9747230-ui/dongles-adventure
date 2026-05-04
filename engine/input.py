"""Per-frame input snapshot helper for Dongle's Adventure.

Tracks which keys went DOWN this frame in addition to held state, so callers
can distinguish "jump just pressed" (one-shot edge action) from "jump still
held" (variable-jump-height ramp). This split is essential for platformers:

- *Edge* events drive discrete actions (jump kickoff, menu confirm, pause).
- *Held* state drives continuous actions (run, charge, variable jump).

The class itself is stateful but tiny; the game loop is expected to call
:meth:`InputState.begin_frame` once per frame and feed every pygame event
through :meth:`InputState.handle_event`.
"""
from __future__ import annotations

import pygame


class InputState:
    """Edge- and held-key snapshot for a single frame of the game loop.

    Attributes:
        _pressed_this_frame (set[int]): Pygame key codes that received a
            ``KEYDOWN`` event since the last :meth:`begin_frame` call. Cleared
            each frame so :meth:`was_pressed` returns ``True`` for exactly one
            frame per physical key press (the "edge").
        _held (set[int]): Pygame key codes currently held down, accumulated
            across frames. A key joins on ``KEYDOWN`` and leaves on ``KEYUP``,
            mirroring physical key state for the lifetime of the program.
    """

    def __init__(self) -> None:
        """Initialize an empty input state.

        Returns:
            None.
        """
        self._pressed_this_frame: set[int] = set()
        self._held: set[int] = set()

    def begin_frame(self) -> None:
        """Reset the per-frame edge buffer; call once at the top of each frame.

        Returns:
            None.

        Why only the edge buffer: ``_held`` must persist across frames so a
        key the user holds down for several seconds keeps reporting
        ``is_held() == True``. Only the "just pressed" set is per-frame.
        """
        self._pressed_this_frame.clear()

    def handle_event(self, event: pygame.event.Event) -> None:
        """Fold a single pygame event into the current input state.

        Args:
            event: A pygame event from ``pygame.event.get()``. Non-key events
                are silently ignored so the caller can route ALL events here
                without filtering.

        Returns:
            None.
        """
        if event.type == pygame.KEYDOWN:
            # KEYDOWN populates BOTH sets: the edge (for one-frame triggers)
            # and the held set (so subsequent frames still see it as held
            # until the matching KEYUP arrives).
            self._pressed_this_frame.add(event.key)
            self._held.add(event.key)
        elif event.type == pygame.KEYUP:
            # ``discard`` (not ``remove``) is intentional: pygame can in rare
            # cases emit KEYUP without a matching KEYDOWN (e.g. window focus
            # transitions), and we don't want a KeyError to crash the loop.
            self._held.discard(event.key)

    def is_held(self, key: int) -> bool:
        """Return whether ``key`` is currently held down.

        Args:
            key: Pygame key code, e.g. ``pygame.K_SPACE``.

        Returns:
            ``True`` while the physical key is depressed; ``False`` otherwise.
        """
        return key in self._held

    def was_pressed(self, key: int) -> bool:
        """Return whether ``key`` transitioned to DOWN during this frame.

        Args:
            key: Pygame key code, e.g. ``pygame.K_SPACE``.

        Returns:
            ``True`` only on the single frame when the KEYDOWN was received.
            On every subsequent frame (even while the key is still held)
            this returns ``False`` — that's the whole point of edge detection.
        """
        return key in self._pressed_this_frame
