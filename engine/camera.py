"""Vertical-scroll camera for Dongle's Adventure.

The camera tracks the maximum altitude reached. It never scrolls back down.
"""
from __future__ import annotations


class Camera:
    """Tracks `y_top`: world_y altitude that maps to screen y=0."""

    def __init__(self, screen_height: int, player_offset_from_top: int) -> None:
        self.screen_height = screen_height
        self.player_offset_from_top = player_offset_from_top
        self.y_top: float = 0.0

    def follow(self, player_world_y: float) -> None:
        """Update y_top to keep player at the configured screen offset, monotonically."""
        target = player_world_y + self.player_offset_from_top
        if target > self.y_top:
            self.y_top = target

    def world_to_screen_y(self, world_y: float) -> float:
        """Convert world altitude to screen y (top-of-screen is 0; increases downward)."""
        return self.y_top - world_y

    def is_below_screen(self, world_y: float) -> bool:
        """True when a world point is below the current visible region."""
        bottom_world_y = self.y_top - self.screen_height
        return world_y < bottom_world_y
