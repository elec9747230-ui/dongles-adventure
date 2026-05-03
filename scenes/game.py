"""Main game scene - climb the cat tower."""
from __future__ import annotations

import random

import pygame

import settings
from engine import audio
from engine.camera import Camera
from engine.input import InputState
from engine.physics import aabb_overlap
from entities.hazards import make_hazard
from entities.items import make_item
from entities.platforms import StandardPlatform, resolve_landings
from entities.player import Player
from entities.player_render import draw_player
from world.difficulty import difficulty_for_altitude
from world.generator import Chunk, generate_chunk


def _sky_color(altitude_m: int) -> tuple[int, int, int]:
    if altitude_m < 150:
        return (60, 130, 200)    # day
    if altitude_m < 350:
        return (210, 110, 60)    # sunset
    if altitude_m < 500:
        return (50, 30, 80)      # night
    return (8, 8, 20)            # space


class GameScene:
    def __init__(self, *, seed: int | None = None) -> None:
        self.rng = random.Random(seed)

        self.player = Player(
            start_x=settings.INTERNAL_WIDTH / 2 - settings.PLAYER_WIDTH / 2,
            start_y=20.0,
        )
        self.player.grounded = True
        self.camera = Camera(
            screen_height=settings.INTERNAL_HEIGHT,
            player_offset_from_top=settings.PLAYER_SCREEN_OFFSET_FROM_TOP,
        )
        self.dead = False

        # Ground chunk: a thin sentinel chunk holding only the floor platform.
        # Sized to just the floor's height so the next generated chunk starts
        # immediately above (y=20) and the cat tower fills the visible area.
        ground = StandardPlatform(x=0.0, y=0.0, w=settings.INTERNAL_WIDTH, h=20.0)
        self.chunks: list[Chunk] = [
            Chunk(y_start=0, y_end=20, platforms=[ground]),
        ]
        # Pre-spawn two chunks so the player always has visible platforms ahead.
        self._spawn_next_chunk()
        self._spawn_next_chunk()

        self.hazards: list = []
        self.items: list = []
        self.tuna_count: int = 0
        self._processed_chunk_ids: set[int] = set()
        self._vacuum_spawned: bool = False

        self.input = InputState()
        self._internal = pygame.Surface((settings.INTERNAL_WIDTH, settings.INTERNAL_HEIGHT))

    # ------------------------------------------------------- chunk helpers

    def _spawn_next_chunk(self) -> None:
        top = self.chunks[-1]
        diff = difficulty_for_altitude(top.y_end // settings.PIXELS_PER_METER)
        prev_top_y = max((p.y for p in top.platforms), default=None)
        new_chunk = generate_chunk(
            y_start=top.y_end, difficulty=diff, rng=self.rng, prev_top_y=prev_top_y,
        )
        self.chunks.append(new_chunk)

    def _process_pending_spawns(self) -> None:
        for ch in self.chunks:
            key = id(ch)
            if key in self._processed_chunk_ids:
                continue
            for kind, world_y in ch.hazard_requests:
                if kind == "vacuum":
                    if self._vacuum_spawned:
                        continue
                    spawn_y = self.camera.y_top - settings.INTERNAL_HEIGHT
                    self.hazards.append(make_hazard("vacuum", x=0, y=spawn_y))
                    self._vacuum_spawned = True
                else:
                    x = self.rng.uniform(0, settings.INTERNAL_WIDTH - 14)
                    self.hazards.append(make_hazard(kind, x=x, y=world_y))
            for ikind, ix, iy in ch.item_requests:
                self.items.append(make_item(ikind, x=ix, y=iy))
            self._processed_chunk_ids.add(key)

    # ------------------------------------------------------- scene API

    def begin_frame(self) -> None:
        self.input.begin_frame()

    def handle_event(self, event: pygame.event.Event) -> None:
        self.input.handle_event(event)

    def update(self, dt: float) -> None:
        self.player.set_input(
            left_held=self.input.is_held(settings.KEY_LEFT),
            right_held=self.input.is_held(settings.KEY_RIGHT),
            jump_pressed=self.input.was_pressed(settings.KEY_JUMP),
            jump_held=self.input.is_held(settings.KEY_JUMP),
        )
        prev_bottom = self.player.y
        was_grounded = self.player.grounded
        self.player.update(dt)

        # After integration: clear grounded so resolve_landings can re-engage.
        # If the player jumped this frame, update() already set grounded=False;
        # otherwise we clear it here so walking off an edge transitions to airborne.
        self.player.grounded = False

        # Collect platforms from all live chunks
        all_plats: list = []
        for ch in self.chunks:
            all_plats.extend(ch.platforms)
        resolve_landings(self.player, all_plats, prev_bottom_y=prev_bottom)
        # Suppress "just_landed" SFX when the player merely stays put on the same
        # platform (they were grounded last frame and still are this frame).
        if was_grounded and self.player.grounded and self.player.vy == 0:
            self.player.just_landed = False
        for plat in all_plats:
            plat.update(dt)

        if self.player.just_jumped:
            audio.play("jump")
        if self.player.just_landed:
            audio.play("land")

        self.camera.follow(self.player.y)

        # Spawn-ahead: if player is past midpoint of current top chunk, spawn next
        top = self.chunks[-1]
        midpoint = (top.y_start + top.y_end) / 2
        if self.player.y > midpoint:
            self._spawn_next_chunk()

        # Despawn-behind: drop chunks fully below the screen
        self.chunks = [
            ch for ch in self.chunks if not self.camera.is_below_screen(ch.y_end)
        ]

        self._process_pending_spawns()

        # Hazard updates + collision
        for h in self.hazards:
            h.update(dt, self.camera)
        self.hazards = [h for h in self.hazards if not h.dead]
        for h in self.hazards:
            if aabb_overlap(self.player.rect, h.rect):
                if h.lethal:
                    audio.play("gameover")
                    self.dead = True
                else:
                    if self.player.iframe_timer <= 0 and self.player.invincible_timer <= 0:
                        audio.play("hit")
                    self.player.take_hit()
                    if not self.player.is_alive:
                        audio.play("gameover")
                        self.dead = True

        # Items: update + pickup
        for it in self.items:
            it.update(dt, self.camera)
        self.items = [it for it in self.items if not it.dead]
        for it in list(self.items):
            if aabb_overlap(self.player.rect, it.rect):
                self.tuna_count += it.apply(self.player)
                it.dead = True
                audio.play("pickup")
        self.items = [it for it in self.items if not it.dead]

        # Death by fall
        if self.camera.is_below_screen(self.player.y + settings.PLAYER_HEIGHT):
            self.dead = True

    def draw(self, window: pygame.Surface) -> None:
        sky = _sky_color(self.player.altitude_m)
        self._internal.fill(sky)
        if self.player.altitude_m >= 500:
            star_rng = random.Random(int(self.camera.y_top) // 50)
            for _ in range(40):
                sx = star_rng.randint(0, settings.INTERNAL_WIDTH - 1)
                sy = star_rng.randint(0, settings.INTERNAL_HEIGHT - 1)
                self._internal.set_at((sx, sy), (240, 240, 240))

        for ch in self.chunks:
            for plat in ch.platforms:
                plat.draw(self._internal, self.camera)
        for it in self.items:
            it.draw(self._internal, self.camera)
        for h in self.hazards:
            h.draw(self._internal, self.camera)
        draw_player(self._internal, self.player, self.camera)

        scaled = pygame.transform.scale(
            self._internal, (settings.GAME_AREA_WIDTH, settings.GAME_AREA_HEIGHT),
        )
        window.blit(scaled, (settings.GAME_AREA_X, settings.GAME_AREA_Y))

    def active_powerups(self) -> list[tuple[str, float]]:
        out: list[tuple[str, float]] = []
        if self.player.invincible_timer > 0:
            out.append(("Catnip", self.player.invincible_timer))
        if self.player.jump_boost_timer > 0:
            out.append(("Feather", self.player.jump_boost_timer))
        return out
