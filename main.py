"""Dongle's Adventure - entry point."""
from __future__ import annotations

import sys

import pygame

import settings


def main() -> int:
    pygame.init()
    pygame.font.init()
    screen = pygame.display.set_mode((settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT))
    pygame.display.set_caption("Dongle's Adventure")
    clock = pygame.time.Clock()

    from engine import audio
    from engine.highscore import load_high_score, save_high_score
    from scenes._hud import Hud
    from scenes.game import GameScene
    from scenes.gameover import GameOverScene
    from scenes.menu import MenuScene
    from world.next_hazard import next_hazard

    audio.init()
    audio.start_bgm()

    hud = Hud()
    best_m = load_high_score()
    state = "menu"  # menu | game | gameover
    menu = MenuScene(best_m=best_m)
    scene: GameScene | None = None
    gameover: GameOverScene | None = None

    running = True
    while running:
        # Per-frame begin (only the active scene needs it)
        if state == "menu":
            menu.begin_frame()
        elif state == "game":
            scene.begin_frame()
        else:
            gameover.begin_frame()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                continue
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
                continue
            if state == "menu":
                menu.handle_event(event)
            elif state == "game":
                scene.handle_event(event)
            else:
                gameover.handle_event(event)

        dt = clock.tick(settings.FPS) / 1000.0

        if state == "menu":
            menu.update(dt)
            if menu.start_requested:
                scene = GameScene()
                state = "game"
        elif state == "game":
            scene.update(dt)
            if scene.dead:
                final_m = scene.player.altitude_m
                new_record = final_m > best_m
                if new_record:
                    best_m = final_m
                    save_high_score(best_m)
                gameover = GameOverScene(altitude_m=final_m, best_m=best_m, new_record=new_record)
                state = "gameover"
        else:  # gameover
            gameover.update(dt)
            if gameover.restart_requested:
                scene = GameScene()
                gameover = None
                state = "game"

        # Render
        screen.fill(settings.COLOR_BG)
        # HUD panel backgrounds
        pygame.draw.rect(
            screen, settings.COLOR_HUD_BG,
            (settings.LEFT_HUD_X, 0, settings.LEFT_HUD_WIDTH, settings.WINDOW_HEIGHT),
        )
        pygame.draw.rect(
            screen, settings.COLOR_HUD_BG,
            (settings.RIGHT_HUD_X, 0, settings.RIGHT_HUD_WIDTH, settings.WINDOW_HEIGHT),
        )

        if state == "menu":
            pygame.draw.rect(
                screen, settings.COLOR_GAME_BG,
                (settings.GAME_AREA_X, settings.GAME_AREA_Y,
                 settings.GAME_AREA_WIDTH, settings.GAME_AREA_HEIGHT),
            )
            menu.draw(screen)
            hud.draw(
                screen,
                altitude_m=0, best_m=best_m, lives=settings.START_LIVES,
                tuna=0, next_hazard_label="Yarn", next_hazard_m=0,
            )
        else:
            scene.draw(screen)
            nh_label, nh_m = next_hazard(scene.player.altitude_m)
            hud.draw(
                screen,
                altitude_m=scene.player.altitude_m, best_m=best_m,
                lives=max(0, scene.player.lives), tuna=scene.tuna_count,
                next_hazard_label=nh_label, next_hazard_m=nh_m,
                active_powerups=scene.active_powerups(),
            )
            if state == "gameover":
                gameover.draw(screen)

        pygame.display.flip()

    pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
