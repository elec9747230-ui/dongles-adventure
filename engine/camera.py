"""Vertical-scroll camera for Dongle's Adventure.

The camera tracks the maximum altitude reached and never scrolls back down,
which is the core feel of an endless vertical climber: falling off a platform
is punishing because the world below has already left the screen.

Coordinate conventions (consistent with :mod:`engine.physics`):

- World space: ``world_y`` increases UPWARD (altitude in pixels).
- Screen space: ``screen_y`` increases DOWNWARD (pygame convention,
  origin at top-left).
- The camera stores ``y_top``: the world altitude that currently maps to
  ``screen_y == 0`` (the top edge of the window). Therefore the visible
  vertical band in world space is ``[y_top - screen_height, y_top]``.
"""
from __future__ import annotations


class Camera:
    """One-way vertical scrolling camera.

    The camera follows the player upward by tracking the highest altitude
    they have reached, offset so the player rests near the top of the
    viewport. It is monotonic — once ``y_top`` increases it never decreases,
    so anything that falls below the visible band is permanently lost.

    Attributes:
        screen_height (int): Window height in pixels; defines how much world
            below ``y_top`` is currently visible.
        player_offset_from_top (int): Desired distance (in pixels) between
            the player and the top of the screen. A larger value gives the
            player more headroom to see what's coming.
        y_top (float): World altitude currently mapped to ``screen_y == 0``.
            Initialized to ``0.0`` and only ever increases.
    """

    def __init__(self, screen_height: int, player_offset_from_top: int) -> None:
        """Initialize the camera with viewport size and player headroom.

        Args:
            screen_height: Window height in pixels.
            player_offset_from_top: Pixels of headroom kept above the player.

        Returns:
            None.
        """
        self.screen_height = screen_height
        self.player_offset_from_top = player_offset_from_top
        self.y_top: float = 0.0

    def follow(self, player_world_y: float) -> None:
        """Update y_top to keep player at the configured screen offset, monotonically.

        Args:
            player_world_y: Current altitude of the player in world space.

        Returns:
            None.

        Why monotonic: in an endless climber we never want the camera to drop
        when the player falls — that would let the player "rewind" the world
        and undo the difficulty curve. So we only raise ``y_top``, never lower
        it. The target altitude is ``player_y + offset`` because adding the
        offset positions the player ``offset`` pixels below ``y_top`` (which
        is the top of the screen), giving them headroom to look up.
        """
        target = player_world_y + self.player_offset_from_top
        if target > self.y_top:
            self.y_top = target

    def world_to_screen_y(self, world_y: float) -> float:
        """Convert world altitude to screen y (top-of-screen is 0; increases downward).

        Args:
            world_y: Altitude in world space (up-positive).

        Returns:
            Screen-space y in pixels (down-positive). A point exactly at
            ``y_top`` returns ``0``; a point ``screen_height`` below ``y_top``
            returns ``screen_height``.

        Why ``y_top - world_y``: world is up-positive but screen is
        down-positive, so we flip the sign. ``y_top`` provides the offset that
        anchors the visible band.
        """
        return self.y_top - world_y

    def is_below_screen(self, world_y: float) -> bool:
        """True when a world point is below the current visible region.

        Args:
            world_y: Altitude to test.

        Returns:
            ``True`` if ``world_y`` lies strictly below the bottom edge of the
            viewport — i.e. it has scrolled off and can be culled / treated
            as a death plane.
        """
        # Bottom of the visible band lies exactly screen_height below y_top
        # in world space (because screen y grows downward over that range).
        bottom_world_y = self.y_top - self.screen_height
        return world_y < bottom_world_y
