"""
Isometric 2:1 Environment & Lighting Engine (art_engine_25d.py) — IsoEngine + Dunwick Merge
Tailored for CHRONICLES OF DUNWICK: DEFYING FATE (1924):
1. Merges IsoEngine's 2:1 Mathematical Isometric Grid (`modules/grid.py`) and 108 Isometric Sprites
   (`modules/sprites.py` -> `assets/iso_sprites/`) with all 6 Dunwick Overworld Landmark Estates and
   all 6 Dedicated Cutaway Isometric Interior Room Scenes (`home`, `cafe`, `office`, `school`, `market`, `park`).
2. Provides exact 2:1 isometric forward and inverse projection (`world_to_iso`, `iso_to_world`,
   `world_to_screen`, `screen_to_world`, `get_iso_tile_diamond`) mapping Dunwick's 81x56 logical tile matrix
   onto a 2:1 isometric diamond world (`TILE_WIDTH = 64`, `TILE_HEIGHT = 32`).
3. Retains the full Octopath Traveler HD-2D Dynamic Point-Lighting, Volumetric God-Rays, Coal-Ash Motes,
   and Tilt-Shift Vignette pipeline in isometric screen space.
"""

from __future__ import annotations

import math
import os
import random
import pygame
from config import BUILDINGS, COLORS, SCREEN_HEIGHT, SCREEN_WIDTH, WORLD_HEIGHT, WORLD_WIDTH
from modules.grid import IsometricGrid
from modules.sprites import IsometricSpriteLibrary


TILE_SIZE = 32
GRID_W = WORLD_WIDTH // TILE_SIZE   # 81 tiles
GRID_H = WORLD_HEIGHT // TILE_SIZE  # 56 tiles

ISO_TILE_W = 64
ISO_TILE_H = 32
ISO_ORIGIN_X = 1856
ISO_ORIGIN_Y = 96
ISO_CANVAS_W = 4560
ISO_CANVAS_H = 2400

INTERIOR_PAD = 90


def _load_image_rgba(path: str) -> pygame.Surface:
    """Python 3.14-safe RGBA PNG loader with PIL fallback."""
    try:
        return pygame.image.load(path).convert_alpha()
    except Exception:
        from PIL import Image
        pil_img = Image.open(path).convert("RGBA")
        return pygame.image.frombytes(pil_img.tobytes(), pil_img.size, "RGBA")


def _clamp_rgb(r: float, g: float, b: float) -> tuple[int, int, int]:
    return (
        max(0, min(255, int(r))),
        max(0, min(255, int(g))),
        max(0, min(255, int(b))),
    )


def _shade(color: tuple[int, int, int], factor: float) -> tuple[int, int, int]:
    return _clamp_rgb(color[0] * factor, color[1] * factor, color[2] * factor)


class ArtEngine25D:
    """
    Isometric 2:1 Environment & Post-Processing Engine combining IsoEngine's IsometricGrid
    and IsometricSpriteLibrary with Dunwick's Overworld and 6 Interior Room Scenes.
    """

    def __init__(self, assets_dir: str):
        self.assets_dir = assets_dir
        self.hd2d_dir = os.path.join(assets_dir, "hd2d_sprites")
        self.portraits_cache: dict[str, pygame.Surface] = {}
        self.sprites: dict[str, pygame.Surface] = {}
        self.house_sprites: dict[str, pygame.Surface] = {}

        # Initialize IsoEngine Sprite Library & 81x56 IsometricGrid
        self.iso_lib = IsometricSpriteLibrary()
        self.iso_grid = IsometricGrid(
            cols=GRID_W,
            rows=GRID_H,
            tile_width=ISO_TILE_W,
            tile_height=ISO_TILE_H,
            sprite_lib=self.iso_lib,
        )

        self._load_hd2d_sprite_library()

        # Tree, Barrel, Crate & Gaslamp isometric sprites from IsoEngine library
        self.tree_sprite = (
            self.iso_lib.get_surface("iso_tree_hd2d")
            or self.get_sprite("tree_hd2d", (118, 136))
            or self._bake_fallback_tree()
        )
        self.barrel_sprite = self.iso_lib.get_surface("iso_barrel_single") or self.iso_lib.get_surface("iso_barrels")
        self.barrels_stack_sprite = self.iso_lib.get_surface("iso_barrels_stacked")
        self.crate_sprite = self.iso_lib.get_surface("iso_crates_group") or self.iso_lib.get_surface("iso_crates")
        self.patio_table_sprite = self.iso_lib.get_surface("iso_table_round_items") or self.iso_lib.get_surface("iso_table_round")
        self.gaslamp_sprite = self.iso_lib.get_surface("iso_street_gaslamp")

        # 1. Pre-bake the 2:1 Isometric Overworld Ground Canvas (4560 x 2400)
        self.world_ground_surface = pygame.Surface((ISO_CANVAS_W, ISO_CANVAS_H))
        self._bake_overworld_ground()

        # 2. Pre-bake the 6 Dedicated 2:1 Isometric Cutaway Interior Room Surfaces
        self.interior_room_surfaces: dict[str, pygame.Surface] = {}
        self.interior_room_offsets: dict[str, tuple[int, int]] = {}
        self._bake_all_interior_rooms()

        # Ambient 1920s British Steampunk outdoor street props in logical world coordinates
        self.street_props = [
            ("lamp", 385, 765),
            ("lamp", 515, 765),
            ("lamp", 755, 765),
            ("lamp", 1225, 765),
            ("lamp", 1355, 765),
            ("lamp", 1585, 765),
            ("lamp", 2075, 765),
            ("lamp", 2205, 765),
            ("lamp", 2425, 765),
            ("lamp", 385, 1005),
            ("lamp", 515, 1005),
            ("lamp", 1225, 1005),
            ("lamp", 1355, 1005),
            ("lamp", 2075, 1005),
            ("lamp", 2205, 1005),
            ("barrel", 985, 750),
            ("barrel", 1022, 755),
            ("crate", 1585, 750),
            ("barrel", 985, 1030),
            ("crate", 1025, 1035),
            ("flower_cart", 1395, 762),
            ("flower_cart", 1565, 1035),
            ("barrel", 1825, 750),
            ("crate", 2445, 750),
            ("flower_cart", 725, 755),
        ]

        # Pre-bake HD-2D Light Radial Brush, Tilt-Shift Vignette Overlay, and Atmospheric Dust Motes
        self._light_radial_warm = self._bake_radial_light(256, (255, 206, 118))
        self._light_radial_cyan = self._bake_radial_light(256, (95, 232, 255))
        self._light_radial_crimson = self._bake_radial_light(192, (255, 92, 82))
        self._vignette_overlay = self._bake_octopath_tilt_shift_vignette(SCREEN_WIDTH, SCREEN_HEIGHT)
        self._light_map_lowres = pygame.Surface((SCREEN_WIDTH // 4, SCREEN_HEIGHT // 4))

        rng = random.Random(1924)
        self._ash_motes = [
            {
                "x": rng.uniform(0, SCREEN_WIDTH),
                "y": rng.uniform(0, SCREEN_HEIGHT),
                "vx": rng.uniform(8.0, 22.0),
                "vy": rng.uniform(-12.0, 6.0),
                "sz": rng.choice([1, 2, 2, 3]),
                "phase": rng.uniform(0, math.tau),
                "ember": rng.random() < 0.28,
            }
            for _ in range(65)
        ]

    # =========================================================================
    # ISOENGINE 2:1 MATHEMATICAL PROJECTION HELPERS
    # =========================================================================
    def world_to_iso(self, wx: float, wy: float, elev: float = 0.0) -> tuple[float, float]:
        """Convert Dunwick logical world (wx, wy) to 2:1 isometric canvas coordinates."""
        iso_x = ISO_ORIGIN_X + (wx - wy)
        iso_y = ISO_ORIGIN_Y + 0.5 * (wx + wy) - (elev * 16.0)
        return iso_x, iso_y

    def iso_to_world(self, iso_x: float, iso_y: float, elev: float = 0.0) -> tuple[float, float]:
        """Exact inverse 2:1 isometric projection from canvas coordinates to logical (wx, wy)."""
        dx = iso_x - ISO_ORIGIN_X
        dy = (iso_y + elev * 16.0) - ISO_ORIGIN_Y
        wx = dy + 0.5 * dx
        wy = dy - 0.5 * dx
        return wx, wy

    def world_to_screen(self, wx: float, wy: float, cam_x: float, cam_y: float, elev: float = 0.0) -> tuple[int, int]:
        """Project logical world coordinate (wx, wy) to screen pixel (sx, sy)."""
        iso_x, iso_y = self.world_to_iso(wx, wy, elev)
        return int(round(iso_x - cam_x)), int(round(iso_y - cam_y))

    def screen_to_world(self, sx: float, sy: float, cam_x: float, cam_y: float, elev: float = 0.0) -> tuple[float, float]:
        """Inverse project screen pixel (sx, sy) back to Dunwick logical (wx, wy)."""
        return self.iso_to_world(sx + cam_x, sy + cam_y, elev)

    def screen_to_grid_cell(self, sx: float, sy: float, cam_x: float, cam_y: float) -> tuple[int, int]:
        """Return integer isometric grid cell (gx, gy) under screen pixel (sx, sy)."""
        wx, wy = self.screen_to_world(sx, sy, cam_x, cam_y)
        return int(wx // TILE_SIZE), int(wy // TILE_SIZE)

    def get_iso_tile_diamond(self, gx: int, gy: int, cam_x: float, cam_y: float, elev: float = 0.0) -> list[tuple[int, int]]:
        """Return the 4 screen-space vertices [top, right, bottom, left] of isometric cell (gx, gy)."""
        wx = gx * TILE_SIZE + TILE_SIZE * 0.5
        wy = gy * TILE_SIZE + TILE_SIZE * 0.5
        sx, sy = self.world_to_screen(wx, wy, cam_x, cam_y, elev)
        hw = ISO_TILE_W // 2
        hh = ISO_TILE_H // 2
        return [
            (sx, sy - hh),
            (sx + hw, sy),
            (sx, sy + hh),
            (sx - hw, sy),
        ]

    # =========================================================================
    # SPRITE LOADING & CACHING
    # =========================================================================
    def _load_hd2d_sprite_library(self):
        # 1. Load all 108 true 2:1 isometric sprites from IsoEngine's IsometricSpriteLibrary
        for spr_id in self.iso_lib.manifest:
            surf = self.iso_lib.get_surface(spr_id)
            if surf is not None:
                self.sprites[spr_id] = surf
                if spr_id.startswith("iso_"):
                    short_key = spr_id[4:]
                    self.sprites[short_key] = surf

        for bid in ("home", "cafe", "office", "school", "market", "park"):
            iso_house = self.iso_lib.get_surface(f"iso_house_{bid}")
            if iso_house is not None:
                # Scale the 2:1 isometric landmark house so it spans the estate majestically
                self.house_sprites[bid] = pygame.transform.smoothscale(iso_house, (380, 326))

        # 2. Also load fallback hd2d_sprites if any key isn't in iso_sprites
        for sub in ("props", "tiles", "vehicles"):
            folder = os.path.join(self.hd2d_dir, sub)
            if not os.path.exists(folder):
                continue
            for fn in os.listdir(folder):
                if fn.endswith(".png"):
                    key = fn[:-4]
                    if key not in self.sprites:
                        try:
                            self.sprites[key] = _load_image_rgba(os.path.join(folder, fn))
                        except Exception:
                            pass

    def get_sprite(self, key: str, size: tuple[int, int] | None = None) -> pygame.Surface | None:
        iso_key = key if key.startswith("iso_") else f"iso_{key}"
        base = self.iso_lib.get_surface(iso_key) or self.sprites.get(key)
        if base is None:
            return None
        if size is not None:
            ckey = f"{iso_key}_{size[0]}x{size[1]}"
            if ckey not in self.sprites:
                self.sprites[ckey] = pygame.transform.smoothscale(base, size)
            return self.sprites[ckey]
        return base

    def load_ai_portrait_if_available(self, char_id: str, size: tuple[int, int]) -> pygame.Surface | None:
        key = f"{char_id}_{size[0]}x{size[1]}"
        if key in self.portraits_cache:
            return self.portraits_cache[key]

        p_dir = os.path.join(self.assets_dir, "portraits")
        p_path = os.path.join(p_dir, f"{char_id}.png")
        if os.path.exists(p_path):
            try:
                img = _load_image_rgba(p_path)
                scaled = pygame.transform.smoothscale(img, size)
                self.portraits_cache[key] = scaled
                return scaled
            except Exception:
                return None
        return None

    # =========================================================================
    # 1. PRE-BAKING THE 81x56 2:1 ISOMETRIC OVERWORLD GROUND CANVAS
    # =========================================================================
    def _choose_overworld_tile_sprite(self, tx: int, ty: int) -> str:
        wx = tx * TILE_SIZE + TILE_SIZE // 2
        wy = ty * TILE_SIZE + TILE_SIZE // 2

        # Crosswalks across High Street
        if 805 <= wy <= 955 and (abs(wx - 450) <= 48 or abs(wx - 1290) <= 48 or abs(wx - 2140) <= 48):
            return "iso_crosswalk"

        # High Street recessed brass steam-tramway lanes
        if 830 <= wy <= 858 or 904 <= wy <= 932:
            return "iso_tram_rail_ne"

        # High Street & Cross-Street Cobblestone Carriageways
        if (
            805 <= wy <= 955
            or (825 <= wx <= 915 and not (755 <= wy <= 1005))
            or (1665 <= wx <= 1755 and not (755 <= wy <= 1005))
        ):
            return "iso_cobblestone"

        # Sandstone Flagstone Sidewalks & Plazas
        if 755 <= wy <= 1005 or 790 <= wx <= 950 or 1630 <= wx <= 1790:
            return "iso_sidewalk"

        # Check if inside one of the 6 Estate Courtyards
        for b in BUILDINGS:
            rx, ry, rw, rh = b["rect"]
            dx, dy = b["door_x"], b["door_y"]
            if abs(wx - dx) <= 42 and abs(wy - dy) <= 42:
                return "iso_door_threshold"
            if rx <= wx <= rx + rw and ry <= wy <= ry + rh:
                bid = b["id"]
                if bid == "park":
                    # Severn Commons Park: central fountain water basin + stone walkways + greensward
                    if math.hypot(wx - (rx + rw * 0.5), wy - (ry + rh * 0.52)) <= 84:
                        return "iso_water"
                    elif abs(wx - dx) <= 64 or abs(wy - (ry + rh * 0.52)) <= 44:
                        return "iso_stone_inset"
                    return "iso_moor_grass"
                elif bid in ("home", "cafe"):
                    return "iso_stone_inset"
                elif bid in ("office", "market"):
                    return "iso_stone_tile"
                elif bid == "school":
                    return "iso_stone_slab"

        # Subtle moorland path variations
        if (tx * 17 + ty * 31) % 19 == 0:
            return "iso_dirt_ground"
        return "iso_moor_grass"

    def _bake_overworld_ground(self):
        surf = self.world_ground_surface
        surf.fill((12, 15, 22))

        # Render all 81x56 isometric tiles in back-to-front painter's order (tx + ty, ty)
        for s in range(GRID_W + GRID_H - 1):
            for ty in range(max(0, s - GRID_W + 1), min(GRID_H, s + 1)):
                tx = s - ty
                spr_id = self._choose_overworld_tile_sprite(tx, ty)
                tile_obj = self.iso_grid.get_tile(tx, ty)
                if tile_obj is not None:
                    tile_obj.tile_sprite = spr_id

                wx = tx * TILE_SIZE + TILE_SIZE * 0.5
                wy = ty * TILE_SIZE + TILE_SIZE * 0.5
                iso_x, iso_y = self.world_to_iso(wx, wy)
                ix, iy = int(round(iso_x)), int(round(iso_y))

                spr = self.iso_lib.get_surface(spr_id)
                if spr is not None:
                    surf.blit(spr, (ix - spr.get_width() // 2, iy - ISO_TILE_H // 2))

                # Crisp, subtle IsoEngine 2:1 diamond grid wireframe over every tile
                diamond = [
                    (ix, iy - ISO_TILE_H // 2),
                    (ix + ISO_TILE_W // 2, iy),
                    (ix, iy + ISO_TILE_H // 2),
                    (ix - ISO_TILE_W // 2, iy),
                ]
                wire_col = (28, 44, 32) if spr_id == "iso_moor_grass" else (48, 44, 40)
                pygame.draw.polygon(surf, wire_col, diamond, 1)

        # Bake isometric estate boundary fencing, corner pillars & topiary hedges around each lot
        fence_sw = self.iso_lib.get_surface("iso_fence_iron_sw")
        fence_se = self.iso_lib.get_surface("iso_fence_iron_se")
        pillar = self.iso_lib.get_surface("iso_fence_pillar")
        hedge = self.iso_lib.get_surface("iso_topiary_hedge")

        for b in BUILDINGS:
            rx, ry, rw, rh = b["rect"]
            dx, dy = b["door_x"], b["door_y"]
            x0, y0 = max(0, rx // TILE_SIZE), max(0, ry // TILE_SIZE)
            x1, y1 = min(GRID_W - 1, (rx + rw) // TILE_SIZE), min(GRID_H - 1, (ry + rh) // TILE_SIZE)

            # Back & side perimeter fence segments in painter's order
            perim_cells = []
            for tx in range(x0, x1 + 1, 2):
                perim_cells.append((tx, y0, "sw"))
                perim_cells.append((tx, y1, "sw"))
            for ty in range(y0, y1 + 1, 2):
                perim_cells.append((x0, ty, "se"))
                perim_cells.append((x1, ty, "se"))
            perim_cells.sort(key=lambda item: item[0] + item[1])

            for tx, ty, orient in perim_cells:
                wx = tx * TILE_SIZE + 16
                wy = ty * TILE_SIZE + 16
                if math.hypot(wx - dx, wy - dy) < 88:
                    continue
                ix, iy = self.world_to_screen(wx, wy, 0.0, 0.0)
                if (tx in (x0, x1) and ty in (y0, y1)) and pillar is not None:
                    surf.blit(pillar, (ix - pillar.get_width() // 2, iy + 16 - pillar.get_height()))
                elif orient == "sw" and fence_sw is not None:
                    surf.blit(fence_sw, (ix - fence_sw.get_width() // 2, iy + 16 - fence_sw.get_height()))
                elif orient == "se" and fence_se is not None:
                    surf.blit(fence_se, (ix - fence_se.get_width() // 2, iy + 16 - fence_se.get_height()))

            # Corner topiary hedges
            if hedge is not None:
                for htx, hty in [(x0 + 1, y0 + 1), (x1 - 1, y0 + 1), (x0 + 1, y1 - 1), (x1 - 1, y1 - 1)]:
                    wx = htx * TILE_SIZE + 16
                    wy = hty * TILE_SIZE + 16
                    if math.hypot(wx - dx, wy - dy) >= 88:
                        ix, iy = self.world_to_screen(wx, wy, 0.0, 0.0)
                        surf.blit(hedge, (ix - hedge.get_width() // 2, iy + 16 - hedge.get_height()))

    # =========================================================================
    # 2. PRE-BAKING THE 6 ISOMETRIC CUTAWAY INTERIOR ROOM SCENES
    # =========================================================================
    def _bake_all_interior_rooms(self):
        for b in BUILDINGS:
            self._bake_single_interior_room(b)

    def _bake_single_interior_room(self, b: dict):
        """
        Pre-bakes a true 2:1 Isometric Cutaway Interior Room for building `b` using
        IsoEngine's isometric floor tiles, carpets, and 3D architectural walls.
        """
        rx, ry, rw, rh = b["rect"]
        bid = b["id"]
        dx, dy = b["door_x"], b["door_y"]

        x0 = max(0, (rx - 32) // TILE_SIZE)
        y0 = max(0, (ry - 32) // TILE_SIZE)
        x1 = min(GRID_W - 1, (rx + rw + 32) // TILE_SIZE)
        y1 = min(GRID_H - 1, (ry + rh + 32) // TILE_SIZE)

        # Compute bounding box in isometric canvas coordinates
        corners_iso = [
            self.world_to_iso(x0 * TILE_SIZE, y0 * TILE_SIZE),
            self.world_to_iso((x1 + 1) * TILE_SIZE, y0 * TILE_SIZE),
            self.world_to_iso(x0 * TILE_SIZE, (y1 + 1) * TILE_SIZE),
            self.world_to_iso((x1 + 1) * TILE_SIZE, (y1 + 1) * TILE_SIZE),
        ]
        min_ix = int(min(p[0] for p in corners_iso)) - 140
        max_ix = int(max(p[0] for p in corners_iso)) + 140
        min_iy = int(min(p[1] for p in corners_iso)) - 160
        max_iy = int(max(p[1] for p in corners_iso)) + 120

        surf_w = max(320, max_ix - min_ix)
        surf_h = max(240, max_iy - min_iy)
        surf = pygame.Surface((surf_w, surf_h), pygame.SRCALPHA)
        self.interior_room_offsets[bid] = (min_ix, min_iy)

        # Choose floor tile sprite for this interior
        if bid in ("home", "school"):
            base_floor_id = "iso_wood_planks"
        elif bid in ("office", "park"):
            base_floor_id = "iso_stone_inset"
        else:
            base_floor_id = "iso_stone_tile"

        # Pass 1: Isometric Floor Tiles & Thresholds in Painter's Order
        for s in range((x0 + y0), (x1 + y1) + 1):
            for ty in range(y0, y1 + 1):
                tx = s - ty
                if not (x0 <= tx <= x1):
                    continue
                wx = tx * TILE_SIZE + 16
                wy = ty * TILE_SIZE + 16
                iso_x, iso_y = self.world_to_iso(wx, wy)
                lx = int(round(iso_x - min_ix))
                ly = int(round(iso_y - min_iy))

                if math.hypot(wx - dx, wy - dy) <= 44:
                    fl_id = "iso_door_threshold"
                elif bid == "park" and (tx > (x0 + x1) // 2 and ty > (y0 + y1) // 2):
                    fl_id = "iso_moor_grass"
                elif bid == "school" and (tx > (x0 + x1) // 2 and ty > (y0 + y1) // 2):
                    fl_id = "iso_gym_court"
                else:
                    fl_id = base_floor_id

                fl_spr = self.iso_lib.get_surface(fl_id)
                if fl_spr is not None:
                    surf.blit(fl_spr, (lx - fl_spr.get_width() // 2, ly - ISO_TILE_H // 2))

                # Crisp IsoEngine interior tile grid diamond outline
                diamond = [
                    (lx, ly - ISO_TILE_H // 2),
                    (lx + ISO_TILE_W // 2, ly),
                    (lx, ly + ISO_TILE_H // 2),
                    (lx - ISO_TILE_W // 2, ly),
                ]
                pygame.draw.polygon(surf, (46, 38, 32, 160), diamond, 1)

        # Pass 2: Isometric Woven Carpets in the center of the room
        cx_iso, cy_iso = self.world_to_iso(rx + rw * 0.5, ry + rh * 0.5)
        clx, cly = int(cx_iso - min_ix), int(cy_iso - min_iy)
        carpet_main = self.iso_lib.get_surface("iso_carpet_main")
        if carpet_main is not None:
            scaled_c = pygame.transform.smoothscale(carpet_main, (192, 96))
            surf.blit(scaled_c, (clx - 96, cly - 48))

        # Pass 3: Back Isometric Walls (tx == x0 -> NW wall, ty == y0 -> NE wall) & Front Cutaway Half-Walls
        for s in range((x0 + y0), (x1 + y1) + 1):
            for ty in range(y0, y1 + 1):
                tx = s - ty
                if not (x0 <= tx <= x1):
                    continue
                is_edge = tx in (x0, x1) or ty in (y0, y1)
                if not is_edge:
                    continue

                wx = tx * TILE_SIZE + 16
                wy = ty * TILE_SIZE + 16
                iso_x, iso_y = self.world_to_iso(wx, wy)
                lx = int(round(iso_x - min_ix))
                ly = int(round(iso_y - min_iy))

                near_door = math.hypot(wx - dx, wy - dy) <= 56
                if near_door:
                    w_id = "iso_wall_door_open_sw" if ty in (y0, y1) else "iso_wall_door_open_se"
                elif tx == x0 or ty == y0:
                    # Back walls: full height isometric walls with windows & bookcases
                    orient = "sw" if ty == y0 else "se"
                    step_idx = (tx - x0) if ty == y0 else (ty - y0)
                    if step_idx % 4 == 2:
                        w_id = f"iso_wall_window_{orient}"
                    elif bid in ("home", "school") and step_idx % 3 == 1:
                        w_id = f"iso_wall_books_{orient}"
                    else:
                        w_id = f"iso_wall_stone_{orient}"
                else:
                    # Front cutaway walls: low isometric half-wall so interior is never obscured
                    orient = "sw" if ty == y1 else "se"
                    w_id = f"iso_wall_half_{orient}"

                w_spr = self.iso_lib.get_surface(w_id) or self.iso_lib.get_surface(w_id.rsplit("_", 1)[0])
                if w_spr is not None:
                    surf.blit(w_spr, (lx - w_spr.get_width() // 2, ly + 16 - w_spr.get_height()))

        self.interior_room_surfaces[bid] = surf

    def _bake_fallback_tree(self) -> pygame.Surface:
        surf = pygame.Surface((96, 112), pygame.SRCALPHA)
        pygame.draw.circle(surf, (38, 76, 42), (48, 42), 34)
        return surf

    # =========================================================================
    # 3. ISOMETRIC OVERWORLD HOUSES, FURNITURE, QUEST STATIONS & GRID OVERLAY
    # =========================================================================
    def draw_iso_grid_overlay(
        self,
        surface: pygame.Surface,
        cam_x: float,
        cam_y: float,
        player_wx: float,
        player_wy: float,
        mouse_pos: tuple[int, int],
        click_target: tuple[float, float] | None = None,
        font_xs: pygame.font.Font | None = None,
    ):
        """
        Renders IsoEngine's interactive 2:1 isometric tile highlights:
        - Golden diamond under the player's current tile
        - Cyan diamond + coordinate badge under the hovered mouse tile
        - Emerald diamond on the active click-to-move destination tile
        """
        # 1. Player current isometric tile diamond
        pgx, pgy = int(player_wx // TILE_SIZE), int(player_wy // TILE_SIZE)
        if 0 <= pgx < GRID_W and 0 <= pgy < GRID_H:
            p_diamond = self.get_iso_tile_diamond(pgx, pgy, cam_x, cam_y)
            pygame.draw.polygon(surface, (242, 198, 82), p_diamond, 2)

        # 2. Click-to-walk target isometric tile diamond
        if click_target is not None:
            tgx, tgy = int(click_target[0] // TILE_SIZE), int(click_target[1] // TILE_SIZE)
            if 0 <= tgx < GRID_W and 0 <= tgy < GRID_H:
                t_diamond = self.get_iso_tile_diamond(tgx, tgy, cam_x, cam_y)
                pygame.draw.polygon(surface, (92, 242, 168), t_diamond, 2)

        # 3. Hovered mouse cursor isometric tile diamond
        mx, my = mouse_pos
        if my > 68:
            hgx, hgy = self.screen_to_grid_cell(mx, my, cam_x, cam_y)
            if 0 <= hgx < GRID_W and 0 <= hgy < GRID_H:
                h_diamond = self.get_iso_tile_diamond(hgx, hgy, cam_x, cam_y)
                pygame.draw.polygon(surface, (95, 228, 255), h_diamond, 2)
                if font_xs is not None:
                    tile_obj = self.iso_grid.get_tile(hgx, hgy)
                    spr_lbl = (tile_obj.tile_sprite or "iso_tile").replace("iso_", "").replace("_", " ")
                    tag = font_xs.render(f"IsoTile ({hgx}, {hgy}) • {spr_lbl.title()}", True, (195, 238, 255))
                    tag_bg = pygame.Rect(mx + 14, my + 12, tag.get_width() + 12, 18)
                    pygame.draw.rect(surface, (12, 16, 24), tag_bg, border_radius=5)
                    pygame.draw.rect(surface, (78, 168, 210), tag_bg, 1, border_radius=5)
                    surface.blit(tag, (mx + 20, my + 13))

    def draw_exterior_house(
        self,
        surface: pygame.Surface,
        b: dict,
        cam_x: float,
        cam_y: float,
        t_sec: float,
        occupants: list,
        protected_id: str | None = None,
        catalyst_id: str | None = None,
        player_near_door: bool = False,
        font_sm: pygame.font.Font | None = None,
        font_xs: pygame.font.Font | None = None,
    ):
        """
        Renders the 2:1 Isometric Landmark House (`iso_house_{bid}.png`) on the Overworld,
        with animated chimney coal-smoke, isometric doorway diamond beacon, and occupancy signboard.
        """
        bid = b["id"]
        spr = self.house_sprites.get(bid)
        if spr is None:
            return

        rx, ry, rw, rh = b["rect"]
        dx, dy = b["door_x"], b["door_y"]
        is_north = dy > ry + rh // 2

        # Anchor the isometric building just behind its front entrance door
        house_wx = dx
        house_wy = (dy - 48) if is_north else (ry + rh * 0.48)
        hsx, hsy = self.world_to_screen(house_wx, house_wy, cam_x, cam_y)
        sw, sh = spr.get_size()
        sx = hsx - sw // 2
        sy = hsy - sh + 34

        if sx + sw < -160 or sx > surface.get_width() + 160 or sy + sh < -160 or sy > surface.get_height() + 160:
            return

        # 1. Blit the 2:1 Isometric Exterior House Sprite
        surface.blit(spr, (sx, sy))

        # 2. Animated Steampunk Chimney Coal-Smoke Plumes
        for c_off in (int(sw * 0.32), int(sw * 0.68)):
            for p_i in range(3):
                age = (t_sec * 1.4 + p_i * 0.9 + c_off * 0.01) % 2.7
                puff_x = sx + c_off + int(math.sin(t_sec * 1.8 + p_i) * 8 + age * 10)
                puff_y = sy + 28 - int(age * 22)
                rad = int(6 + age * 5)
                alpha = max(0, min(115, int(115 * (1.0 - age / 2.7))))
                if alpha > 8:
                    p_surf = pygame.Surface((rad * 2 + 2, rad * 2 + 2), pygame.SRCALPHA)
                    pygame.draw.circle(p_surf, (212, 208, 202, alpha), (rad + 1, rad + 1), rad)
                    surface.blit(p_surf, (puff_x - rad, puff_y - rad))

        # 3. Glowing Isometric Doorway Diamond Beacon at `(dx, dy)`
        door_sx, door_sy = self.world_to_screen(dx, dy, cam_x, cam_y)
        pulse = int(4 + math.sin(t_sec * 5.0) * 3)
        dw = 42 + pulse
        dh = 21 + pulse // 2
        diamond = [
            (door_sx, door_sy - dh),
            (door_sx + dw, door_sy),
            (door_sx, door_sy + dh),
            (door_sx - dw, door_sy),
        ]
        ring_col = (95, 242, 168) if player_near_door else (255, 208, 92)
        beacon_s = pygame.Surface((dw * 2 + 8, dh * 2 + 8), pygame.SRCALPHA)
        local_d = [
            (dw + 4, 4),
            (dw * 2 + 4, dh + 4),
            (dw + 4, dh * 2 + 4),
            (4, dh + 4),
        ]
        pygame.draw.polygon(beacon_s, (*ring_col, 78 if player_near_door else 44), local_d)
        pygame.draw.polygon(beacon_s, (*ring_col, 230), local_d, 2)
        surface.blit(beacon_s, (door_sx - dw - 4, door_sy - dh - 4))

        # 4. Hanging Victorian Brass & Oak Guild Signboard + Live Occupancy Badge
        if font_sm is not None:
            sign_y = door_sy - 88
            lbl = font_sm.render(b["name"], True, (248, 238, 212))
            sign_w = lbl.get_width() + 28
            sign_rect = pygame.Rect(door_sx - sign_w // 2, sign_y, sign_w, 26)
            pygame.draw.rect(surface, (12, 14, 20), sign_rect.move(0, 3), border_radius=6)
            pygame.draw.rect(surface, (38, 26, 18), sign_rect, border_radius=6)
            pygame.draw.rect(surface, (218, 172, 78), sign_rect, 2, border_radius=6)
            surface.blit(lbl, (door_sx - lbl.get_width() // 2, sign_y + 4))

            if font_xs is not None:
                has_loved = any(c.id == protected_id for c in occupants)
                has_cat = any(c.id == catalyst_id for c in occupants)
                if occupants:
                    names_preview = ", ".join(c.name.split("(")[0].strip() for c in occupants[:3])
                    if len(occupants) > 3:
                        names_preview += f" +{len(occupants) - 3}"
                    occ_txt = f"Inside ({len(occupants)}): {names_preview}"
                else:
                    occ_txt = "Inside: Empty right now"

                occ_col = (
                    (98, 238, 255)
                    if has_loved
                    else ((255, 198, 88) if has_cat else ((218, 214, 204) if occupants else (138, 142, 154)))
                )
                occ_surf = font_xs.render(occ_txt, True, occ_col)
                occ_w = occ_surf.get_width() + 18
                occ_rect = pygame.Rect(door_sx - occ_w // 2, sign_y + 29, occ_w, 20)
                pygame.draw.rect(surface, (14, 18, 28), occ_rect, border_radius=6)
                pygame.draw.rect(
                    surface,
                    (88, 218, 245) if has_loved else (142, 114, 62),
                    occ_rect,
                    1,
                    border_radius=6,
                )
                surface.blit(occ_surf, (door_sx - occ_surf.get_width() // 2, sign_y + 31))

    def draw_street_prop(
        self, surface: pygame.Surface, ptype: str, wx: float, wy: float, cam_x: float, cam_y: float, t_sec: float
    ):
        sx, sy = self.world_to_screen(wx, wy, cam_x, cam_y)
        if sx < -100 or sx > surface.get_width() + 100 or sy < -120 or sy > surface.get_height() + 100:
            return

        if ptype == "barrel":
            if self.barrel_sprite:
                surface.blit(
                    self.barrel_sprite,
                    (sx - self.barrel_sprite.get_width() // 2, sy + 12 - self.barrel_sprite.get_height()),
                )
        elif ptype == "crate":
            if self.crate_sprite:
                surface.blit(
                    self.crate_sprite,
                    (sx - self.crate_sprite.get_width() // 2, sy + 12 - self.crate_sprite.get_height()),
                )
        elif ptype == "flower_cart":
            if self.patio_table_sprite:
                surface.blit(
                    self.patio_table_sprite,
                    (sx - self.patio_table_sprite.get_width() // 2, sy + 14 - self.patio_table_sprite.get_height()),
                )
        elif ptype == "lamp":
            if self.gaslamp_sprite:
                surface.blit(
                    self.gaslamp_sprite,
                    (sx - self.gaslamp_sprite.get_width() // 2, sy + 12 - self.gaslamp_sprite.get_height()),
                )
            glow_r = int(28 + math.sin(t_sec * 3.8 + wx * 0.01) * 4)
            glow_s = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
            pygame.draw.circle(glow_s, (255, 204, 88, 56), (glow_r, glow_r), glow_r)
            pygame.draw.circle(glow_s, (255, 238, 168, 92), (glow_r, glow_r), glow_r // 2)
            surface.blit(glow_s, (sx - glow_r, sy - 64 - glow_r))

    def draw_25d_furniture(self, surface: pygame.Surface, f: dict, cam_x: float, cam_y: float, t_sec: float):
        """Renders interior/courtyard furniture at its projected 2:1 isometric coordinate using IsoEngine sprites."""
        fx, fy, fw, fh = f["rect"]
        cx_w = fx + fw * 0.5
        cy_w = fy + fh * 0.5
        sx, sy = self.world_to_screen(cx_w, cy_w, cam_x, cam_y)
        name = f["name"]

        if sx < -160 or sx > surface.get_width() + 160 or sy < -160 or sy > surface.get_height() + 160:
            return

        if "Gym Court" in name:
            return  # Already baked into the isometric floor tiles

        # Map Dunwick furniture item to its generated 2:1 isometric sprite in assets/iso_sprites/
        if "Fountain" in name:
            spr_key = "iso_gargoyle_fountain"
        elif "Generator" in name or "Boiler" in name:
            spr_key = "iso_quest_power_generator"
        elif "Sofa" in name:
            spr_key = "iso_chesterfield_sofa"
        elif "Range" in name or "Hearth" in name or "Kitchen" in name or "Stove" in name:
            spr_key = "iso_victorian_coal_range"
        elif "Teahouse" in name:
            spr_key = "iso_table_round_items"
        elif "Table" in name or "Lecture" in name or "Desk" in name:
            spr_key = "iso_long_table_books"
        elif "Stall" in name:
            spr_key = "iso_display_sword" if (fx // 100) % 2 == 0 else "iso_display_books"
        elif "Galvanic" in name or "Difference" in name or "Records" in name:
            spr_key = "iso_lab_desk_pc"
        elif "Apothecary" in name:
            spr_key = "iso_bookcase_glass"
        else:
            spr_key = "iso_display_open"

        spr = self.iso_lib.get_surface(spr_key)
        if spr is not None:
            # Scale large centerpiece stations slightly larger
            if spr_key in ("iso_gargoyle_fountain", "iso_quest_power_generator"):
                spr = self.get_sprite(spr_key, (136, 128)) or spr
            elif spr_key in ("iso_chesterfield_sofa", "iso_long_table_books", "iso_victorian_coal_range"):
                spr = self.get_sprite(spr_key, (112, 92)) or spr
            surface.blit(spr, (sx - spr.get_width() // 2, sy + 18 - spr.get_height()))

            # Animated fountain water ripple or boiler cog pulse
            if "Fountain" in name:
                spray_h = int(6 + math.sin(t_sec * 7.5) * 3)
                pygame.draw.circle(surface, (195, 242, 255), (sx, sy - 46 - spray_h), 5)
            elif "Generator" in name or "Boiler" in name:
                pulse_r = int(12 + math.sin(t_sec * 6.0) * 3)
                pygame.draw.circle(surface, (95, 232, 255), (sx, sy - 34), pulse_r, 2)

    def draw_quest_object(
        self,
        surface: pygame.Surface,
        wobj: dict,
        cam_x: float,
        cam_y: float,
        t_sec: float,
        is_active_hazard: bool = False,
    ):
        """Renders interactive Quest Stations using their dedicated 2:1 isometric sprites on an isometric diamond."""
        oid = wobj["id"]
        sx, sy = self.world_to_screen(wobj["x"], wobj["y"], cam_x, cam_y)
        if sx < -120 or sx > surface.get_width() + 120 or sy < -120 or sy > surface.get_height() + 120:
            return

        col = (255, 82, 82) if is_active_hazard else wobj["color"]
        bob = int(math.sin(t_sec * 4.5 + wobj["x"] * 0.02) * 3)

        # Pulsing Isometric Tile Diamond Highlight beneath the quest station
        pulse = int(4 + math.sin(t_sec * 6.0) * 3)
        dw = 36 + pulse
        dh = 18 + pulse // 2
        glow_s = pygame.Surface((dw * 2 + 8, dh * 2 + 8), pygame.SRCALPHA)
        local_d = [
            (dw + 4, 4),
            (dw * 2 + 4, dh + 4),
            (dw + 4, dh * 2 + 4),
            (4, dh + 4),
        ]
        pygame.draw.polygon(glow_s, (*col[:3], 82 if is_active_hazard else 48), local_d)
        pygame.draw.polygon(glow_s, (*col[:3], 235), local_d, 2)
        surface.blit(glow_s, (sx - dw - 4, sy - dh - 4))

        iso_quest_key = f"iso_quest_{oid}"
        q_spr = self.iso_lib.get_surface(iso_quest_key)
        if q_spr is not None:
            surface.blit(q_spr, (sx - q_spr.get_width() // 2, sy + 14 - q_spr.get_height() + bob))
            return

    # =========================================================================
    # OCTOPATH TRAVELER HD-2D DYNAMIC LIGHTING, GOD-RAYS & TILT-SHIFT VIGNETTE
    # =========================================================================
    def _bake_radial_light(self, diameter: int, color: tuple[int, int, int]) -> pygame.Surface:
        surf = pygame.Surface((diameter, diameter))
        surf.fill((0, 0, 0))
        cx = cy = diameter // 2
        max_r = diameter // 2
        for r in range(max_r, 2, -3):
            t = 1.0 - (r / max_r)
            falloff = t * t
            col = _clamp_rgb(color[0] * falloff, color[1] * falloff, color[2] * falloff)
            pygame.draw.circle(surf, col, (cx, cy), r)
        return surf

    def _bake_octopath_tilt_shift_vignette(self, w: int, h: int) -> pygame.Surface:
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        top_band = 115
        bot_band = 135
        for y in range(top_band):
            t = 1.0 - (y / top_band)
            alpha = int(135 * (t ** 1.6))
            pygame.draw.line(surf, (6, 8, 14, alpha), (0, y), (w, y))
        for y in range(h - bot_band, h):
            t = (y - (h - bot_band)) / bot_band
            alpha = int(150 * (t ** 1.6))
            pygame.draw.line(surf, (6, 8, 14, alpha), (0, y), (w, y))

        side_band = 95
        for x in range(side_band):
            t = 1.0 - (x / side_band)
            alpha = int(95 * (t ** 1.8))
            pygame.draw.line(surf, (6, 8, 14, alpha), (x, 0), (x, h))
            pygame.draw.line(surf, (6, 8, 14, alpha), (w - 1 - x, 0), (w - 1 - x, h))
        return surf

    def render_hd2d_lighting_pass(
        self,
        screen: pygame.Surface,
        cam_x: float,
        cam_y: float,
        sim_minutes: float,
        player_wx: float,
        player_wy: float,
        loved_wx: float | None,
        loved_wy: float | None,
        world_objects: list[dict],
        active_hazard_obj_id: str | None,
        t_sec: float,
        active_scene: str = "OVERWORLD",
    ):
        """
        Executes the 3-Stage Octopath Traveler HD-2D Post-Processing Pipeline in 2:1 Isometric Screen Space.
        """
        sw, sh = screen.get_size()
        lw, lh = self._light_map_lowres.get_size()
        scale_x = lw / float(sw)
        scale_y = lh / float(sh)

        hour = (sim_minutes / 60.0) % 24.0
        if active_scene != "OVERWORLD":
            amb = (196, 184, 168)
        elif hour < 9.5:
            amb = (186, 178, 172)
        elif hour < 15.5:
            amb = (212, 198, 178)
        elif hour < 18.5:
            t_dusk = (hour - 15.5) / 3.0
            amb = _clamp_rgb(212 - 58 * t_dusk, 198 - 76 * t_dusk, 178 - 42 * t_dusk)
        else:
            t_night = min(1.0, (hour - 18.5) / 2.5)
            amb = _clamp_rgb(154 - 68 * t_night, 122 - 48 * t_night, 136 - 24 * t_night)

        self._light_map_lowres.fill(amb)

        def blit_point_light(brush: pygame.Surface, wx: float, wy: float, radius_px: int, screen_y_offset: int = 0):
            psx, psy = self.world_to_screen(wx, wy, cam_x, cam_y)
            psy += screen_y_offset
            sx = int(psx * scale_x)
            sy = int(psy * scale_y)
            r_low = max(8, int(radius_px * scale_x))
            if sx + r_low < 0 or sx - r_low > lw or sy + r_low < 0 or sy - r_low > lh:
                return
            scaled_b = pygame.transform.smoothscale(brush, (r_low * 2, r_low * 2))
            self._light_map_lowres.blit(scaled_b, (sx - r_low, sy - r_low), special_flags=pygame.BLEND_RGB_ADD)

        # 1. Player Warm Brass Lantern Pool (Sole-Knower Aura)
        flicker = int(math.sin(t_sec * 7.5) * 8)
        blit_point_light(self._light_radial_warm, player_wx, player_wy, 215 + flicker, screen_y_offset=-24)

        # 2. Protected Loved-One Cyan "Thread of Fate" Light Pool
        if loved_wx is not None and loved_wy is not None:
            blit_point_light(self._light_radial_cyan, loved_wx, loved_wy, 170, screen_y_offset=-24)

        if active_scene == "OVERWORLD":
            # 3A. Outdoor Street Gaslamps & Exterior House Window Glows
            for ptype, px, py in self.street_props:
                if ptype == "lamp":
                    blit_point_light(
                        self._light_radial_warm,
                        px,
                        py,
                        175 + int(math.sin(t_sec * 4.0 + px) * 6),
                        screen_y_offset=-52,
                    )
            for b in BUILDINGS:
                dx, dy = b["door_x"], b["door_y"]
                blit_point_light(self._light_radial_warm, dx, dy, 185, screen_y_offset=-32)
                blit_point_light(self._light_radial_warm, dx - 90, dy - 90, 150, screen_y_offset=-60)
                blit_point_light(self._light_radial_warm, dx + 90, dy - 90, 150, screen_y_offset=-60)
        else:
            # 3B. Interior Room Hearth, Candelabras & Interactive Station Glows
            for b in BUILDINGS:
                if b["id"] == active_scene:
                    rx, ry, rw, rh = b["rect"]
                    blit_point_light(self._light_radial_warm, rx + rw * 0.35, ry + rh * 0.42, 260)
                    blit_point_light(self._light_radial_warm, rx + rw * 0.65, ry + rh * 0.58, 260)
                    blit_point_light(self._light_radial_warm, b["door_x"], b["door_y"], 165)

            for wobj in world_objects:
                if wobj.get("building") != active_scene:
                    continue
                if wobj["id"] == active_hazard_obj_id:
                    blit_point_light(self._light_radial_crimson, wobj["x"], wobj["y"], 195, screen_y_offset=-16)
                elif wobj["id"] == "power_generator":
                    blit_point_light(self._light_radial_cyan, wobj["x"], wobj["y"], 220, screen_y_offset=-16)
                else:
                    blit_point_light(self._light_radial_warm, wobj["x"], wobj["y"], 135, screen_y_offset=-16)

        full_light = pygame.transform.smoothscale(self._light_map_lowres, (sw, sh))
        screen.blit(full_light, (0, 0), special_flags=pygame.BLEND_RGB_MULT)

        # Stage 2: Diagonal Volumetric Golden God-Rays & Floating Ember/Ash Motes
        if hour < 19.0 or active_scene != "OVERWORLD":
            ray_surf = pygame.Surface((sw, sh), pygame.SRCALPHA)
            ray_alpha = 15 if active_scene != "OVERWORLD" else (18 if hour < 15.5 else 24)
            ray_col = (255, 218, 138, ray_alpha) if hour < 15.5 else (255, 168, 98, ray_alpha)
            for rx_base in (140, 480, 860, 1180):
                drift = int(math.sin(t_sec * 0.45 + rx_base * 0.01) * 35)
                x0 = rx_base + drift
                pts = [(x0, 0), (x0 + 115, 0), (x0 + 360, sh), (x0 + 210, sh)]
                pygame.draw.polygon(ray_surf, ray_col, pts)
            screen.blit(ray_surf, (0, 0))

        for m in self._ash_motes:
            mx = int((m["x"] + t_sec * m["vx"]) % sw)
            my = int((m["y"] + t_sec * m["vy"] + math.sin(t_sec * 1.8 + m["phase"]) * 14.0) % sh)
            if m["ember"]:
                pygame.draw.circle(screen, (255, 192, 86), (mx, my), m["sz"])
            else:
                pygame.draw.circle(screen, (186, 182, 174), (mx, my), max(1, m["sz"] - 1))

        screen.blit(self._vignette_overlay, (0, 0))
