"""Main game scene - climb the cat tower.

The middle stage of the scene flow:

    menu  ->  game  ->  gameover  ->  menu

This is the gameplay scene. It owns the player, the camera, the procedurally
generated world (a list of vertical "chunks"), all live hazards and items, and
the side HUD-feeding state (lives, tuna, active powerups).

Per-frame structure (driven by the outer scene manager):

  1. ``begin_frame()``  - reset transient input edges (just-pressed flags).
  2. ``handle_event()`` - feed each pygame event into the input recorder.
  3. ``update(dt)``     - advance physics, world streaming, hazards, items,
                          camera following, and death checks. NO drawing.
  4. ``draw(window)``   - render gameplay onto an internal surface and blit it
                          (scaled) into the gameplay viewport. NO state edits.

The scene marks itself ``dead`` when the player dies; the scene manager polls
that flag and transitions to :class:`GameOverScene`. Pause is handled outside
this scene by the scene manager (which simply stops calling ``update``); the
scene needs no internal pause flag because it is fully driven by ``update``.
"""
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
    """Pick a sky background color based on the player's altitude.

    The four bands give the run a sense of progression: day at the bottom,
    sunset, night, then deep space at extreme altitude. Star sprinkling in
    the draw step is gated on the same 500m threshold used here.

    Args:
        altitude_m: Current player altitude in meters.

    Returns:
        An RGB tuple suitable for ``Surface.fill``.
    """
    if altitude_m < 150:
        return (60, 130, 200)    # day
    if altitude_m < 350:
        return (210, 110, 60)    # sunset
    if altitude_m < 500:
        return (50, 30, 80)      # night
    return (8, 8, 20)            # space


class GameScene:
    """The gameplay scene: player, world streaming, hazards, items, camera.

    World generation is chunk-based: the world is a vertical stack of
    :class:`Chunk` objects, each holding the platforms / hazard requests /
    item requests for a slice of altitude. A new chunk is appended whenever
    the player passes the midpoint of the current top chunk (spawn-ahead),
    and chunks fully below the camera are dropped (despawn-behind), keeping
    the live entity set bounded regardless of how high the player climbs.

    The score for a run is the maximum altitude reached, surfaced via the
    player's ``altitude_m`` (the player records its own peak, so the HUD can
    read it directly each frame).

    Attributes:
        rng: Deterministic RNG used for both world generation and ambient
            visual effects (e.g. star sprinkling) when a seed is supplied.
        player: The player entity.
        camera: Vertical-only camera; follows the player upward as they climb.
        dead: Set to True when the player is killed (lethal hazard, lost all
            lives, or fell below the screen). Polled by the scene manager.
        hazards: Live hazard entities (vacuum, etc.). Lists are filtered each
            frame to drop ``dead`` entries.
        items: Live pickup items (tuna, powerups, ...).
        tuna_count: Running total of tuna collected this run; surfaced to HUD.
        chunks: Vertical stack of world chunks, ascending in altitude.
        input: Edge-tracking input recorder (held vs just-pressed).
    """

    def __init__(self, *, seed: int | None = None) -> None:
        """Build a fresh run.

        Args:
            seed: Optional RNG seed for deterministic world layouts; pass None
                for a non-deterministic run.
        """
        self.rng = random.Random(seed)

        self.player = Player(
            start_x=settings.INTERNAL_WIDTH / 2 - settings.PLAYER_WIDTH / 2,
            start_y=20.0,
        )
        # Player starts standing on the floor, not falling, so the first frame
        # does not register a phantom landing or play a stray "land" sfx.
        self.player.grounded = True
        self.camera = Camera(
            screen_height=settings.INTERNAL_HEIGHT,
            player_offset_from_top=settings.PLAYER_SCREEN_OFFSET_FROM_TOP,
        )
        self.dead = False

        # IMPORTANT: hazard/item lists must exist BEFORE _spawn_next_chunk()
        # below, because the spawn helper appends to them at chunk-creation time.
        self.hazards: list = []
        self.items: list = []
        self.tuna_count: int = 0
        # Vacuum is a one-shot screen-wide hazard; we track that we've spawned
        # it so we never duplicate it across multiple chunk-generation requests.
        self._vacuum_spawned: bool = False

        # Ground chunk: a thin sentinel chunk holding only the floor platform.
        # Sized to just the floor's height so the next generated chunk starts
        # immediately above (y=20) and the cat tower fills the visible area.
        ground = StandardPlatform(x=0.0, y=0.0, w=settings.INTERNAL_WIDTH, h=20.0)
        self.chunks: list[Chunk] = [
            Chunk(y_start=0, y_end=20, platforms=[ground]),
        ]
        # Pre-spawn two chunks so the player always has visible platforms ahead.
        # One chunk would be enough for collision but two avoids a visible gap
        # at the top of the viewport on the very first frame.
        self._spawn_next_chunk()
        self._spawn_next_chunk()

        self.input = InputState()
        # Internal low-resolution surface; gameplay is rendered here at logical
        # size, then scaled up to the game viewport on draw. This keeps physics
        # and pixel art crisp regardless of the actual window resolution.
        self._internal = pygame.Surface((settings.INTERNAL_WIDTH, settings.INTERNAL_HEIGHT))

    # ------------------------------------------------------- chunk helpers

    def _spawn_next_chunk(self) -> None:
        """Generate the next chunk above the current top chunk and bind its content.

        Chooses difficulty from the chunk's altitude band, anchors the new
        chunk's first platform to the previous chunk's highest platform (so
        the climb chain never has an unreachable gap at chunk boundaries),
        and immediately materializes any hazard / item spawn requests the
        generator returned. Resolving spawns at chunk-creation time keeps the
        spawn pipeline stateless and avoids duplicates if a chunk is later
        re-encountered.

        Why anchor to the *highest* platform in the previous chunk rather than
        just the chunk top: the generator places platforms throughout each
        chunk's height range, so the literal y_end is just a coordinate -- the
        last reachable platform may be slightly below it. Anchoring on the
        actual platform guarantees vertical AND horizontal reachability.
        """
        top = self.chunks[-1]
        # Difficulty is altitude-driven (in meters), not chunk-index-driven,
        # so chunk sizing changes don't shift the difficulty curve.
        diff = difficulty_for_altitude(top.y_end // settings.PIXELS_PER_METER)
        # Use the highest platform in the previous chunk as the reachability
        # anchor for the new chunk's first platform - both vertically AND
        # horizontally - so there's no broken-chain gap at chunk boundaries.
        if top.platforms:
            top_plat = max(top.platforms, key=lambda p: p.y)
            prev_top_y = top_plat.y
            prev_top_x = top_plat.x
        else:
            prev_top_y = None
            prev_top_x = None
        new_chunk = generate_chunk(
            y_start=top.y_end,
            difficulty=diff,
            rng=self.rng,
            prev_top_y=prev_top_y,
            prev_top_x=prev_top_x,
        )
        self.chunks.append(new_chunk)
        # Spawn hazards/items immediately when the chunk is created so we never
        # double-process and never lose spawns to garbage-collected chunk ids.
        for kind, world_y in new_chunk.hazard_requests:
            if kind == "vacuum":
                # Vacuum is a unique global hazard - spawn it at most once,
                # and offset it one screen above the camera so it descends
                # into view rather than appearing on top of the player.
                if self._vacuum_spawned:
                    continue
                spawn_y = self.camera.y_top - settings.INTERNAL_HEIGHT
                self.hazards.append(make_hazard("vacuum", x=0, y=spawn_y))
                self._vacuum_spawned = True
            else:
                # Standard hazards get a random x across the playfield (-24
                # accounts for hazard width so they stay fully on-screen).
                x = self.rng.uniform(0, settings.INTERNAL_WIDTH - 24)
                self.hazards.append(make_hazard(kind, x=x, y=world_y))
        for ikind, ix, iy in new_chunk.item_requests:
            self.items.append(make_item(ikind, x=ix, y=iy))

    # ------------------------------------------------------- scene API

    def begin_frame(self) -> None:
        """Per-frame setup hook; rolls input edge state for the new frame.

        Called by the scene manager before any ``handle_event`` calls. The
        :class:`InputState` uses this to age "just pressed" edges out, so the
        player can detect single key presses cleanly.
        """
        self.input.begin_frame()

    def handle_event(self, event: pygame.event.Event) -> None:
        """Forward a pygame event to the input recorder.

        Args:
            event: A pygame event from the main event queue.
        """
        self.input.handle_event(event)

    def update(self, dt: float) -> None:
        """Advance simulation by one fixed frame.

        Order matters: input -> player physics -> landing resolution against
        all platforms -> SFX edges -> camera follow -> chunk streaming
        (spawn-ahead / despawn-behind) -> hazard tick & collision ->
        item tick & pickup -> off-screen death check. Drawing is deliberately
        kept in :meth:`draw` so the scene manager can pause or repaint without
        re-running simulation.

        Args:
            dt: Frame delta time in seconds.
        """
        self.player.set_input(
            left_held=self.input.is_held(settings.KEY_LEFT),
            right_held=self.input.is_held(settings.KEY_RIGHT),
            jump_pressed=self.input.was_pressed(settings.KEY_JUMP),
            jump_held=self.input.is_held(settings.KEY_JUMP),
        )
        # Snapshot pre-integration state needed by landing resolution and the
        # "stayed put" SFX suppression below.
        prev_bottom = self.player.y
        was_grounded = self.player.grounded
        self.player.update(dt)

        # After integration: clear grounded so resolve_landings can re-engage.
        # If the player jumped this frame, update() already set grounded=False;
        # otherwise we clear it here so walking off an edge transitions to airborne.
        self.player.grounded = False

        # Collect platforms from all live chunks for one unified collision pass.
        # Done each frame because the chunk list mutates via streaming.
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

        # SFX are edge-triggered, played from booleans the player flipped this
        # frame, so transient sounds fire exactly once per event.
        if self.player.just_jumped:
            audio.play("jump")
        if self.player.just_landed:
            audio.play("land")

        # Camera follows the player vertically (horizontal is fixed). This keeps
        # the player anchored near the top of the viewport so what's ahead
        # (above) is always visible during the climb.
        self.camera.follow(self.player.y)

        # Spawn-ahead: if player is past midpoint of current top chunk, spawn
        # next. Halfway is the latest safe trigger point - past that, the next
        # chunk's platforms could become visible at the top of the viewport
        # before they exist.
        top = self.chunks[-1]
        midpoint = (top.y_start + top.y_end) / 2
        if self.player.y > midpoint:
            self._spawn_next_chunk()

        # Despawn-behind: drop chunks fully below the screen so memory and
        # collision cost stay bounded across long runs.
        self.chunks = [
            ch for ch in self.chunks if not self.camera.is_below_screen(ch.y_end)
        ]

        # Hazard updates + collision. Two-pass (update then filter then collide)
        # so a hazard that decides to die this frame doesn't both kill itself
        # and damage the player on the same tick.
        for h in self.hazards:
            h.update(dt, self.camera)
        self.hazards = [h for h in self.hazards if not h.dead]
        for h in self.hazards:
            if aabb_overlap(self.player.rect, h.rect):
                if h.lethal:
                    # Lethal hazards skip the lives system entirely - the run
                    # ends regardless of remaining lives.
                    audio.play("gameover")
                    self.dead = True
                else:
                    # Only play the hit sfx if the player is actually
                    # vulnerable; otherwise the hit is silently absorbed by
                    # invincibility frames or a Catnip powerup.
                    if self.player.iframe_timer <= 0 and self.player.invincible_timer <= 0:
                        audio.play("hit")
                    # take_hit() consumes a life and grants i-frames; the player
                    # respawns in place (no positional reset) which is the
                    # life-loss / respawn flow for non-lethal damage.
                    self.player.take_hit()
                    if not self.player.is_alive:
                        audio.play("gameover")
                        self.dead = True

        # Items: update, drop dead, then pickup-collide. ``apply`` returns the
        # tuna delta so generic items (powerups, tuna) share one code path.
        for it in self.items:
            it.update(dt, self.camera)
        self.items = [it for it in self.items if not it.dead]
        for it in list(self.items):
            if aabb_overlap(self.player.rect, it.rect):
                self.tuna_count += it.apply(self.player)
                it.dead = True
                audio.play("pickup")
        self.items = [it for it in self.items if not it.dead]

        # Death by fall: if the player's lower edge sinks below the visible
        # screen, end the run. Checked last so any hazard / pickup interactions
        # this frame have already resolved.
        if self.camera.is_below_screen(self.player.y + settings.PLAYER_HEIGHT):
            self.dead = True

    def draw(self, window: pygame.Surface) -> None:
        """Render the gameplay viewport.

        Renders sky, optional star field, platforms, items, hazards and the
        player at the logical ``_internal`` resolution, then scales the result
        once into the viewport on ``window``. No simulation state is mutated
        here - keeping update / draw separated lets the scene manager redraw
        a paused or game-over frame without altering the world.

        Args:
            window: Main display surface; gameplay is blitted to the viewport.
        """
        # Sky color is altitude-banded; fill the internal surface fresh each
        # frame so we don't have to carry over previous-frame artifacts.
        sky = _sky_color(self.player.altitude_m)
        self._internal.fill(sky)
        if self.player.altitude_m >= 500:
            # In the "space" band, sprinkle a star field. The RNG is seeded by
            # the camera position quantized to 50px buckets so stars stay
            # roughly stable as the camera moves (small twinkle as you climb)
            # without needing a persistent star list.
            star_rng = random.Random(int(self.camera.y_top) // 50)
            for _ in range(40):
                sx = star_rng.randint(0, settings.INTERNAL_WIDTH - 1)
                sy = star_rng.randint(0, settings.INTERNAL_HEIGHT - 1)
                self._internal.set_at((sx, sy), (240, 240, 240))

        # Draw order: world -> items -> hazards -> player. Player on top so
        # they're never visually occluded by overlapping pickups or hazards.
        for ch in self.chunks:
            for plat in ch.platforms:
                plat.draw(self._internal, self.camera)
        for it in self.items:
            it.draw(self._internal, self.camera)
        for h in self.hazards:
            h.draw(self._internal, self.camera)
        draw_player(self._internal, self.player, self.camera)

        # Single scale-and-blit to the viewport rectangle. Doing the scale once
        # here (rather than rendering at full resolution) is what keeps the
        # logical pixel size crisp regardless of the actual window size.
        scaled = pygame.transform.scale(
            self._internal, (settings.GAME_AREA_WIDTH, settings.GAME_AREA_HEIGHT),
        )
        window.blit(scaled, (settings.GAME_AREA_X, settings.GAME_AREA_Y))

    def active_powerups(self) -> list[tuple[str, float]]:
        """Return the currently active powerups for HUD display.

        Each entry is ``(label, seconds_remaining)``. Order is fixed so the HUD
        rows don't reorder mid-run.

        Returns:
            A list of ``(name, remaining_time)`` tuples; empty if none active.
        """
        out: list[tuple[str, float]] = []
        if self.player.invincible_timer > 0:
            out.append(("Catnip", self.player.invincible_timer))
        if self.player.jump_boost_timer > 0:
            out.append(("Feather", self.player.jump_boost_timer))
        return out
