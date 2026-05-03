"""Game Over scene - shows result and waits for restart."""
from __future__ import annotations

import pygame

import settings


class GameOverScene:
    def __init__(self, *, altitude_m: int, best_m: int, new_record: bool) -> None:
        self.altitude_m = altitude_m
        self.best_m = best_m
        self.new_record = new_record
        self.restart_requested = False
        pygame.font.init()
        self.font_huge = pygame.font.SysFont("consolas", 72, bold=True)
        self.font_med = pygame.font.SysFont("consolas", 32)

    def begin_frame(self) -> None:
        pass

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == settings.KEY_RESTART:
            self.restart_requested = True

    def update(self, dt: float) -> None:
        pass

    def draw(self, window: pygame.Surface) -> None:
        # Dim the game area
        overlay = pygame.Surface(
            (settings.GAME_AREA_WIDTH, settings.GAME_AREA_HEIGHT), pygame.SRCALPHA
        )
        overlay.fill((0, 0, 0, 180))
        window.blit(overlay, (settings.GAME_AREA_X, settings.GAME_AREA_Y))

        cx = settings.GAME_AREA_X + settings.GAME_AREA_WIDTH // 2
        cy = settings.GAME_AREA_Y + settings.GAME_AREA_HEIGHT // 2

        title = self.font_huge.render("GAME OVER", True, settings.COLOR_HUD_ACCENT)
        window.blit(title, title.get_rect(center=(cx, cy - 100)))

        result = self.font_med.render(
            f"You reached {self.altitude_m} m", True, settings.COLOR_HUD_TEXT,
        )
        window.blit(result, result.get_rect(center=(cx, cy - 20)))

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
