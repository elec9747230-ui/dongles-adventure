"""Side HUD rendering for the 1920x1080 layout."""
from __future__ import annotations

import pygame

import settings


class Hud:
    def __init__(self) -> None:
        self.font_large = pygame.font.SysFont("consolas", 48, bold=True)
        self.font_med = pygame.font.SysFont("consolas", 28)
        self.font_small = pygame.font.SysFont("consolas", 20)

    def draw(
        self,
        window: pygame.Surface,
        *,
        altitude_m: int,
        best_m: int,
        lives: int,
        tuna: int,
        next_hazard_label: str,
        next_hazard_m: int,
        active_powerups: list[tuple[str, float]] | None = None,
    ) -> None:
        self._draw_left(
            window,
            altitude_m=altitude_m,
            best_m=best_m,
            lives=lives,
            active_powerups=active_powerups or [],
        )
        self._draw_right(
            window,
            altitude_m=altitude_m,
            tuna=tuna,
            next_hazard_label=next_hazard_label,
            next_hazard_m=next_hazard_m,
        )

    # ---------------------------------------------------------------- left

    def _draw_left(
        self,
        window: pygame.Surface,
        *,
        altitude_m: int,
        best_m: int,
        lives: int,
        active_powerups: list[tuple[str, float]],
    ) -> None:
        x0 = settings.LEFT_HUD_X + 40
        # ALTITUDE
        label = self.font_small.render("ALTITUDE", True, settings.COLOR_HUD_TEXT)
        window.blit(label, (x0, 60))
        value = self.font_large.render(f"{altitude_m} m", True, settings.COLOR_HUD_ACCENT)
        window.blit(value, (x0, 90))
        # BEST
        best = self.font_med.render(f"BEST  {best_m} m", True, settings.COLOR_HUD_TEXT)
        window.blit(best, (x0, 170))
        # LIVES
        lbl = self.font_small.render("LIVES", True, settings.COLOR_HUD_TEXT)
        window.blit(lbl, (x0, 240))
        for i in range(settings.MAX_LIVES):
            color = settings.COLOR_HUD_ACCENT if i < lives else (60, 60, 60)
            pygame.draw.circle(window, color, (x0 + 20 + i * 50, 290), 18)

        # POWERUPS
        pu_y = 360
        pu_label = self.font_small.render("POWERUPS", True, settings.COLOR_HUD_TEXT)
        window.blit(pu_label, (x0, pu_y))
        pu_y += 30
        if active_powerups:
            for name, remaining in active_powerups:
                txt = self.font_small.render(
                    f"  {name}  {remaining:.1f}s", True, settings.COLOR_HUD_ACCENT,
                )
                window.blit(txt, (x0, pu_y))
                pu_y += 28
        else:
            txt = self.font_small.render("  (none)", True, (120, 120, 120))
            window.blit(txt, (x0, pu_y))

        # CONTROLS
        ctl_y = 900
        for line in ["CONTROLS", "  <- ->  Move", "  SPACE  Jump", "  ESC    Pause"]:
            txt = self.font_small.render(line, True, settings.COLOR_HUD_TEXT)
            window.blit(txt, (x0, ctl_y))
            ctl_y += 30

    # ---------------------------------------------------------------- right

    def _draw_right(
        self,
        window: pygame.Surface,
        *,
        altitude_m: int,
        tuna: int,
        next_hazard_label: str,
        next_hazard_m: int,
    ) -> None:
        x0 = settings.RIGHT_HUD_X + 40
        scale_top_y = 100
        scale_bot_y = 800
        scale_top_m = 600
        pygame.draw.line(
            window, settings.COLOR_HUD_TEXT,
            (x0 + 60, scale_top_y), (x0 + 60, scale_bot_y), 2,
        )
        for mark_m in (50, 150, 300, 500):
            ratio = mark_m / scale_top_m
            y = int(scale_bot_y - (scale_bot_y - scale_top_y) * ratio)
            pygame.draw.line(window, settings.COLOR_HUD_TEXT, (x0 + 50, y), (x0 + 70, y), 2)
            txt = self.font_small.render(f"{mark_m}m", True, settings.COLOR_HUD_TEXT)
            window.blit(txt, (x0 + 80, y - 12))
        you_ratio = min(1.0, altitude_m / scale_top_m)
        you_y = int(scale_bot_y - (scale_bot_y - scale_top_y) * you_ratio)
        pygame.draw.polygon(
            window, settings.COLOR_HUD_ACCENT,
            [(x0 + 30, you_y - 8), (x0 + 30, you_y + 8), (x0 + 50, you_y)],
        )
        you = self.font_small.render(f"YOU {altitude_m}m", True, settings.COLOR_HUD_ACCENT)
        window.blit(you, (x0 - 20, you_y + 14))

        if next_hazard_m >= 0:
            nh = self.font_small.render(
                f"NEXT  {next_hazard_label} @ {next_hazard_m}m",
                True, settings.COLOR_HUD_TEXT,
            )
        else:
            nh = self.font_small.render(
                "NEXT  (all unlocked)", True, settings.COLOR_HUD_TEXT,
            )
        window.blit(nh, (x0, 850))
        tn = self.font_med.render(f"TUNA  {tuna}", True, settings.COLOR_HUD_TEXT)
        window.blit(tn, (x0, 900))
        hint = self.font_small.render("R: Restart", True, settings.COLOR_HUD_TEXT)
        window.blit(hint, (x0, 970))
