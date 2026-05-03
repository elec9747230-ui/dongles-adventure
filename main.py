"""Dongle's Adventure - entry point."""
from __future__ import annotations

import sys

import pygame

import settings


def main() -> int:
    pygame.init()
    screen = pygame.display.set_mode((settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT))
    pygame.display.set_caption("Dongle's Adventure")
    clock = pygame.time.Clock()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False

        screen.fill(settings.COLOR_BG)
        # Game area placeholder
        pygame.draw.rect(
            screen,
            settings.COLOR_GAME_BG,
            (settings.GAME_AREA_X, settings.GAME_AREA_Y, settings.GAME_AREA_WIDTH, settings.GAME_AREA_HEIGHT),
        )
        # HUD panels
        pygame.draw.rect(
            screen, settings.COLOR_HUD_BG,
            (settings.LEFT_HUD_X, 0, settings.LEFT_HUD_WIDTH, settings.WINDOW_HEIGHT),
        )
        pygame.draw.rect(
            screen, settings.COLOR_HUD_BG,
            (settings.RIGHT_HUD_X, 0, settings.RIGHT_HUD_WIDTH, settings.WINDOW_HEIGHT),
        )

        pygame.display.flip()
        clock.tick(settings.FPS)

    pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
