"""Dongle's Adventure - entry point.

Boots Pygame, owns the main loop, and orchestrates a tiny scene state machine
(menu -> game -> gameover -> game). Heavy game modules are imported *inside*
``main()`` so the splash window appears immediately while the rest of the
engine wakes up.
"""
from __future__ import annotations

import sys

import pygame

import settings


def main() -> int:
    """Run the game until the player quits.

    Returns:
        Process exit code (0 = clean exit). Suitable to pass to ``sys.exit``.
    """
    # Pygame init order matters: the core subsystems must be up before any
    # display or font surface is created.
    pygame.init()
    pygame.font.init()
    screen = pygame.display.set_mode((settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT))
    pygame.display.set_caption("Dongle's Adventure")
    clock = pygame.time.Clock()

    # Deferred imports: these modules transitively pull in pygame surfaces and
    # asset loading, so we wait until after ``set_mode`` to keep startup snappy
    # and to avoid surface-conversion warnings.
    from engine import audio
    from engine.highscore import load_high_score, save_high_score
    from scenes._hud import Hud
    from scenes.game import GameScene
    from scenes.gameover import GameOverScene
    from scenes.menu import MenuScene
    from world.next_hazard import next_hazard

    audio.init()
    audio.start_bgm()

    # Scene-stack init: we don't use a real stack because transitions are
    # strictly linear (menu -> game -> gameover -> game). A single ``state``
    # string plus three optional scene slots is simpler and avoids the
    # bookkeeping of push/pop semantics we'd never use.
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

        # ``tick`` returns the elapsed milliseconds since the previous call and
        # also caps the loop to FPS. Convert to seconds so physics integration
        # in the scenes can use SI-friendly units.
        dt = clock.tick(settings.FPS) / 1000.0

        if state == "menu":
            menu.update(dt)
            if menu.start_requested:
                scene = GameScene()
                state = "game"
        elif state == "game":
            scene.update(dt)
            if scene.dead:
                # Persist the high score *only* when beaten; this avoids
                # rewriting the file on every death.
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
                # Drop the previous GameScene so its world/chunks/entities are
                # garbage-collected before the new run allocates its own.
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

    # Exit cleanup: release SDL/audio handles before the process exits so the
    # OS doesn't leak the audio device on rapid relaunches.
    pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
