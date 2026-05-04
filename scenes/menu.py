"""Title / menu scene.

This is the entry point of the scene flow:

    menu  ->  game  ->  gameover  ->  menu (or new game)

The menu displays the title art and the player's best altitude record. It waits
for SPACE or ENTER, at which point the parent scene manager transitions to the
gameplay scene by reading ``start_requested``.
"""
from __future__ import annotations

import pygame

import settings


class MenuScene:
    """Title screen displayed before a run starts.

    Renders the game logo, the best-recorded altitude, and a prompt asking the
    player to press SPACE / ENTER. This scene performs no simulation work; it
    simply flips ``start_requested`` to True when the player confirms, and the
    outer scene manager observes that flag to swap to the gameplay scene.

    Attributes:
        best_m: The best altitude (in meters) recorded across previous runs.
            Passed in by the scene manager so persistence stays out of the scene.
        start_requested: Becomes True once the player presses SPACE or ENTER.
            The scene manager polls this between frames to advance the flow.
        font_title: Large bold font used for the two-line "DONGLE'S ADVENTURE"
            title.
        font_med: Mid-size font used for the best-score line and prompt.
    """

    def __init__(self, *, best_m: int) -> None:
        """Build the menu scene with the given best score.

        Args:
            best_m: Best altitude (meters) ever achieved; shown to the player.
        """
        self.best_m = best_m
        self.start_requested = False
        # Font subsystem is idempotent; init() here ensures it is safe even if
        # the menu is constructed before the main module has initialized it.
        pygame.font.init()
        self.font_title = pygame.font.SysFont("consolas", 80, bold=True)
        self.font_med = pygame.font.SysFont("consolas", 32)

    def begin_frame(self) -> None:
        """Per-frame hook called before event dispatch.

        The menu has no per-frame setup, but the method exists so the scene
        manager can call it uniformly across all scene types.
        """
        pass

    def handle_event(self, event: pygame.event.Event) -> None:
        """Process a single input event.

        Watches for SPACE or ENTER key-down events to request a transition into
        the gameplay scene. Any other event is ignored.

        Args:
            event: A pygame event from the main event queue.
        """
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE):
            # Flag-based transition keeps scene-switching logic out of this
            # scene; the manager owns the actual swap.
            self.start_requested = True

    def update(self, dt: float) -> None:
        """Advance scene state. The static menu has nothing to update.

        Args:
            dt: Frame delta time in seconds (unused).
        """
        pass

    def draw(self, window: pygame.Surface) -> None:
        """Render the title art, best score, and start prompt.

        All text is centered on the gameplay viewport (not the full window) so
        the side HUD areas remain free even on the menu.

        Args:
            window: The main display surface to blit onto.
        """
        # Center coordinates within the game viewport (not the entire window),
        # so the title sits over the gameplay area regardless of HUD widths.
        cx = settings.GAME_AREA_X + settings.GAME_AREA_WIDTH // 2
        cy = settings.GAME_AREA_Y + settings.GAME_AREA_HEIGHT // 2
        title = self.font_title.render("DONGLE'S", True, settings.COLOR_HUD_ACCENT)
        title2 = self.font_title.render("ADVENTURE", True, settings.COLOR_HUD_ACCENT)
        window.blit(title, title.get_rect(center=(cx, cy - 200)))
        window.blit(title2, title2.get_rect(center=(cx, cy - 110)))

        best = self.font_med.render(f"BEST  {self.best_m} m", True, settings.COLOR_HUD_TEXT)
        window.blit(best, best.get_rect(center=(cx, cy + 20)))

        prompt = self.font_med.render("Press SPACE / ENTER to start", True, settings.COLOR_HUD_TEXT)
        window.blit(prompt, prompt.get_rect(center=(cx, cy + 100)))
