"""Game Over scene - shows result and waits for restart.

Final stop in the scene flow:

    menu  ->  game  ->  gameover  ->  (menu or new game)

The scene is intentionally lightweight: it captures the run summary handed in
by the gameplay scene, dims the game viewport with a translucent overlay, and
waits for the restart key (typically R) before signaling the scene manager to
return to the menu / start a fresh run.
"""
from __future__ import annotations

import pygame

import settings


class GameOverScene:
    """End-of-run summary screen shown after the player dies.

    Displays the player's final altitude (which is the score, since score is
    defined as the maximum height reached during the run), the best record,
    and a "NEW RECORD!" banner if this run beat the prior best. Waits for the
    configured restart key to flag a transition back to gameplay.

    Attributes:
        altitude_m: Final altitude reached during the just-finished run, in
            meters. This is the player's score for the run.
        best_m: Highest altitude achieved across all runs (including this one
            if it was a new record).
        new_record: True if ``altitude_m`` set a new best; controls whether the
            "NEW RECORD!" banner replaces the "Best: X m" line.
        restart_requested: Set to True once the player presses the restart key.
            The scene manager polls this to advance back to the menu / game.
        font_huge: Large bold font used for the GAME OVER headline.
        font_med: Mid-size font used for the result, record and hint lines.
    """

    def __init__(self, *, altitude_m: int, best_m: int, new_record: bool) -> None:
        """Capture the run summary to display.

        Args:
            altitude_m: Score (max altitude reached) for the finished run.
            best_m: Best altitude across all runs.
            new_record: Whether ``altitude_m`` is a new personal best.
        """
        self.altitude_m = altitude_m
        self.best_m = best_m
        self.new_record = new_record
        self.restart_requested = False
        pygame.font.init()
        self.font_huge = pygame.font.SysFont("consolas", 72, bold=True)
        self.font_med = pygame.font.SysFont("consolas", 32)

    def begin_frame(self) -> None:
        """Per-frame setup hook; nothing to do for a static screen."""
        pass

    def handle_event(self, event: pygame.event.Event) -> None:
        """Watch for the restart key to request a scene transition.

        Args:
            event: A pygame event from the main event queue.
        """
        # Restart key is centralized in settings so it can be rebound without
        # touching scene code.
        if event.type == pygame.KEYDOWN and event.key == settings.KEY_RESTART:
            self.restart_requested = True

    def update(self, dt: float) -> None:
        """No simulation runs on the game-over screen.

        Args:
            dt: Frame delta time in seconds (unused).
        """
        pass

    def draw(self, window: pygame.Surface) -> None:
        """Render the dim overlay, headline, score, record state and restart hint.

        Args:
            window: The main display surface to draw onto.
        """
        # Translucent black overlay sits over the gameplay viewport so the last
        # rendered frame of gameplay (already on `window` from the prior draw)
        # is still visible but de-emphasized.
        overlay = pygame.Surface(
            (settings.GAME_AREA_WIDTH, settings.GAME_AREA_HEIGHT), pygame.SRCALPHA
        )
        overlay.fill((0, 0, 0, 180))
        window.blit(overlay, (settings.GAME_AREA_X, settings.GAME_AREA_Y))

        # Center text within the gameplay viewport (HUD areas stay untouched).
        cx = settings.GAME_AREA_X + settings.GAME_AREA_WIDTH // 2
        cy = settings.GAME_AREA_Y + settings.GAME_AREA_HEIGHT // 2

        title = self.font_huge.render("GAME OVER", True, settings.COLOR_HUD_ACCENT)
        window.blit(title, title.get_rect(center=(cx, cy - 100)))

        result = self.font_med.render(
            f"You reached {self.altitude_m} m", True, settings.COLOR_HUD_TEXT,
        )
        window.blit(result, result.get_rect(center=(cx, cy - 20)))

        # Either show the celebratory new-record banner OR the prior best — not
        # both, to keep the layout compact and the message unambiguous.
        if self.new_record:
            rec = self.font_med.render("NEW RECORD!", True, settings.COLOR_HUD_ACCENT)
            window.blit(rec, rec.get_rect(center=(cx, cy + 20)))
        else:
            best = self.font_med.render(
                f"Best: {self.best_m} m", True, settings.COLOR_HUD_TEXT,
            )
            window.blit(best, best.get_rect(center=(cx, cy + 20)))

        hint = self.font_med.render("Press R to restart", True, settings.COLOR_HUD_TEXT)
        window.blit(hint, hint.get_rect(center=(cx, cy + 100)))
