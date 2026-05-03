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
