"""Title / menu scene."""
from __future__ import annotations

import pygame

import settings


class MenuScene:
    def __init__(self, *, best_m: int) -> None:
        self.best_m = best_m
        self.start_requested = False
        pygame.font.init()
        self.font_title = pygame.font.SysFont("consolas", 80, bold=True)
        self.font_med = pygame.font.SysFont("consolas", 32)

    def begin_frame(self) -> None:
        pass

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE):
            self.start_requested = True

    def update(self, dt: float) -> None:
        pass

    def draw(self, window: pygame.Surface) -> None:
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
