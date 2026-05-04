"""Side HUD rendering for the 1920x1080 layout.

The HUD lives in the two side columns flanking the central gameplay viewport
(see settings.LEFT_HUD_X / RIGHT_HUD_X / GAME_AREA_*). The gameplay scene draws
itself into the central viewport; this module fills the side columns.

Layout summary (left -> right):

    [ Left HUD ] [ Game viewport ] [ Right HUD ]
       ALTITUDE    (player + world)     altitude scale
       BEST                             YOU marker
       LIVES                            NEXT hazard
       POWERUPS                         TUNA count
       CONTROLS                         R: Restart hint

This module exposes a single ``Hud.draw(...)`` entry point. The gameplay scene
calls it once per frame after drawing the gameplay viewport; pure rendering, no
state of its own beyond cached fonts.
"""
from __future__ import annotations

import pygame

import settings


class Hud:
    """Stateless renderer for the left and right HUD columns.

    The HUD only owns its fonts; everything dynamic (altitude, lives, powerups,
    next hazard, tuna count) is passed into ``draw`` each frame by the gameplay
    scene. Score is shown as the player's current altitude in meters, which is
    the maximum height reached so far during the run.

    Attributes:
        font_large: Large bold font used for the headline altitude readout.
        font_med: Medium font used for the BEST line and TUNA counter.
        font_small: Small font used for labels, scale ticks, controls, etc.
    """

    def __init__(self) -> None:
        """Cache the three font sizes used across the HUD."""
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
        """Render both HUD columns onto ``window``.

        All dynamic data is passed in by the gameplay scene each frame, so the
        HUD can stay stateless and re-rendered cheaply at any time (e.g. during
        a pause overlay).

        Args:
            window: Main display surface; HUD draws into the side margins.
            altitude_m: Player's current/max altitude in meters (the score).
            best_m: All-time best altitude, displayed under the current value.
            lives: Remaining lives, shown as filled/empty dots.
            tuna: Collected tuna count, shown on the right column.
            next_hazard_label: Human-readable name of the next hazard tier.
            next_hazard_m: Altitude (meters) at which the next hazard unlocks;
                use a negative value to indicate "all hazards already unlocked".
            active_powerups: List of ``(name, seconds_remaining)`` tuples to
                show under the POWERUPS section. None or empty -> "(none)".
        """
        # Split into helpers so the two columns can be reasoned about and
        # tweaked independently without one bleeding into the other's keyword
        # argument list.
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
        """Render the left HUD column (altitude, best, lives, powerups, controls).

        Args:
            window: Display surface to draw onto.
            altitude_m: Player's current/max altitude in meters.
            best_m: All-time best altitude in meters.
            lives: Remaining lives count for the dot indicator.
            active_powerups: Active powerups as ``(name, remaining_seconds)``.
        """
        # 40px padding inside the left HUD column for breathing room.
        x0 = settings.LEFT_HUD_X + 40
        # ALTITUDE: small label above a large accent-colored value. This is the
        # player's score for the run (max height reached, in meters).
        label = self.font_small.render("ALTITUDE", True, settings.COLOR_HUD_TEXT)
        window.blit(label, (x0, 60))
        value = self.font_large.render(f"{altitude_m} m", True, settings.COLOR_HUD_ACCENT)
        window.blit(value, (x0, 90))
        # BEST altitude across all runs, sits under the current readout.
        best = self.font_med.render(f"BEST  {best_m} m", True, settings.COLOR_HUD_TEXT)
        window.blit(best, (x0, 170))
        # LIVES: render MAX_LIVES dots; first ``lives`` are accent-colored,
        # the rest are dimmed gray so the player can see life loss at a glance
        # (a dot turns dark on hit, becomes accent again on respawn).
        lbl = self.font_small.render("LIVES", True, settings.COLOR_HUD_TEXT)
        window.blit(lbl, (x0, 240))
        for i in range(settings.MAX_LIVES):
            color = settings.COLOR_HUD_ACCENT if i < lives else (60, 60, 60)
            # 50px horizontal stride per dot; radius 18 keeps them readable.
            pygame.draw.circle(window, color, (x0 + 20 + i * 50, 290), 18)

        # POWERUPS section: list active effects with remaining time, or "(none)"
        # in dim gray when nothing is active.
        pu_y = 360
        pu_label = self.font_small.render("POWERUPS", True, settings.COLOR_HUD_TEXT)
        window.blit(pu_label, (x0, pu_y))
        pu_y += 30
        if active_powerups:
            for name, remaining in active_powerups:
                # Two leading spaces visually indent under the POWERUPS header.
                txt = self.font_small.render(
                    f"  {name}  {remaining:.1f}s", True, settings.COLOR_HUD_ACCENT,
                )
                window.blit(txt, (x0, pu_y))
                pu_y += 28
        else:
            txt = self.font_small.render("  (none)", True, (120, 120, 120))
            window.blit(txt, (x0, pu_y))

        # CONTROLS reference is anchored near the bottom of the column so it
        # acts as a stable reminder regardless of the powerup list height.
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
        """Render the right HUD column (vertical altitude scale, tuna, restart).

        The scale is a vertical line with tick marks at notable altitudes; a
        triangular YOU pointer slides up the scale as the player climbs.

        Args:
            window: Display surface to draw onto.
            altitude_m: Player's current altitude (positions the YOU marker).
            tuna: Tuna pickup count to display.
            next_hazard_label: Name of the next hazard tier.
            next_hazard_m: Altitude where the next hazard unlocks; negative
                means everything is already unlocked.
        """
        x0 = settings.RIGHT_HUD_X + 40
        # Pixel range mapping for the scale: scale_top_y..scale_bot_y on screen
        # corresponds to scale_top_m..0 meters in altitude. scale_top_m caps
        # the marker so it doesn't fly off-screen at extreme altitudes.
        scale_top_y = 100
        scale_bot_y = 800
        scale_top_m = 600
        # Vertical spine of the altitude scale.
        pygame.draw.line(
            window, settings.COLOR_HUD_TEXT,
            (x0 + 60, scale_top_y), (x0 + 60, scale_bot_y), 2,
        )
        # Tick marks at key altitudes. Y inverted: more meters -> higher on
        # screen (smaller y), matching real-world climbing intuition.
        for mark_m in (50, 150, 300, 500):
            ratio = mark_m / scale_top_m
            y = int(scale_bot_y - (scale_bot_y - scale_top_y) * ratio)
            pygame.draw.line(window, settings.COLOR_HUD_TEXT, (x0 + 50, y), (x0 + 70, y), 2)
            txt = self.font_small.render(f"{mark_m}m", True, settings.COLOR_HUD_TEXT)
            window.blit(txt, (x0 + 80, y - 12))
        # YOU triangle marker. Clamp to 1.0 so once the player exceeds
        # scale_top_m the arrow pins at the top of the scale rather than
        # disappearing off the column.
        you_ratio = min(1.0, altitude_m / scale_top_m)
        you_y = int(scale_bot_y - (scale_bot_y - scale_top_y) * you_ratio)
        pygame.draw.polygon(
            window, settings.COLOR_HUD_ACCENT,
            [(x0 + 30, you_y - 8), (x0 + 30, you_y + 8), (x0 + 50, you_y)],
        )
        you = self.font_small.render(f"YOU {altitude_m}m", True, settings.COLOR_HUD_ACCENT)
        window.blit(you, (x0 - 20, you_y + 14))

        # NEXT hazard preview helps players anticipate difficulty spikes; once
        # all hazards are unlocked we show a static "all unlocked" string
        # rather than a meaningless target altitude.
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
        # Persistent restart-key hint: useful both during play and on game over.
        hint = self.font_small.render("R: Restart", True, settings.COLOR_HUD_TEXT)
        window.blit(hint, (x0, 970))
