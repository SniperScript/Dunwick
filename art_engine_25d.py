"""
2.5D Defined Pixel-Art & Axonometric Environment Engine (art_engine_25d.py)
Inspired by:
- The user's reference artwork (Warm European Timber-Frame & Cobblestone 2.5D Town Square,
  striped market awnings, flower boxes, barrels, crates, stone fountains, and rich 3/4 depth)
- Terraria / Octopath Traveler / FIFE (Unknown Horizons) / GemRB (from bobeff/open-source-games)

Pre-bakes detailed 2.5D textures, timber-framed buildings, 3D-extruded furniture (tables with chairs,
counters, striped market stalls, lab benches), and animated quest item sprites so the world runs at
a locked 60 FPS with rich visual depth and continuous animations.
"""

import math
import os
import random
import pygame
from config import BUILDINGS, COLORS, WORLD_HEIGHT, WORLD_WIDTH


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
    Pre-renders and animates the 2.5D environment, timber-frame buildings,
    cobblestone streets, market awnings, 3D furniture, chairs, tables, and quest items.
    """

    def __init__(self, assets_dir: str):
        self.assets_dir = assets_dir
        self.portraits_cache: dict[str, pygame.Surface] = {}

        # Pre-baked 2.5D tile patterns
        self.cobble_tile = self._make_cobblestone_tile(128, 128, base=(142, 134, 124))
        self.sidewalk_tile = self._make_cobblestone_tile(128, 128, base=(186, 178, 164), brick_w=32, brick_h=16)
        self.grass_tile = self._make_grass_tile(160, 160)

        # Pre-baked static ground canvas (2600 x 1800) so rendering the whole town takes < 1ms per frame!
        self.world_ground_surface = pygame.Surface((WORLD_WIDTH, WORLD_HEIGHT))
        self._bake_world_ground_and_buildings()

        # Pre-baked 2.5D Tree, Barrel, Crate & Street Lamp sprites
        self.tree_sprite = self._bake_25d_tree_sprite()
        self.barrel_sprite = self._bake_barrel_sprite()
        self.crate_sprite = self._bake_crate_sprite()
        self.flower_cart_sprite = self._bake_flower_cart_sprite()

        # Ambient street props (barrels, crates, lamp posts, flower carts like the reference image!)
        self.street_props = [
            ("lamp", 400, 770), ("lamp", 750, 770), ("lamp", 1220, 770), ("lamp", 1580, 770),
            ("lamp", 2060, 770), ("lamp", 2420, 770),
            ("lamp", 400, 1000), ("lamp", 1220, 1000), ("lamp", 2060, 1000),
            ("barrel", 975, 755), ("barrel", 1002, 760), ("crate", 1595, 755),
            ("barrel", 975, 1035), ("crate", 1005, 1040), ("flower_cart", 1600, 1035),
            ("barrel", 1815, 755), ("crate", 2455, 755), ("flower_cart", 745, 755),
        ]

    def load_ai_portrait_if_available(self, char_id: str, size: tuple[int, int]) -> pygame.Surface | None:
        key = f"{char_id}_{size[0]}x{size[1]}"
        if key in self.portraits_cache:
            return self.portraits_cache[key]

        p_dir = os.path.join(self.assets_dir, "portraits")
        p_path = os.path.join(p_dir, f"{char_id}.png")
        if os.path.exists(p_path):
            try:
                img = pygame.image.load(p_path).convert_alpha()
                scaled = pygame.transform.smoothscale(img, size)
                self.portraits_cache[key] = scaled
                return scaled
            except Exception:
                return None
        return None

    # =========================================================================
    # 1. 2.5D COBBLESTONE, GRASS & TIMBER-FRAME BUILDING BAKER
    # =========================================================================
    def _make_cobblestone_tile(
        self, w: int, h: int, base: tuple[int, int, int], brick_w: int = 24, brick_h: int = 14
    ) -> pygame.Surface:
        surf = pygame.Surface((w, h))
        surf.fill(_shade(base, 0.72))  # Dark mortar joints
        rng = random.Random(42 + base[0])

        rows = h // brick_h
        cols = w // brick_w
        for r in range(rows + 1):
            offset = (brick_w // 2) if (r % 2 == 1) else 0
            for c in range(-1, cols + 1):
                bx = c * brick_w + offset
                by = r * brick_h
                tone = rng.uniform(0.88, 1.12)
                stone_col = _shade(base, tone)
                rect = pygame.Rect(bx + 1, by + 1, brick_w - 2, brick_h - 2)
                pygame.draw.rect(surf, stone_col, rect, border_radius=3)
                # Top sunlit bevel highlight (2.5D depth)
                pygame.draw.line(
                    surf, _shade(stone_col, 1.16), (rect.left + 2, rect.top + 1), (rect.right - 2, rect.top + 1), 1
                )
                # Bottom shadow bevel
                pygame.draw.line(
                    surf, _shade(stone_col, 0.78), (rect.left + 2, rect.bottom - 1), (rect.right - 2, rect.bottom - 1), 1
                )
        return surf

    def _make_grass_tile(self, w: int, h: int) -> pygame.Surface:
        surf = pygame.Surface((w, h))
        base = (76, 128, 72)
        surf.fill(base)
        rng = random.Random(101)
        for _ in range(180):
            gx = rng.randint(2, w - 6)
            gy = rng.randint(2, h - 6)
            patch_col = _shade(base, rng.uniform(0.88, 1.14))
            pygame.draw.circle(surf, patch_col, (gx, gy), rng.randint(2, 5))
        # Tiny grass blades & wildflowers
        for _ in range(45):
            bx = rng.randint(4, w - 6)
            by = rng.randint(6, h - 6)
            blade_col = (54, 102, 52) if rng.random() < 0.5 else (98, 152, 82)
            pygame.draw.line(surf, blade_col, (bx, by), (bx - 2, by - 4), 1)
            pygame.draw.line(surf, blade_col, (bx, by), (bx + 2, by - 5), 1)
            if rng.random() < 0.22:
                fcol = rng.choice([(245, 215, 85), (240, 115, 115), (245, 245, 240)])
                pygame.draw.circle(surf, fcol, (bx, by - 5), 2)
        return surf

    def _tile_fill_rect(self, target: pygame.Surface, tile: pygame.Surface, rect: pygame.Rect):
        tw, th = tile.get_size()
        old_clip = target.get_clip()
        target.set_clip(rect)
        for x in range(rect.left, rect.right, tw):
            for y in range(rect.top, rect.bottom, th):
                target.blit(tile, (x, y))
        target.set_clip(old_clip)

    def _bake_world_ground_and_buildings(self):
        surf = self.world_ground_surface

        # 1. Lush 2.5D Grass Meadow
        self._tile_fill_rect(surf, self.grass_tile, pygame.Rect(0, 0, WORLD_WIDTH, WORLD_HEIGHT))

        # 2. Sandstone Cobblestone Sidewalks & Plazas (like the reference image!)
        sidewalk_rects = [
            pygame.Rect(0, 745, WORLD_WIDTH, 270),
            pygame.Rect(785, 0, 170, WORLD_HEIGHT),
            pygame.Rect(1625, 0, 170, WORLD_HEIGHT),
        ]
        for sr in sidewalk_rects:
            self._tile_fill_rect(surf, self.sidewalk_tile, sr)
            pygame.draw.rect(surf, (92, 84, 74), sr, 3)

        # 3. Cobblestone Main Thoroughfare & Cross Streets
        road_rects = [
            pygame.Rect(0, 802, WORLD_WIDTH, 156),
            pygame.Rect(822, 0, 96, WORLD_HEIGHT),
            pygame.Rect(1662, 0, 96, WORLD_HEIGHT),
        ]
        for rr in road_rects:
            self._tile_fill_rect(surf, self.cobble_tile, rr)
            # Raised 2.5D stone curb along the top and bottom of the road
            pygame.draw.line(surf, (215, 205, 188), (rr.left, rr.top), (rr.right, rr.top), 3)
            pygame.draw.line(surf, (82, 76, 68), (rr.left, rr.bottom), (rr.right, rr.bottom), 4)

        # Center brass road studs / lane divider
        for rx in range(50, WORLD_WIDTH, 90):
            stud = pygame.Rect(rx, 876, 42, 6)
            pygame.draw.rect(surf, (228, 194, 96), stud, border_radius=3)
            pygame.draw.rect(surf, (110, 88, 36), stud, 1, border_radius=3)

        # Flagstone Crosswalks at building entrances (x=450, 1290, 2140)
        for cw_x in (450, 1290, 2140):
            for sy in range(810, 952, 22):
                stone = pygame.Rect(cw_x - 38, sy, 76, 14)
                pygame.draw.rect(surf, (224, 216, 202), stone, border_radius=3)
                pygame.draw.rect(surf, (112, 104, 92), stone, 2, border_radius=3)

        # 4. Bake each of the 6 2.5D Timber-Frame Buildings (Walls, Shingled Roofs, Floors, Awnings, Windows)
        for b in BUILDINGS:
            self._bake_single_building(surf, b)

    def _bake_single_building(self, surf: pygame.Surface, b: dict):
        rx, ry, rw, rh = b["rect"]
        door_x, door_y = b["door_x"], b["door_y"]
        bid = b["id"]
        f_col = b["floor_color"]
        r_col = b["roof_color"]

        # A. 2.5D Building Drop Shadow on the ground
        shadow_rect = pygame.Rect(rx + 12, ry + 14, rw, rh)
        pygame.draw.rect(surf, (42, 64, 44), shadow_rect, border_radius=10)

        # B. Interior Floor Planks / Tiles
        floor_rect = pygame.Rect(rx, ry, rw, rh)
        pygame.draw.rect(surf, f_col, floor_rect, border_radius=8)

        if bid == "park":
            # Lush garden cobblestones & flower beds for Town Park
            self._tile_fill_rect(surf, self.grass_tile, floor_rect.inflate(-16, -16))
            # Stone plaza path from entrance to Police Post and Fountain
            path_v = pygame.Rect(door_x - 54, ry + 12, 108, rh - 24)
            path_h = pygame.Rect(rx + 24, ry + 180, rw - 48, 96)
            self._tile_fill_rect(surf, self.sidewalk_tile, path_v)
            self._tile_fill_rect(surf, self.sidewalk_tile, path_h)
        elif bid in ("cafe", "office"):
            # Checkered / stone tile floor
            tile_sz = 32
            alt_col = _shade(f_col, 0.93)
            for tx in range(rx + 12, rx + rw - 12, tile_sz):
                for ty in range(ry + 50, ry + rh - 12, tile_sz):
                    if ((tx // tile_sz) + (ty // tile_sz)) % 2 == 0:
                        pygame.draw.rect(surf, alt_col, (tx, ty, tile_sz, tile_sz))
                    pygame.draw.rect(surf, _shade(f_col, 0.85), (tx, ty, tile_sz, tile_sz), 1)
        else:
            # Warm wooden floorboards / herringbone planks
            plank_h = 18
            for py in range(ry + 50, ry + rh - 10, plank_h):
                pygame.draw.line(surf, _shade(f_col, 0.86), (rx + 10, py), (rx + rw - 10, py), 2)
                for px in range(rx + 20 + ((py // plank_h) % 2) * 45, rx + rw - 20, 90):
                    pygame.draw.line(surf, _shade(f_col, 0.82), (px, py), (px, py + plank_h), 1)

        # C. Decorative Interior Woven Rugs in Home, Cafe, and Office
        if bid == "home":
            rug = pygame.Rect(rx + 330, ry + 170, 260, 160)
            pygame.draw.rect(surf, (165, 58, 58), rug, border_radius=8)
            pygame.draw.rect(surf, (235, 195, 95), rug.inflate(-12, -12), 2, border_radius=6)
        elif bid == "cafe":
            rug = pygame.Rect(rx + 180, ry + 220, 300, 180)
            pygame.draw.rect(surf, (175, 78, 108), rug, border_radius=10)
            pygame.draw.rect(surf, (245, 225, 195), rug.inflate(-14, -14), 2, border_radius=8)

        # D. 3D Extruded Perimeter Timber-Frame & Stone Walls (16px thick with top & inner face)
        wall_outer = (58, 44, 34)
        wall_plaster = (232, 220, 198)
        wall_stone = (128, 122, 114)
        pygame.draw.rect(surf, wall_plaster, floor_rect, 14, border_radius=8)
        pygame.draw.rect(surf, wall_outer, floor_rect, 4, border_radius=8)

        # Timber cross-beams along the East and West walls
        for by in range(ry + 60, ry + rh - 20, 48):
            pygame.draw.rect(surf, wall_outer, (rx, by, 14, 8))
            pygame.draw.rect(surf, wall_outer, (rx + rw - 14, by, 14, 8))

        # E. 2.5D Pitched Shingled Roof Header & Timber Gable (Top of Building)
        roof_h = 64
        roof_rect = pygame.Rect(rx - 4, ry - 10, rw + 8, roof_h)
        # Roof drop shadow onto interior floor
        pygame.draw.rect(surf, _shade(f_col, 0.72), (rx + 8, ry + roof_h - 10, rw - 16, 14))
        # Shingled roof body
        pygame.draw.rect(surf, r_col, roof_rect, border_radius=10)
        # Shingle courses (scalloped horizontal tile lines like the reference image!)
        for sy in range(roof_rect.top + 10, roof_rect.bottom - 8, 11):
            pygame.draw.line(surf, _shade(r_col, 0.76), (roof_rect.left + 6, sy), (roof_rect.right - 6, sy), 2)
            for sx in range(roof_rect.left + 12 + ((sy // 11) % 2) * 14, roof_rect.right - 12, 28):
                pygame.draw.line(surf, _shade(r_col, 0.72), (sx, sy), (sx, sy + 10), 1)

        # Timber ridge beam & gable trim
        pygame.draw.rect(surf, (68, 46, 32), (roof_rect.left, roof_rect.top, roof_rect.width, 8), border_radius=4)
        pygame.draw.rect(surf, (52, 36, 24), roof_rect, 3, border_radius=10)

        # Chimney on left/right corner of roof
        chim_x = rx + rw - 78
        chim_y = ry - 22
        pygame.draw.rect(surf, (145, 78, 62), (chim_x, chim_y, 34, 32), border_radius=3)
        pygame.draw.rect(surf, (75, 42, 34), (chim_x - 3, chim_y, 40, 8), border_radius=2)
        pygame.draw.rect(surf, (45, 28, 24), (chim_x, chim_y, 34, 32), 2, border_radius=3)

        # Windows with Flower Boxes along the Façade Wall!
        win_y = ry + rh - 24 if door_y > ry + rh // 2 else ry + roof_h - 6
        for wx in range(rx + 55, rx + rw - 95, 135):
            if abs(wx + 24 - door_x) < 95:
                continue
            # Window frame
            w_rect = pygame.Rect(wx, win_y - 8, 48, 22)
            pygame.draw.rect(surf, (255, 224, 138), w_rect, border_radius=3)
            pygame.draw.rect(surf, (62, 42, 28), w_rect, 3, border_radius=3)
            pygame.draw.line(surf, (62, 42, 28), (w_rect.centerx, w_rect.top), (w_rect.centerx, w_rect.bottom), 2)
            # Flower box beneath window (red, gold, and lush green blooms like reference image!)
            fbox = pygame.Rect(wx - 4, w_rect.bottom - 2, 56, 10)
            pygame.draw.rect(surf, (112, 68, 42), fbox, border_radius=2)
            pygame.draw.rect(surf, (48, 30, 18), fbox, 1, border_radius=2)
            for fx_dot in range(wx, wx + 48, 9):
                pygame.draw.circle(surf, (62, 138, 64), (fx_dot, fbox.top), 4)
                bloom_c = (235, 75, 75) if (fx_dot // 9) % 2 == 0 else (250, 210, 75)
                pygame.draw.circle(surf, bloom_c, (fx_dot + 1, fbox.top - 1), 2)

        # F. Wide Open 5-Tile Doorway Threshold + Striped Awning Over Entrance!
        door_gap = pygame.Rect(door_x - 66, door_y - 16, 132, 32)
        pygame.draw.rect(surf, f_col, door_gap, border_radius=4)
        # Stone threshold steps
        step_rect = pygame.Rect(door_x - 54, door_y - 11, 108, 22)
        pygame.draw.rect(surf, (212, 198, 174), step_rect, border_radius=4)
        pygame.draw.rect(surf, (95, 82, 66), step_rect, 2, border_radius=4)
        # Carved wooden door pillars on either side of the wide opening
        pygame.draw.rect(surf, (92, 58, 36), (door_x - 70, door_y - 18, 14, 34), border_radius=3)
        pygame.draw.rect(surf, (92, 58, 36), (door_x + 56, door_y - 18, 14, 34), border_radius=3)

        # Striped 2.5D Shop/Building Awning above the doorway (Red/Cream or Gold/Cream stripes)
        awn_y = door_y - 34 if door_y > ry + rh // 2 else door_y + 10
        awn_w = 136
        awn_h = 22
        awn_x = door_x - awn_w // 2
        stripe_w = 17
        stripe_c1 = r_col
        stripe_c2 = (248, 240, 222)
        for s_i in range(awn_w // stripe_w):
            scol = stripe_c1 if s_i % 2 == 0 else stripe_c2
            s_rect = pygame.Rect(awn_x + s_i * stripe_w, awn_y, stripe_w, awn_h)
            pygame.draw.rect(surf, scol, s_rect, border_bottom_left_radius=4, border_bottom_right_radius=4)
        pygame.draw.rect(surf, (48, 34, 24), (awn_x, awn_y, awn_w, awn_h), 2, border_radius=4)

    # =========================================================================
    # 2. 2.5D TREES, BARRELS, CRATES, CARTS & STREET LAMPS
    # =========================================================================
    def _bake_25d_tree_sprite(self) -> pygame.Surface:
        surf = pygame.Surface((96, 112), pygame.SRCALPHA)
        # Ground shadow
        pygame.draw.ellipse(surf, (22, 38, 24, 135), (14, 78, 68, 28))
        # Gnarled 2.5D wooden trunk & roots
        pygame.draw.rect(surf, (96, 62, 38), (40, 56, 16, 36), border_radius=4)
        pygame.draw.line(surf, (124, 84, 52), (44, 58), (44, 88), 3)
        pygame.draw.rect(surf, (48, 30, 18), (40, 56, 16, 36), 2, border_radius=4)

        # Multi-tiered pixel-art foliage clusters (dark base -> mid leaf -> sunlit crown)
        clusters = [
            (48, 48, 34, (44, 96, 48)),
            (30, 50, 24, (48, 106, 52)),
            (66, 50, 24, (48, 106, 52)),
            (48, 36, 30, (64, 134, 62)),
            (32, 38, 21, (74, 148, 68)),
            (64, 38, 21, (74, 148, 68)),
            (46, 26, 22, (98, 174, 78)),
            (36, 28, 14, (122, 194, 88)),
        ]
        for cx, cy, rad, col in clusters:
            pygame.draw.circle(surf, col, (cx, cy), rad)
            pygame.draw.circle(surf, (32, 62, 34), (cx, cy), rad, 1)
        # Red apples / blossoms in the canopy
        for ax, ay in [(34, 36), (58, 32), (44, 48), (62, 46), (28, 48)]:
            pygame.draw.circle(surf, (228, 72, 64), (ax, ay), 3)
            pygame.draw.circle(surf, (255, 165, 145), (ax - 1, ay - 1), 1)
        return surf

    def _bake_barrel_sprite(self) -> pygame.Surface:
        surf = pygame.Surface((34, 42), pygame.SRCALPHA)
        pygame.draw.ellipse(surf, (20, 24, 28, 120), (3, 28, 28, 12))
        body = pygame.Rect(5, 8, 24, 28)
        pygame.draw.rect(surf, (138, 86, 48), body, border_radius=6)
        # Vertical stave lines
        for sx in (10, 17, 23):
            pygame.draw.line(surf, (94, 56, 30), (sx, 9), (sx, 34), 1)
        # Iron hoops
        pygame.draw.rect(surf, (68, 74, 84), (5, 13, 24, 4))
        pygame.draw.rect(surf, (68, 74, 84), (5, 26, 24, 4))
        # Top lid ellipse
        pygame.draw.ellipse(surf, (164, 108, 64), (6, 6, 22, 9))
        pygame.draw.ellipse(surf, (58, 36, 20), (6, 6, 22, 9), 2)
        pygame.draw.rect(surf, (52, 32, 18), body, 2, border_radius=6)
        return surf

    def _bake_crate_sprite(self) -> pygame.Surface:
        surf = pygame.Surface((36, 38), pygame.SRCALPHA)
        pygame.draw.rect(surf, (20, 24, 28, 120), (4, 26, 30, 10), border_radius=3)
        # Top face (2.5D)
        pygame.draw.polygon(surf, (194, 144, 88), [(4, 12), (18, 5), (32, 12), (18, 18)])
        # Front-left & Front-right faces
        pygame.draw.rect(surf, (168, 118, 68), (4, 12, 28, 22), border_radius=3)
        pygame.draw.rect(surf, (142, 96, 52), (8, 15, 20, 16), 2)
        pygame.draw.line(surf, (142, 96, 52), (8, 15), (28, 31), 2)
        pygame.draw.rect(surf, (58, 38, 22), (4, 12, 28, 22), 2, border_radius=3)
        return surf

    def _bake_flower_cart_sprite(self) -> pygame.Surface:
        surf = pygame.Surface((68, 58), pygame.SRCALPHA)
        pygame.draw.ellipse(surf, (20, 24, 28, 120), (6, 40, 56, 14))
        # Wooden cart tray
        pygame.draw.rect(surf, (148, 96, 54), (8, 22, 52, 20), border_radius=4)
        pygame.draw.rect(surf, (58, 36, 20), (8, 22, 52, 20), 2, border_radius=4)
        # Colorful flower bunches in the cart
        for fx, col in [(16, (235, 75, 85)), (28, (250, 205, 65)), (40, (235, 125, 185)), (50, (95, 195, 245))]:
            pygame.draw.circle(surf, (58, 138, 62), (fx, 20), 8)
            pygame.draw.circle(surf, col, (fx - 2, 18), 4)
            pygame.draw.circle(surf, col, (fx + 3, 19), 4)
        # Spoked wooden wheel
        pygame.draw.circle(surf, (88, 54, 30), (34, 44), 10, 3)
        pygame.draw.circle(surf, (210, 185, 140), (34, 44), 3)
        return surf

    def draw_street_prop(self, surface: pygame.Surface, ptype: str, wx: float, wy: float, cam_x: float, cam_y: float, t_sec: float):
        sx = int(wx - cam_x)
        sy = int(wy - cam_y)
        if ptype == "barrel":
            surface.blit(self.barrel_sprite, (sx - 17, sy - 34))
        elif ptype == "crate":
            surface.blit(self.crate_sprite, (sx - 18, sy - 32))
        elif ptype == "flower_cart":
            surface.blit(self.flower_cart_sprite, (sx - 34, sy - 48))
        elif ptype == "lamp":
            # Cast iron 2.5D street lamp with animated warm lantern glow!
            pygame.draw.ellipse(surface, (20, 24, 28), (sx - 10, sy - 4, 20, 8))
            pygame.draw.rect(surface, (42, 48, 58), (sx - 3, sy - 58, 6, 56), border_radius=2)
            pygame.draw.rect(surface, (58, 66, 78), (sx - 7, sy - 10, 14, 8), border_radius=2)
            # Lantern housing
            lantern = pygame.Rect(sx - 9, sy - 72, 18, 16)
            pygame.draw.rect(surface, (255, 225, 125), lantern, border_radius=4)
            pygame.draw.rect(surface, (36, 40, 48), lantern, 2, border_radius=4)
            pygame.draw.polygon(surface, (36, 40, 48), [(sx - 11, sy - 72), (sx, sy - 80), (sx + 11, sy - 72)])
            # Soft warm halo
            glow_r = int(22 + math.sin(t_sec * 3.5 + wx * 0.01) * 3)
            glow_s = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
            pygame.draw.circle(glow_s, (255, 215, 95, 42), (glow_r, glow_r), glow_r)
            surface.blit(glow_s, (sx - glow_r, sy - 64 - glow_r))

    # =========================================================================
    # 3. 2.5D 3D-EXTRUDED FURNITURE, CHAIRS, TABLES & MARKET STALLS
    # =========================================================================
    def draw_25d_furniture(self, surface: pygame.Surface, f: dict, cam_x: float, cam_y: float, t_sec: float):
        fx, fy, fw, fh = f["rect"]
        sx = int(fx - cam_x)
        sy = int(fy - cam_y)
        name = f["name"]
        base_col = f["color"]

        if sx + fw < -80 or sx > surface.get_width() + 80 or sy + fh < -80 or sy > surface.get_height() + 80:
            return

        # 1. Town Park Animated 3-Tier Stone Fountain (Just like the reference image!)
        if "Fountain" in name:
            cx, cy = sx + fw // 2, sy + fh // 2
            rx_outer = fw // 2
            # Drop shadow
            pygame.draw.circle(surface, (36, 58, 38), (cx + 6, cy + 8), rx_outer)
            # Outer carved stone basin rim
            pygame.draw.circle(surface, (168, 164, 156), (cx, cy), rx_outer)
            pygame.draw.circle(surface, (212, 208, 198), (cx, cy - 3), rx_outer - 4)
            pygame.draw.circle(surface, (68, 64, 58), (cx, cy), rx_outer, 3)
            # Sparkling animated water pool
            pygame.draw.circle(surface, (64, 168, 224), (cx, cy), rx_outer - 14)
            for ring_i in range(3):
                r_wave = int(((t_sec * 28.0 + ring_i * 24) % (rx_outer - 18)))
                pygame.draw.circle(surface, (165, 232, 255), (cx, cy), max(6, r_wave), 2)
            # Central stone pedestal & spouting water plume
            pygame.draw.circle(surface, (148, 144, 136), (cx, cy), 22)
            pygame.draw.rect(surface, (182, 178, 168), (cx - 12, cy - 34, 24, 34), border_radius=4)
            pygame.draw.rect(surface, (58, 54, 48), (cx - 12, cy - 34, 24, 34), 2, border_radius=4)
            # Animated water spray arcs
            spray_h = int(12 + math.sin(t_sec * 8.0) * 4)
            pygame.draw.circle(surface, (215, 248, 255), (cx, cy - 36 - spray_h // 2), 8)
            for ang in (-0.8, -0.4, 0.0, 0.4, 0.8):
                px = int(cx + math.sin(ang) * 18)
                py = int(cy - 28 + abs(ang) * 14)
                pygame.draw.line(surface, (195, 242, 255), (cx, cy - 38), (px, py), 2)
            return

        # 2. Main Town Aether-Core Power Generator (Towering 2.5D Copper/Steel Reactor with Animated Plasma!)
        if "Generator" in name:
            # Heavy steel foundation platform
            plat = pygame.Rect(sx, sy, fw, fh)
            pygame.draw.rect(surface, (28, 32, 40), plat.move(8, 10), border_radius=10)
            pygame.draw.rect(surface, (54, 62, 76), plat, border_radius=10)
            # Yellow/black hazard stripes along the bottom edge
            haz_y = sy + fh - 18
            for hx in range(sx + 8, sx + fw - 16, 24):
                pygame.draw.polygon(
                    surface,
                    (235, 185, 45),
                    [(hx, haz_y), (hx + 12, haz_y), (hx + 6, haz_y + 14), (hx - 6, haz_y + 14)],
                )
            pygame.draw.rect(surface, (24, 28, 36), plat, 3, border_radius=10)

            # Twin Copper Induction Coils on Left & Right
            for coil_x in (sx + 24, sx + fw - 68):
                for cy_off in range(sy + 36, sy + fh - 48, 34):
                    c_rect = pygame.Rect(coil_x, cy_off, 44, 24)
                    pygame.draw.rect(surface, (198, 118, 62), c_rect, border_radius=6)
                    pygame.draw.line(surface, (245, 178, 115), (c_rect.left + 4, c_rect.top + 4), (c_rect.right - 4, c_rect.top + 4), 2)
                    pygame.draw.rect(surface, (52, 32, 18), c_rect, 2, border_radius=6)

            # Central Glowing Aether-Core Plasma Containment Cylinder
            core_rect = pygame.Rect(sx + 78, sy + 28, fw - 156, fh - 64)
            pygame.draw.rect(surface, (22, 38, 54), core_rect, border_radius=14)
            pulse = 0.5 + 0.5 * math.sin(t_sec * 6.0)
            plasma_col = _clamp_rgb(65 + pulse * 60, 205 + pulse * 45, 255)
            inner_core = core_rect.inflate(-16, -16)
            pygame.draw.rect(surface, plasma_col, inner_core, border_radius=10)
            # Animated energy rings moving vertically inside the core
            for r_i in range(4):
                ry_pos = inner_core.top + int(((t_sec * 65.0 + r_i * 55.0) % max(1, inner_core.height - 8)))
                pygame.draw.line(
                    surface, (255, 255, 255), (inner_core.left + 4, ry_pos), (inner_core.right - 4, ry_pos), 3
                )
            pygame.draw.rect(surface, (36, 44, 58), core_rect, 4, border_radius=14)
            return

        # 3. School Gym Basketball Court (Painted Hardwood Court markings, no solid table extrusion)
        if "Gym Court" in name:
            court = pygame.Rect(sx, sy, fw, fh)
            pygame.draw.rect(surface, (208, 148, 92), court, border_radius=6)
            pygame.draw.rect(surface, (245, 242, 232), court.inflate(-12, -12), 3, border_radius=4)
            pygame.draw.circle(surface, (245, 242, 232), court.center, 36, 3)
            pygame.draw.line(surface, (245, 242, 232), (court.centerx, court.top + 6), (court.centerx, court.bottom - 6), 3)
            return

        # 4. 2.5D Cafe / Classroom / Study Tables with Cushioned Chairs tucked around them!
        if "Table" in name or "Classroom" in name or "Desk" in name:
            # Draw cushioned 2.5D chairs around the table FIRST (top & sides)
            chair_col = (155, 68, 62) if "Cafe" in name else (72, 108, 148)
            for cx_pos in range(sx + 22, sx + fw - 34, 56):
                # Top chair backrest & seat peeking above table
                c_top = pygame.Rect(cx_pos, sy - 14, 30, 18)
                pygame.draw.rect(surface, _shade(chair_col, 0.85), c_top, border_radius=4)
                pygame.draw.rect(surface, (38, 28, 22), c_top, 2, border_radius=4)

            # Floor shadow under table
            pygame.draw.rect(surface, (32, 36, 42), (sx + 4, sy + 10, fw, fh - 2), border_radius=6)

            # Carved wooden table legs at bottom corners
            leg_col = (82, 52, 32)
            pygame.draw.rect(surface, leg_col, (sx + 6, sy + fh - 12, 10, 16), border_radius=2)
            pygame.draw.rect(surface, leg_col, (sx + fw - 16, sy + fh - 12, 10, 16), border_radius=2)

            # 3D Front Apron / Thickness of the Table
            apron_rect = pygame.Rect(sx, sy + 12, fw, fh - 14)
            pygame.draw.rect(surface, _shade(base_col, 0.76), apron_rect, border_radius=6)
            pygame.draw.rect(surface, (42, 30, 22), apron_rect, 2, border_radius=6)

            # 2.5D Tabletop Surface (shifted up to show 3D thickness!)
            top_rect = pygame.Rect(sx, sy, fw, fh - 12)
            pygame.draw.rect(surface, base_col, top_rect, border_radius=6)
            pygame.draw.line(
                surface, _shade(base_col, 1.22), (top_rect.left + 4, top_rect.top + 2), (top_rect.right - 4, top_rect.top + 2), 2
            )
            pygame.draw.rect(surface, (45, 32, 22), top_rect, 2, border_radius=6)

            # Tabletop Props (Coffee cups, books, laptops, lamps!)
            if "Cafe" in name:
                # White porcelain coffee cups & pastry plate
                pygame.draw.circle(surface, (245, 242, 236), (sx + 32, sy + 26), 9)
                pygame.draw.circle(surface, (112, 68, 42), (sx + 32, sy + 26), 5)
                pygame.draw.circle(surface, (245, 242, 236), (sx + fw - 34, sy + 32), 10)
                pygame.draw.circle(surface, (225, 145, 85), (sx + fw - 34, sy + 32), 6)
            else:
                # Open ledger book & brass desk lamp
                book = pygame.Rect(sx + 24, sy + 16, 34, 24)
                pygame.draw.rect(surface, (245, 238, 220), book, border_radius=2)
                pygame.draw.rect(surface, (62, 48, 36), book, 2, border_radius=2)
                pygame.draw.line(surface, (120, 110, 95), (book.centerx, book.top + 2), (book.centerx, book.bottom - 2), 1)
                pygame.draw.circle(surface, (235, 195, 75), (sx + fw - 28, sy + 22), 9)
                pygame.draw.circle(surface, (52, 42, 28), (sx + fw - 28, sy + 22), 9, 2)
            return

        # 5. 2.5D Living Room Sofa (Plush Cushions, Armrests & Backrest)
        if "Sofa" in name:
            pygame.draw.rect(surface, (36, 40, 46), (sx + 5, sy + 8, fw, fh), border_radius=8)
            # Backrest
            back = pygame.Rect(sx, sy, fw, 28)
            pygame.draw.rect(surface, _shade(base_col, 0.82), back, border_radius=8)
            pygame.draw.rect(surface, (32, 42, 58), back, 2, border_radius=8)
            # Seat cushions (3 sections)
            c_w = (fw - 36) // 3
            for i in range(3):
                cush = pygame.Rect(sx + 18 + i * c_w, sy + 22, c_w - 2, fh - 26)
                pygame.draw.rect(surface, base_col, cush, border_radius=6)
                pygame.draw.rect(surface, (32, 42, 58), cush, 2, border_radius=6)
            # Left & Right rolled armrests
            for ax in (sx, sx + fw - 20):
                arm = pygame.Rect(ax, sy + 12, 20, fh - 12)
                pygame.draw.rect(surface, _shade(base_col, 0.9), arm, border_radius=6)
                pygame.draw.rect(surface, (32, 42, 58), arm, 2, border_radius=6)
            return

        # 6. 2.5D Market Stalls, Counters & Science Lab Benches (with Striped Canopy / Display Crates!)
        pygame.draw.rect(surface, (32, 36, 42), (sx + 5, sy + 9, fw, fh), border_radius=6)
        front_face = pygame.Rect(sx, sy + 14, fw, fh - 14)
        pygame.draw.rect(surface, _shade(base_col, 0.74), front_face, border_radius=6)
        # Wood paneling on front of counter
        for px in range(sx + 18, sx + fw - 18, 36):
            pygame.draw.rect(surface, _shade(base_col, 0.64), (px, sy + 20, 24, fh - 26), 2, border_radius=2)
        pygame.draw.rect(surface, (42, 30, 22), front_face, 2, border_radius=6)

        # Countertop
        top_face = pygame.Rect(sx - 2, sy, fw + 4, fh - 16)
        pygame.draw.rect(surface, base_col, top_face, border_radius=6)
        pygame.draw.rect(surface, (42, 30, 22), top_face, 2, border_radius=6)

        # Countertop Goods (Baskets of fruit/bread on Market stalls, flasks on Science Bench, espresso machine at Cafe!)
        if "Stall" in name:
            # Woven display baskets filled with colorful goods (just like the reference image!)
            goods_colors = [(235, 85, 65), (245, 195, 65), (115, 185, 75), (215, 145, 85)]
            for idx, gx in enumerate(range(sx + 16, sx + fw - 36, 48)):
                basket = pygame.Rect(gx, sy + 8, 36, 26)
                pygame.draw.rect(surface, (152, 104, 58), basket, border_radius=4)
                pygame.draw.rect(surface, (58, 38, 22), basket, 2, border_radius=4)
                gcol = goods_colors[idx % len(goods_colors)]
                for ox, oy in [(9, 9), (18, 8), (27, 10), (13, 17), (23, 17)]:
                    pygame.draw.circle(surface, gcol, (gx + ox, sy + 8 + oy), 5)
                    pygame.draw.circle(surface, _shade(gcol, 1.25), (gx + ox - 1, sy + 7 + oy), 2)
        elif "Science" in name or "Chemist" in name:
            for gx in range(sx + 24, sx + fw - 30, 52):
                pygame.draw.circle(surface, (85, 235, 205), (gx, sy + 22), 9)
                pygame.draw.circle(surface, (32, 58, 62), (gx, sy + 22), 9, 2)
                pygame.draw.rect(surface, (215, 238, 245), (gx - 3, sy + 8, 6, 8))

    # =========================================================================
    # 4. ANIMATED 2.5D QUEST ITEM & TERMINAL SPRITES (WORLD_OBJECTS)
    # =========================================================================
    def draw_quest_object(self, surface: pygame.Surface, wobj: dict, cam_x: float, cam_y: float, t_sec: float):
        oid = wobj["id"]
        sx = int(wobj["x"] - cam_x)
        sy = int(wobj["y"] - cam_y)
        col = wobj["color"]
        bob = int(math.sin(t_sec * 4.5 + wobj["x"] * 0.02) * 3)

        # Subtle golden floor indicator ring
        pulse_r = int(20 + math.sin(t_sec * 5.0) * 2)
        pygame.draw.ellipse(surface, (28, 34, 46), (sx - pulse_r, sy - 8, pulse_r * 2, 18))
        pygame.draw.ellipse(surface, col, (sx - pulse_r, sy - 8, pulse_r * 2, 18), 2)

        if oid == "study_notebook":
            # 2.5D Leather-Bound Detective Case Tome & Magnifying Glass
            book = pygame.Rect(sx - 16, sy - 22 + bob, 32, 22)
            pygame.draw.rect(surface, (148, 64, 42), book, border_radius=4)
            pygame.draw.rect(surface, (248, 238, 210), book.inflate(-6, -6), border_radius=2)
            pygame.draw.line(surface, (148, 64, 42), (sx, book.top + 2), (sx, book.bottom - 2), 2)
            pygame.draw.rect(surface, (42, 24, 18), book, 2, border_radius=4)
            # Gold bookmark ribbon
            pygame.draw.line(surface, (255, 215, 75), (sx + 4, book.bottom - 2), (sx + 8, book.bottom + 5), 3)

        elif oid == "cafe_counter":
            # Steaming Brass & Porcelain Espresso Machine Cup
            cup = pygame.Rect(sx - 11, sy - 22 + bob, 22, 20)
            pygame.draw.ellipse(surface, (235, 232, 225), (sx - 15, sy - 6 + bob, 30, 10))
            pygame.draw.rect(surface, (248, 245, 240), cup, border_radius=5)
            pygame.draw.rect(surface, (52, 38, 32), cup, 2, border_radius=5)
            pygame.draw.ellipse(surface, (112, 64, 36), (sx - 8, sy - 20 + bob, 16, 6))
            # Rising animated steam curls
            for s_i in range(2):
                st_y = sy - 26 + bob - int((t_sec * 18 + s_i * 7) % 12)
                st_x = sx - 4 + s_i * 8 + int(math.sin(t_sec * 6 + s_i) * 3)
                pygame.draw.circle(surface, (245, 245, 250), (st_x, st_y), 3)

        elif oid == "school_lab_table":
            # Animated Science Oscilloscope & Frequency Scanner
            housing = pygame.Rect(sx - 18, sy - 26 + bob, 36, 26)
            pygame.draw.rect(surface, (58, 72, 88), housing, border_radius=5)
            scr = housing.inflate(-8, -8)
            pygame.draw.rect(surface, (16, 38, 36), scr, border_radius=3)
            # Live animated sine wave across the oscilloscope screen!
            pts = []
            for px in range(scr.left + 2, scr.right - 2, 3):
                wy = scr.centery + int(math.sin(t_sec * 10.0 + px * 0.35) * 5)
                pts.append((px, wy))
            if len(pts) >= 2:
                pygame.draw.lines(surface, (80, 255, 195), False, pts, 2)
            pygame.draw.rect(surface, (28, 34, 44), housing, 2, border_radius=5)

        elif oid == "market_ledger":
            # Vintage Brass Cash Register & Hardware Ledger
            reg = pygame.Rect(sx - 16, sy - 24 + bob, 32, 24)
            pygame.draw.rect(surface, (218, 168, 62), reg, border_radius=4)
            pygame.draw.rect(surface, (245, 242, 230), (sx - 11, sy - 20 + bob, 22, 8), border_radius=2)
            pygame.draw.rect(surface, (58, 42, 18), reg, 2, border_radius=4)

        elif oid == "office_records" or oid == "police_dispatch":
            # 2.5D Security Mainframe Terminal with Blinking Status LEDs
            mon = pygame.Rect(sx - 17, sy - 26 + bob, 34, 24)
            pygame.draw.rect(surface, (72, 84, 102), mon, border_radius=4)
            scr = mon.inflate(-8, -8)
            pygame.draw.rect(surface, (22, 48, 76), scr, border_radius=2)
            pygame.draw.line(surface, col, (scr.left + 3, scr.top + 4), (scr.right - 5, scr.top + 4), 2)
            pygame.draw.line(surface, (255, 215, 75), (scr.left + 3, scr.top + 9), (scr.right - 9, scr.top + 9), 2)
            pygame.draw.rect(surface, (28, 34, 44), mon, 2, border_radius=4)

        elif oid == "power_generator":
            # Glowing Aether-Core Master Control Console Pedestal
            ped = pygame.Rect(sx - 18, sy - 26 + bob, 36, 26)
            pygame.draw.rect(surface, (62, 42, 48), ped, border_radius=5)
            pygame.draw.circle(surface, (255, 85, 85), (sx - 6, sy - 13 + bob), 5)
            pygame.draw.circle(surface, (85, 245, 155), (sx + 7, sy - 13 + bob), 5)
            pygame.draw.rect(surface, (255, 195, 75), ped, 2, border_radius=5)
