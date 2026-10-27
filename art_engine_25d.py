"""
Octopath Traveler HD-2D & Real 3D-to-2.5D Isometric/Angle Environment Engine (art_engine_25d.py)
Tailored for CHRONICLES OF DUNWICK: DEFYING FATE (1924) — Medieval-Steampunk British Borough:
1. TRUE 2.5D OVERWORLD EXTERIOR HOUSES vs. DEDICATED INTERIOR ROOM SCENES:
   - Overworld (`active_scene == "OVERWORLD"`): Renders a true 2.5D village with 6 towering, multi-story
     3D-shaded Tudor/Victorian/Steampunk exterior houses (`assets/hd2d_sprites/houses/house_*.png`),
     landscaped stone-walled estate courtyards, cobblestone streets, brass tramways, trees, and gaslamps.
   - Interior Scenes (`active_scene == building_id`): When the player enters a house, the scene changes
     to a dedicated Octopath-style 2.5D cutaway interior room surrounded by a deep atmospheric void,
     showing 3D Kenney stone/bookcase walls, wood/flagstone floors, woven rugs, furniture, interactive
     stations, and ONLY the people currently inside that building.
2. Implements an Octopath Traveler HD-2D Post-Processing & Dynamic Point-Lighting Pipeline:
   - Real-time multiplicative ambient shadow map (`BLEND_RGB_MULT`) with warm gaslamp light pools,
     building window light spills, player lantern aura, and cyan Aether-Boiler glow.
   - Real-time additive bloom, diagonal volumetric sunbeams / god-rays, and floating coal-ash/ember motes.
   - Cinematic top/bottom Tilt-Shift Depth-of-Field darkening & radial corner vignette.
"""

import math
import os
import random
import pygame
from config import BUILDINGS, COLORS, SCREEN_HEIGHT, SCREEN_WIDTH, WORLD_HEIGHT, WORLD_WIDTH


INTERIOR_PAD = 90  # Extra pixel margin around each interior room surface for 3D walls & roof headers


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
    Pre-renders and animates both the HD-2D Overworld (with real 2.5D exterior houses) and the
    6 Dedicated 2.5D Cutaway Interior Room Scenes for Dunwick-on-Severn (1924).
    """

    def __init__(self, assets_dir: str):
        self.assets_dir = assets_dir
        self.hd2d_dir = os.path.join(assets_dir, "hd2d_sprites")
        self.portraits_cache: dict[str, pygame.Surface] = {}
        self.sprites: dict[str, pygame.Surface] = {}
        self.house_sprites: dict[str, pygame.Surface] = {}

        self._load_hd2d_sprite_library()

        # Pre-baked 3D-textured Cobblestone, Sandstone Flagstone, Wood Planks & Severn Moor Grass tiles
        self.cobble_tile = self._make_3d_textured_tile(
            "stone_tile", (128, 102), tint_mult=(118, 122, 132), tint_add=(8, 10, 14)
        )
        self.sidewalk_tile = self._make_3d_textured_tile(
            "stone_slab", (128, 102), tint_mult=(186, 174, 156), tint_add=(14, 12, 8)
        )
        self.courtyard_tile = self._make_3d_textured_tile(
            "stone_inset", (128, 102), tint_mult=(142, 136, 126), tint_add=(6, 6, 8)
        )
        self.wood_floor_tile = self._make_3d_textured_tile(
            "wood_planks", (128, 96), tint_mult=(188, 148, 108), tint_add=(12, 8, 4)
        )
        self.stone_floor_tile = self._make_3d_textured_tile(
            "stone_inset", (128, 102), tint_mult=(176, 166, 152), tint_add=(10, 8, 6)
        )
        self.grass_tile = self._make_hd2d_moor_grass_tile(160, 160)

        # Tree, Barrel, Crate & Patio sprites from pre-rendered 3D library
        self.tree_sprite = self.get_sprite("tree_hd2d", (118, 136)) or self._bake_fallback_tree()
        self.barrel_sprite = self.get_sprite("barrel_single", (46, 52))
        self.barrels_stack_sprite = self.get_sprite("barrels_stacked", (96, 64))
        self.crate_sprite = self.get_sprite("crates_group", (68, 56))
        self.patio_table_sprite = self.get_sprite("iso_table_round", (84, 74))
        self.candle_lamp_sprite = self.get_sprite("candle_double", (52, 64))

        # 1. Pre-bake the Pure Outdoor 2.5D Overworld Ground Canvas (2600 x 1800)
        self.world_ground_surface = pygame.Surface((WORLD_WIDTH, WORLD_HEIGHT))
        self._bake_overworld_ground()

        # 2. Pre-bake the 6 Dedicated 2.5D Cutaway Interior Room Surfaces (`interior_room_surfaces[bid]`)
        self.interior_room_surfaces: dict[str, pygame.Surface] = {}
        self._bake_all_interior_rooms()

        # Ambient 1920s British Steampunk outdoor street props (gaslamps, stacked casks, crates, patio tables)
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

    def _load_hd2d_sprite_library(self):
        for sub in ("props", "tiles", "vehicles"):
            folder = os.path.join(self.hd2d_dir, sub)
            if not os.path.exists(folder):
                continue
            for fn in os.listdir(folder):
                if fn.endswith(".png"):
                    key = fn[:-4]
                    try:
                        self.sprites[key] = pygame.image.load(os.path.join(folder, fn)).convert_alpha()
                    except Exception:
                        pass

        houses_folder = os.path.join(self.hd2d_dir, "houses")
        if os.path.exists(houses_folder):
            for fn in os.listdir(houses_folder):
                if fn.startswith("house_") and fn.endswith(".png"):
                    bid = fn[len("house_") : -4]
                    try:
                        self.house_sprites[bid] = pygame.image.load(
                            os.path.join(houses_folder, fn)
                        ).convert_alpha()
                    except Exception:
                        pass

    def get_sprite(self, key: str, size: tuple[int, int] | None = None) -> pygame.Surface | None:
        if size is not None:
            ckey = f"{key}_{size[0]}x{size[1]}"
            if ckey in self.sprites:
                return self.sprites[ckey]
            base = self.sprites.get(key)
            if base is not None:
                scaled = pygame.transform.smoothscale(base, size)
                self.sprites[ckey] = scaled
                return scaled
            return None
        return self.sprites.get(key)

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

    def _make_3d_textured_tile(
        self,
        sprite_key: str,
        size: tuple[int, int],
        tint_mult: tuple[int, int, int] = (255, 255, 255),
        tint_add: tuple[int, int, int] = (0, 0, 0),
    ) -> pygame.Surface:
        w, h = size
        surf = pygame.Surface((w, h))
        surf.fill(_shade(tint_mult, 0.55))
        spr = self.get_sprite(sprite_key, (w, h))
        if spr is not None:
            surf.blit(spr, (0, 0))
            if tint_mult != (255, 255, 255):
                mult_s = pygame.Surface((w, h))
                mult_s.fill(tint_mult)
                surf.blit(mult_s, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
            if tint_add != (0, 0, 0):
                add_s = pygame.Surface((w, h))
                add_s.fill(tint_add)
                surf.blit(add_s, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        return surf

    def _make_hd2d_moor_grass_tile(self, w: int, h: int) -> pygame.Surface:
        """Creates a rich, moody Octopath-style dark-emerald & moss moorland terrain tile."""
        surf = pygame.Surface((w, h))
        base = (38, 62, 42)
        surf.fill(base)

        dirt_spr = self.get_sprite("dirt_tiles", (w, h))
        if dirt_spr is not None:
            temp = pygame.Surface((w, h))
            temp.fill((58, 92, 62))
            temp.blit(dirt_spr, (0, 0))
            mult = pygame.Surface((w, h))
            mult.fill((72, 118, 76))
            temp.blit(mult, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
            surf.blit(temp, (0, 0))

        rng = random.Random(101)
        for _ in range(120):
            gx = rng.randint(2, w - 6)
            gy = rng.randint(2, h - 6)
            patch_col = _shade(base, rng.uniform(0.78, 1.24))
            pygame.draw.circle(surf, patch_col, (gx, gy), rng.randint(2, 5))
        for _ in range(55):
            bx = rng.randint(4, w - 6)
            by = rng.randint(6, h - 6)
            blade_col = (26, 48, 30) if rng.random() < 0.5 else (64, 98, 56)
            pygame.draw.line(surf, blade_col, (bx, by), (bx - 2, by - 4), 1)
            pygame.draw.line(surf, blade_col, (bx, by), (bx + 2, by - 5), 1)
            if rng.random() < 0.16:
                fcol = rng.choice([(218, 178, 72), (178, 76, 76), (195, 190, 178)])
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

    # =========================================================================
    # 1. OVERWORLD OUTDOOR GROUND & ESTATE COURTYARDS (NO 2D BOX ROOMS!)
    # =========================================================================
    def _bake_overworld_ground(self):
        surf = self.world_ground_surface

        # A. Severn Moorland Greensward (Moody HD-2D Forest Floor)
        self._tile_fill_rect(surf, self.grass_tile, pygame.Rect(0, 0, WORLD_WIDTH, WORLD_HEIGHT))

        # B. Medieval Sandstone Flagstone Pavements, Plazas & Wynds
        sidewalk_rects = [
            pygame.Rect(0, 740, WORLD_WIDTH, 280),
            pygame.Rect(785, 0, 170, WORLD_HEIGHT),
            pygame.Rect(1625, 0, 170, WORLD_HEIGHT),
        ]
        for sr in sidewalk_rects:
            self._tile_fill_rect(surf, self.sidewalk_tile, sr)
            pygame.draw.rect(surf, (44, 38, 32), sr, 4)

        # C. Landscaped Outdoor Estate Grounds & Stone Perimeter Courtyards for the 6 Houses
        for b in BUILDINGS:
            self._bake_overworld_estate_lot(surf, b)

        # D. 3D Cobblestone High Street & Brass Steam-Tramway Rails
        road_rects = [
            pygame.Rect(0, 802, WORLD_WIDTH, 156),
            pygame.Rect(822, 0, 96, WORLD_HEIGHT),
            pygame.Rect(1662, 0, 96, WORLD_HEIGHT),
        ]
        for rr in road_rects:
            self._tile_fill_rect(surf, self.cobble_tile, rr)
            pygame.draw.line(surf, (176, 166, 148), (rr.left, rr.top), (rr.right, rr.top), 3)
            pygame.draw.line(surf, (24, 22, 20), (rr.left, rr.top + 3), (rr.right, rr.top + 3), 3)
            pygame.draw.line(surf, (22, 20, 18), (rr.left, rr.bottom), (rr.right, rr.bottom), 4)

        # Scatter `space-lab-76` floor wear decals (`dirt_1..3.png`) & broadsheets along High Street
        rng_wear = random.Random(1924)
        for _ in range(42):
            wkey = rng_wear.choice(["wear_dirt_1", "wear_dirt_2", "wear_dirt_3"])
            wspr = self.get_sprite(wkey)
            if wspr is not None:
                wx = rng_wear.randint(40, WORLD_WIDTH - 120)
                wy = rng_wear.randint(752, 990)
                surf.blit(wspr, (wx, wy))
        paper_spr = self.get_sprite("paper_clutter", (28, 22))
        if paper_spr is not None:
            for px, py in [(480, 765), (950, 980), (1380, 768), (1850, 975), (2210, 770)]:
                surf.blit(paper_spr, (px, py))

        # Recessed Brass & Iron Steam-Tramway Rails + Wooden Sleepers along High Street
        for sx_tie in range(8, WORLD_WIDTH, 22):
            pygame.draw.rect(surf, (46, 34, 24), (sx_tie, 831, 8, 23), border_radius=1)
            pygame.draw.rect(surf, (46, 34, 24), (sx_tie, 907, 8, 23), border_radius=1)
        for rail_y in (834, 850, 910, 926):
            pygame.draw.line(surf, (32, 28, 24), (0, rail_y + 2), (WORLD_WIDTH, rail_y + 2), 3)
            pygame.draw.line(surf, (192, 154, 78), (0, rail_y), (WORLD_WIDTH, rail_y), 2)

        # Center Brass Crown Road Studs
        for rx in range(50, WORLD_WIDTH, 90):
            stud = pygame.Rect(rx, 876, 42, 6)
            pygame.draw.rect(surf, (218, 174, 78), stud, border_radius=3)
            pygame.draw.rect(surf, (48, 36, 18), stud, 1, border_radius=3)

        # 3D Stone Slab Crosswalks (`step_stone.png`)
        step_spr = self.get_sprite("step_stone", (78, 22))
        for cw_x in (450, 1290, 2140):
            for sy in range(808, 952, 24):
                if step_spr is not None:
                    surf.blit(step_spr, (cw_x - 39, sy))
                else:
                    stone = pygame.Rect(cw_x - 38, sy, 76, 16)
                    pygame.draw.rect(surf, (188, 178, 162), stone, border_radius=3)

    def _bake_overworld_estate_lot(self, surf: pygame.Surface, b: dict):
        """
        Renders an outdoor Victorian/Tudor landscaped estate lot for each building on the Overworld:
        - Hedged & stone-walled garden courtyard (instead of an indoor floorplan!)
        - Cobblestone front forecourt & stone threshold steps leading to the 2.5D house's front door.
        """
        rx, ry, rw, rh = b["rect"]
        door_x, door_y = b["door_x"], b["door_y"]
        is_north = door_y > ry + rh // 2

        # Soft ambient shadow around the estate lot
        for expand, alpha in [(20, 45), (10, 90)]:
            sh_s = pygame.Surface((rw + expand * 2, rh + expand * 2), pygame.SRCALPHA)
            pygame.draw.rect(sh_s, (6, 8, 12, alpha), sh_s.get_rect(), border_radius=18)
            surf.blit(sh_s, (rx - expand + 6, ry - expand + 10))

        # Flagstone forecourt apron around the front entrance & cobblestone walkway
        if is_north:
            # North-row estate: house sits near the South edge (`y = 740`), garden behind it
            apron = pygame.Rect(rx + 28, ry + rh - 170, rw - 56, 170)
            self._tile_fill_rect(surf, self.courtyard_tile, apron)
            pygame.draw.rect(surf, (42, 38, 34), apron, 3, border_radius=8)
        else:
            # South-row estate: cobblestone avenue from the North gate (`y = 1020`) to the house & South garden
            apron = pygame.Rect(rx + 28, ry, rw - 56, 410)
            self._tile_fill_rect(surf, self.courtyard_tile, apron)
            pygame.draw.rect(surf, (42, 38, 34), apron, 3, border_radius=8)
            walkway = pygame.Rect(door_x - 64, ry, 128, rh - 60)
            self._tile_fill_rect(surf, self.sidewalk_tile, walkway)
            pygame.draw.rect(surf, (46, 40, 34), walkway, 2)

        # Low 3D Kenney Stone Garden Walls & Wrought-Iron Estate Fencing around the lot perimeter
        w_half = self.get_sprite("wall_half", (96, 32))
        col_spr = self.get_sprite("column_stone", (26, 68))

        # Wrought-iron & stone border frame
        border_r = pygame.Rect(rx + 6, ry + 6, rw - 12, rh - 12)
        pygame.draw.rect(surf, (32, 36, 42), border_r, 6, border_radius=10)
        pygame.draw.rect(surf, (158, 146, 128), border_r, 2, border_radius=10)

        # Topiary hedges inside the garden corners
        rng = random.Random( hash(b["id"]) & 0xFFFF )
        for hx in range(rx + 36, rx + rw - 36, 52):
            for hy in (ry + 28, ry + rh - 32):
                if abs(hx - door_x) < 95:
                    continue
                pygame.draw.circle(surf, (22, 42, 26), (hx + 3, hy + 4), 16)
                pygame.draw.circle(surf, (42, 78, 46), (hx, hy), 15)
                pygame.draw.circle(surf, (68, 112, 64), (hx - 3, hy - 3), 8)

        if w_half is not None:
            wall_y = (ry + rh - 24) if is_north else (ry - 6)
            for wx in range(rx + 16, rx + rw - 32, 88):
                if abs((wx + 44) - door_x) < 96:
                    continue
                cur_w = min(88, rx + rw - 16 - wx)
                surf.blit(w_half, (wx, wall_y), pygame.Rect(0, 0, cur_w, 32))

        if col_spr is not None:
            for cx_pos in (rx, rx + rw - 26, door_x - 86, door_x + 60):
                surf.blit(col_spr, (cx_pos, (ry + rh - 56) if is_north else (ry - 28)))

        # Grand Stone Threshold Steps at `(door_x, door_y)`
        step_spr = self.get_sprite("step_stone", (136, 30))
        if step_spr is not None:
            surf.blit(step_spr, (door_x - 68, door_y - 15))

    def get_house_overworld_placement(self, b: dict) -> tuple[int, int, int, int, tuple[int, int]]:
        """
        Returns `(blit_x, blit_y, spr_w, spr_h, (door_trigger_x, door_trigger_y))` for a 2.5D exterior house
        on the Overworld.
        - North-row houses (`home`, `cafe`, `office`): Front steps & oak door sit directly at `(door_x, 742)`
          facing High Street.
        - South-row houses (`school`, `market`, `park`): The towering 2.5D building rises immediately south
          of High Street (`y = 1018..1395`), with a grand High Street entrance portal at `(door_x, 1020)` AND
          south courtyard steps at `(door_x, 1385)`.
        """
        rx, ry, rw, rh = b["rect"]
        bid = b["id"]
        door_x, door_y = b["door_x"], b["door_y"]
        spr = self.house_sprites.get(bid)
        sw = spr.get_width() if spr else 580
        sh = spr.get_height() if spr else 360

        is_north = door_y > ry + rh // 2
        if is_north:
            # Front base of the house sits right along the North sidewalk (`y = 746`)
            blit_x = door_x - sw // 2
            blit_y = door_y - sh + 12
            return (blit_x, blit_y, sw, sh, (door_x, door_y))
        else:
            # South-row house sits on the northern half of the estate (`y = 1015 .. 1015 + sh`)
            blit_x = door_x - sw // 2
            blit_y = ry + 4
            return (blit_x, blit_y, sw, sh, (door_x, door_y))

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
        Renders the towering 3D-shaded 2.5D Exterior House sprite (`house_{bid}.png`) on the Overworld,
        complete with animated chimney coal-smoke, glowing doorway lantern beacon, hanging guild signboard,
        and a live occupancy indicator showing who is currently inside the building!
        """
        bid = b["id"]
        spr = self.house_sprites.get(bid)
        if spr is None:
            return

        bx, by, sw, sh, (dx, dy) = self.get_house_overworld_placement(b)
        sx = int(bx - cam_x)
        sy = int(by - cam_y)

        if sx + sw < -120 or sx > surface.get_width() + 120 or sy + sh < -120 or sy > surface.get_height() + 120:
            return

        # 1. Blit the towering 2.5D Exterior House Sprite
        surface.blit(spr, (sx, sy))

        # 2. Animated Steampunk Chimney Coal-Smoke Plumes rising from the house roof
        for c_off in (int(sw * 0.22), int(sw * 0.78)):
            for p_i in range(3):
                age = (t_sec * 1.4 + p_i * 0.9 + c_off * 0.01) % 2.7
                puff_x = sx + c_off + int(math.sin(t_sec * 1.8 + p_i) * 8 + age * 10)
                puff_y = sy + 18 - int(age * 22)
                rad = int(6 + age * 5)
                alpha = max(0, min(115, int(115 * (1.0 - age / 2.7))))
                if alpha > 8:
                    p_surf = pygame.Surface((rad * 2 + 2, rad * 2 + 2), pygame.SRCALPHA)
                    pygame.draw.circle(p_surf, (212, 208, 202, alpha), (rad + 1, rad + 1), rad)
                    surface.blit(p_surf, (puff_x - rad, puff_y - rad))

        # 3. For South-row houses, also render a grand 3D Stone Entrance Archway at `(door_x, 1020)` facing High Street
        door_sx = int(dx - cam_x)
        door_sy = int(dy - cam_y)
        is_north = dy > b["rect"][1] + b["rect"][3] // 2
        if not is_north:
            arch_spr = self.get_sprite("wall_archway", (142, 74))
            if arch_spr is not None:
                surface.blit(arch_spr, (door_sx - 71, door_sy - 56))

        # 4. Glowing Interactive Doorway Threshold Beacon on the Overworld
        pulse = int(6 + math.sin(t_sec * 5.0) * 4)
        ring_w = 68 + pulse
        ring_s = pygame.Surface((ring_w * 2, 36), pygame.SRCALPHA)
        ring_col = (95, 242, 168) if player_near_door else (255, 208, 92)
        pygame.draw.ellipse(ring_s, (*ring_col, 75 if player_near_door else 42), (4, 4, ring_w * 2 - 8, 28))
        pygame.draw.ellipse(ring_s, (*ring_col, 220), (4, 4, ring_w * 2 - 8, 28), 2)
        surface.blit(ring_s, (door_sx - ring_w, door_sy - 16))

        # 5. Hanging Victorian Brass & Oak Guild Signboard + Live Occupancy Badge
        if font_sm is not None:
            sign_y = (door_sy - 118) if is_north else (door_sy - 72)
            lbl = font_sm.render(b["name"], True, (248, 238, 212))
            sign_w = lbl.get_width() + 28
            sign_rect = pygame.Rect(door_sx - sign_w // 2, sign_y, sign_w, 26)
            pygame.draw.rect(surface, (12, 14, 20), sign_rect.move(0, 3), border_radius=6)
            pygame.draw.rect(surface, (38, 26, 18), sign_rect, border_radius=6)
            pygame.draw.rect(surface, (218, 172, 78), sign_rect, 2, border_radius=6)
            surface.blit(lbl, (door_sx - lbl.get_width() // 2, sign_y + 4))

            # Occupancy pill right below the building sign so the player knows who is inside!
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

    # =========================================================================
    # 2. DEDICATED 2.5D CUTAWAY INTERIOR ROOM SCENES (WHEN INSIDE A HOUSE!)
    # =========================================================================
    def _bake_all_interior_rooms(self):
        for b in BUILDINGS:
            rx, ry, rw, rh = b["rect"]
            surf = pygame.Surface((rw + INTERIOR_PAD * 2, rh + INTERIOR_PAD * 2), pygame.SRCALPHA)
            self._bake_single_interior_room(surf, b, ox=rx - INTERIOR_PAD, oy=ry - INTERIOR_PAD)
            self.interior_room_surfaces[b["id"]] = surf

    def _bake_single_interior_room(self, surf: pygame.Surface, b: dict, ox: int, oy: int):
        """
        Pre-bakes the high-detail Octopath Traveler 2.5D Cutaway Interior Room for building `b`.
        Coordinates are shifted by `(ox, oy)` so world coordinates `(wx, wy)` map to `(wx - ox, wy - oy)`.
        """
        rx, ry, rw, rh = b["rect"]
        lx = rx - ox
        ly = ry - oy
        door_x = b["door_x"] - ox
        door_y = b["door_y"] - oy
        bid = b["id"]
        f_col = b["floor_color"]
        r_col = b["roof_color"]

        # A. Deep Outer Diorama Drop Shadow & Architectural Plinth
        for expand, alpha in [(36, 95), (22, 155), (10, 215)]:
            sh_s = pygame.Surface((rw + expand * 2, rh + expand * 2), pygame.SRCALPHA)
            pygame.draw.rect(sh_s, (4, 6, 12, alpha), sh_s.get_rect(), border_radius=16)
            surf.blit(sh_s, (lx - expand, ly - expand + 12))

        # Thick 3D Cutaway Stone Foundation Skirt along the bottom of the diorama box
        plinth_rect = pygame.Rect(lx - 8, ly + rh - 6, rw + 16, 38)
        pygame.draw.rect(surf, (36, 32, 28), plinth_rect, border_radius=6)
        pygame.draw.rect(surf, (18, 16, 14), plinth_rect, 3, border_radius=6)

        # B. 3D-Textured Interior Floors (Polished Tudor Oak Planks or Cut Sandstone Flagstone)
        floor_rect = pygame.Rect(lx, ly, rw, rh)
        if bid == "park":
            # Constabulary Hall & Cloister Sanctuary Floor
            custom_stone = self._make_3d_textured_tile(
                "stone_inset", (128, 102), tint_mult=(154, 162, 152), tint_add=(8, 10, 8)
            )
            self._tile_fill_rect(surf, custom_stone, floor_rect)
            cloister_lawn = pygame.Rect(lx + 310, ly + 210, 320, 340)
            self._tile_fill_rect(surf, self.grass_tile, cloister_lawn)
            pygame.draw.rect(surf, (148, 138, 122), cloister_lawn, 6, border_radius=10)
        elif bid in ("home", "school"):
            custom_wood = self._make_3d_textured_tile(
                "wood_planks", (128, 96), tint_mult=_shade(f_col, 0.96), tint_add=(8, 6, 4)
            )
            self._tile_fill_rect(surf, custom_wood, floor_rect)
        else:
            custom_stone = self._make_3d_textured_tile(
                "stone_inset", (128, 102), tint_mult=_shade(f_col, 0.94), tint_add=(6, 6, 8)
            )
            self._tile_fill_rect(surf, custom_stone, floor_rect)

        # Interior Ambient Occlusion Vignette along all 4 perimeter walls
        ao_top = pygame.Surface((rw, 56), pygame.SRCALPHA)
        for y_ao in range(56):
            pygame.draw.line(ao_top, (8, 6, 12, int(175 * (1.0 - y_ao / 56.0))), (0, y_ao), (rw, y_ao))
        surf.blit(ao_top, (lx, ly + 48))

        # C. Real 3D Woven Carpets (`carpet_main.png` & `carpet_small.png`) + Warm Window Sunbeam Pools
        carpet_spr = self.get_sprite("carpet_main", (260, 96))
        carpet_sm = self.get_sprite("carpet_small", (145, 76))
        if carpet_spr is not None:
            if bid == "home":
                surf.blit(carpet_spr, (lx + 310, ly + 210))
                if carpet_sm:
                    surf.blit(carpet_sm, (lx + 90, ly + 195))
            elif bid == "cafe":
                surf.blit(carpet_spr, (lx + 195, ly + 245))
            elif bid == "school":
                surf.blit(carpet_spr, (lx + 210, ly + 215))
            elif bid == "office" and carpet_sm:
                surf.blit(carpet_sm, (lx + 240, ly + 210))
            elif bid == "market" and carpet_sm:
                surf.blit(carpet_sm, (lx + 250, ly + 260))

        # D. Real 3D Kenney `Angle/` North (Back) Stone Wall, Windows & Bookcase Walls!
        wall_seg_w = 96
        wall_seg_h = 78
        w_stone = self.get_sprite("wall_stone", (wall_seg_w, wall_seg_h))
        w_win = self.get_sprite("wall_window", (wall_seg_w, wall_seg_h))
        w_round = self.get_sprite("wall_round_win", (wall_seg_w, wall_seg_h))
        w_books = self.get_sprite("wall_books", (wall_seg_w, wall_seg_h))
        w_half = self.get_sprite("wall_half", (wall_seg_w, 36))
        col_spr = self.get_sprite("column_stone", (30, 84))

        if w_stone is not None:
            idx = 0
            for wx in range(lx, lx + rw - 16, wall_seg_w - 6):
                cur_w = min(wall_seg_w, lx + rw - wx)
                has_full_bay = cur_w >= wall_seg_w - 8
                if idx % 3 == 1 and has_full_bay and w_win is not None:
                    chosen = w_round if (bid in ("office", "school") and w_round) else w_win
                    pygame.draw.rect(surf, (255, 214, 112), (wx + 24, ly + 12, 48, 36))
                    # Diagonal Golden Window Light Pool on the Interior Floor!
                    beam_s = pygame.Surface((120, 180), pygame.SRCALPHA)
                    pygame.draw.polygon(
                        beam_s,
                        (255, 224, 138, 38),
                        [(20, 0), (76, 0), (116, 175), (4, 175)],
                    )
                    surf.blit(beam_s, (wx + 4, ly + 62))
                elif bid in ("home", "school") and idx % 2 == 0 and has_full_bay and w_books is not None:
                    chosen = w_books
                else:
                    chosen = w_stone
                surf.blit(chosen, (wx, ly - 10), pygame.Rect(0, 0, cur_w, wall_seg_h))
                idx += 1

        # E. Interior North-Wall 3D Props (Bookcases, Lab Tape Reels/Terminals, Stacked Casks)
        if bid == "home":
            bc_spr = self.get_sprite("bookcase_wide", (98, 84))
            bc_glass = self.get_sprite("bookcase_glass", (90, 84))
            cand_spr = self.get_sprite("candle_double", (46, 58))
            if bc_spr:
                surf.blit(bc_spr, (lx + 36, ly + 18))
                surf.blit(bc_spr, (lx + rw - 140, ly + 18))
            if bc_glass:
                surf.blit(bc_glass, (lx + 290, ly + 18))
            if cand_spr:
                surf.blit(cand_spr, (lx + 235, ly + 32))
        elif bid == "school":
            bc_lad = self.get_sprite("bookcase_ladder", (100, 86))
            bc_wide = self.get_sprite("bookcase_wide", (98, 84))
            if bc_lad:
                surf.blit(bc_lad, (lx + 42, ly + 20))
            if bc_wide:
                surf.blit(bc_wide, (lx + 150, ly + 20))
                surf.blit(bc_wide, (lx + rw - 135, ly + 20))
        elif bid == "office":
            for lx_p, lkey in [
                (lx + 48, "lab_tape_reel"),
                (lx + 135, "lab_blue_comp"),
                (lx + 230, "lab_desk_pc"),
                (lx + rw - 190, "lab_red_comp"),
                (lx + rw - 105, "lab_tape_reel"),
            ]:
                lspr = self.get_sprite(lkey, (50, 78))
                if lspr:
                    surf.blit(lspr, (lx_p, ly + 16))
        elif bid in ("cafe", "market"):
            bs_spr = self.get_sprite("barrels_stacked", (94, 64))
            cr_spr = self.get_sprite("crates_group", (70, 58))
            if bs_spr:
                surf.blit(bs_spr, (lx + 28, ly + 28))
            if cr_spr:
                surf.blit(cr_spr, (lx + rw - 105, ly + 32))
        elif bid == "park":
            bc_spr = self.get_sprite("bookcase_glass", (90, 84))
            comp_spr = self.get_sprite("lab_blue_comp", (50, 78))
            if bc_spr:
                surf.blit(bc_spr, (lx + 44, ly + 18))
            if comp_spr:
                surf.blit(comp_spr, (lx + 152, ly + 18))

        # F. Cutaway Perimeter Stone Walls, Brass Steam-Pipes & Exit Doorway Arch
        pygame.draw.rect(surf, (96, 86, 74), floor_rect, 14, border_radius=6)
        pygame.draw.rect(surf, (24, 18, 14), floor_rect, 3, border_radius=6)

        if w_half is not None:
            for wx in range(lx + 12, lx + rw - 24, wall_seg_w - 8):
                if abs((wx + wall_seg_w // 2) - door_x) < 92 and abs(door_y - (ly + rh)) < 45:
                    continue
                cur_w = min(wall_seg_w, lx + rw - 12 - wx)
                surf.blit(w_half, (wx, ly + rh - 28), pygame.Rect(0, 0, cur_w, 36))

        if col_spr is not None:
            for cx_pos in (lx - 6, lx + rw - 24):
                surf.blit(col_spr, (cx_pos, ly - 14))
                surf.blit(col_spr, (cx_pos, ly + rh - 68))

        # Steampunk Brass Pipeline along West & East interior cutaway walls
        pygame.draw.line(surf, (42, 30, 16), (lx + 14, ly + 64), (lx + 14, ly + rh - 18), 6)
        pygame.draw.line(surf, (214, 164, 72), (lx + 14, ly + 64), (lx + 14, ly + rh - 18), 3)
        pygame.draw.line(surf, (42, 30, 16), (lx + rw - 14, ly + 64), (lx + rw - 14, ly + rh - 18), 6)
        pygame.draw.line(surf, (214, 164, 72), (lx + rw - 14, ly + 64), (lx + rw - 14, ly + rh - 18), 3)

        # Cutaway Roof Header Beam at Top of Interior Room
        roof_rect = pygame.Rect(lx - 8, ly - 20, rw + 16, 28)
        pygame.draw.rect(surf, _shade(r_col, 0.78), roof_rect, border_radius=8)
        pygame.draw.rect(surf, (214, 168, 74), roof_rect, 2, border_radius=8)

        # G. Interior Exit Door Threshold & Welcome Mat at `(door_x, door_y)`
        step_spr = self.get_sprite("step_stone", (136, 30))
        arch_spr = self.get_sprite("wall_archway", (144, 72))
        col_wood = self.get_sprite("column_wood", (26, 66))

        # Crimson & Gold Woven Exit Mat inside the doorway
        mat_y = (door_y - 44) if door_y > ly + rh // 2 else (door_y + 12)
        mat_rect = pygame.Rect(door_x - 56, mat_y, 112, 32)
        pygame.draw.rect(surf, (138, 38, 42), mat_rect, border_radius=5)
        pygame.draw.rect(surf, (218, 174, 74), mat_rect, 2, border_radius=5)

        if step_spr is not None:
            surf.blit(step_spr, (door_x - 68, door_y - 15))
        if abs(door_y - ly) < 35 and arch_spr is not None:
            surf.blit(arch_spr, (door_x - 72, door_y - 46))
        elif col_wood is not None:
            surf.blit(col_wood, (door_x - 76, door_y - 52))
            surf.blit(col_wood, (door_x + 50, door_y - 52))

    def _bake_fallback_tree(self) -> pygame.Surface:
        surf = pygame.Surface((96, 112), pygame.SRCALPHA)
        pygame.draw.circle(surf, (38, 76, 42), (48, 42), 34)
        return surf

    def draw_street_prop(
        self, surface: pygame.Surface, ptype: str, wx: float, wy: float, cam_x: float, cam_y: float, t_sec: float
    ):
        sx = int(wx - cam_x)
        sy = int(wy - cam_y)
        if ptype == "barrel":
            if self.barrel_sprite:
                surface.blit(self.barrel_sprite, (sx - 23, sy - 44))
        elif ptype == "crate":
            if self.crate_sprite:
                surface.blit(self.crate_sprite, (sx - 34, sy - 46))
        elif ptype == "flower_cart":
            if self.patio_table_sprite:
                surface.blit(self.patio_table_sprite, (sx - 42, sy - 58))
        elif ptype == "lamp":
            pygame.draw.ellipse(surface, (10, 12, 16), (sx - 14, sy - 5, 28, 10))
            if self.candle_lamp_sprite:
                surface.blit(self.candle_lamp_sprite, (sx - 26, sy - 60))
            pygame.draw.rect(surface, (32, 36, 44), (sx - 3, sy - 64, 6, 60), border_radius=2)
            pygame.draw.rect(surface, (214, 168, 74), (sx - 7, sy - 12, 14, 8), border_radius=2)
            lantern = pygame.Rect(sx - 10, sy - 78, 20, 18)
            pygame.draw.rect(surface, (255, 224, 128), lantern, border_radius=4)
            pygame.draw.rect(surface, (214, 168, 74), lantern, 2, border_radius=4)
            pygame.draw.polygon(surface, (28, 32, 38), [(sx - 12, sy - 78), (sx, sy - 88), (sx + 12, sy - 78)])
            glow_r = int(32 + math.sin(t_sec * 3.8 + wx * 0.01) * 4)
            glow_s = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
            pygame.draw.circle(glow_s, (255, 204, 88, 62), (glow_r, glow_r), glow_r)
            pygame.draw.circle(glow_s, (255, 238, 168, 95), (glow_r, glow_r), glow_r // 2)
            surface.blit(glow_s, (sx - glow_r, sy - 70 - glow_r))

    def draw_25d_furniture(self, surface: pygame.Surface, f: dict, cam_x: float, cam_y: float, t_sec: float):
        fx, fy, fw, fh = f["rect"]
        sx = int(fx - cam_x)
        sy = int(fy - cam_y)
        name = f["name"]
        base_col = f["color"]

        if sx + fw < -120 or sx > surface.get_width() + 120 or sy + fh < -120 or sy > surface.get_height() + 120:
            return

        # 1. Medieval Gargoyle Fountain in Severn Commons
        if "Fountain" in name:
            cx, cy = sx + fw // 2, sy + fh // 2
            rx_outer = fw // 2
            pygame.draw.circle(surface, (14, 18, 22), (cx + 6, cy + 8), rx_outer + 2)
            pygame.draw.circle(surface, (124, 118, 110), (cx, cy), rx_outer)
            pygame.draw.circle(surface, (168, 160, 148), (cx, cy - 3), rx_outer - 5)
            pygame.draw.circle(surface, (38, 34, 30), (cx, cy), rx_outer, 3)
            pygame.draw.circle(surface, (34, 108, 148), (cx, cy), rx_outer - 14)
            for ring_i in range(3):
                r_wave = int(((t_sec * 26.0 + ring_i * 24) % (rx_outer - 18)))
                pygame.draw.circle(surface, (128, 212, 242), (cx, cy), max(6, r_wave), 2)
            col_spr = self.get_sprite("column_stone", (38, 76))
            if col_spr:
                surface.blit(col_spr, (cx - 19, cy - 58))
            spray_h = int(12 + math.sin(t_sec * 8.0) * 4)
            pygame.draw.circle(surface, (205, 245, 255), (cx, cy - 56 - spray_h // 2), 7)
            for ang in (-0.8, -0.4, 0.0, 0.4, 0.8):
                px = int(cx + math.sin(ang) * 20)
                py = int(cy - 34 + abs(ang) * 16)
                pygame.draw.line(surface, (175, 238, 255), (cx, cy - 56), (px, py), 2)
            return

        # 2. Imperial Aether-Boiler & Clocktower Generator
        if "Generator" in name or "Boiler" in name:
            plat = pygame.Rect(sx, sy, fw, fh)
            pygame.draw.rect(surface, (12, 14, 18), plat.move(10, 12), border_radius=12)
            step_spr = self.get_sprite("stone_slab", (fw, fh))
            if step_spr:
                surface.blit(step_spr, (sx, sy))
            pygame.draw.rect(surface, (44, 40, 36), plat, 6, border_radius=10)
            pygame.draw.rect(surface, (214, 164, 68), plat, 2, border_radius=10)

            col_spr = self.get_sprite("column_stone", (32, 82))
            if col_spr:
                surface.blit(col_spr, (sx + 6, sy - 24))
                surface.blit(col_spr, (sx + fw - 38, sy - 24))

            for coil_x in (sx + 26, sx + fw - 68):
                for cy_off in range(sy + 42, sy + fh - 46, 34):
                    c_rect = pygame.Rect(coil_x, cy_off, 42, 24)
                    pygame.draw.rect(surface, (194, 114, 58), c_rect, border_radius=6)
                    pygame.draw.line(
                        surface,
                        (246, 188, 122),
                        (c_rect.left + 4, c_rect.top + 4),
                        (c_rect.right - 4, c_rect.top + 4),
                        2,
                    )
                    pygame.draw.rect(surface, (36, 22, 14), c_rect, 2, border_radius=6)

            core_rect = pygame.Rect(sx + 78, sy + 26, fw - 156, fh - 58)
            pygame.draw.rect(surface, (18, 24, 34), core_rect, border_radius=14)
            pulse = 0.5 + 0.5 * math.sin(t_sec * 6.0)
            plasma_col = _clamp_rgb(75 + pulse * 105, 198 + pulse * 48, 255)
            inner_core = core_rect.inflate(-16, -16)
            pygame.draw.rect(surface, plasma_col, inner_core, border_radius=10)

            cog_cx, cog_cy = core_rect.centerx, core_rect.centery
            pygame.draw.circle(surface, (224, 178, 74), (cog_cx, cog_cy), 26, 5)
            pygame.draw.circle(surface, (38, 28, 18), (cog_cx, cog_cy), 11)
            for tooth_i in range(8):
                ang = t_sec * 2.0 + tooth_i * (math.tau / 8)
                tx1 = int(cog_cx + math.cos(ang) * 19)
                ty1 = int(cog_cy + math.sin(ang) * 19)
                tx2 = int(cog_cx + math.cos(ang) * 30)
                ty2 = int(cog_cy + math.sin(ang) * 30)
                pygame.draw.line(surface, (228, 184, 78), (tx1, ty1), (tx2, ty2), 4)

            pygame.draw.rect(surface, (218, 168, 68), core_rect, 4, border_radius=14)
            return

        # 3. St. Dunstan's Fencing & Athletics Yard
        if "Gym Court" in name:
            court = pygame.Rect(sx, sy, fw, fh)
            pygame.draw.rect(surface, (82, 64, 46), court, border_radius=6)
            pygame.draw.rect(surface, (214, 198, 168), court.inflate(-12, -12), 2, border_radius=4)
            pygame.draw.circle(surface, (214, 198, 168), court.center, 36, 2)
            pygame.draw.line(
                surface, (214, 198, 168), (court.centerx, court.top + 6), (court.centerx, court.bottom - 6), 2
            )
            return

        # 4. Teahouse / Lecture / Study Tables
        if "Table" in name or "Lecture" in name or "Desk" in name:
            if "Teahouse" in name:
                t_spr = self.get_sprite("table_round_items", (min(138, fw + 16), min(118, fh + 28)))
                if t_spr:
                    surface.blit(t_spr, (sx + (fw - t_spr.get_width()) // 2, sy - 14))
                    pygame.draw.circle(surface, (238, 182, 82), (sx + fw // 2 + 12, sy + fh // 2 - 4), 7)
                    pygame.draw.circle(surface, (48, 32, 18), (sx + fw // 2 + 12, sy + fh // 2 - 4), 7, 1)
                    return
            else:
                lt_spr = self.get_sprite("long_table_books", (fw + 18, fh + 32))
                if lt_spr:
                    surface.blit(lt_spr, (sx - 9, sy - 18))
                    return

        # 5. Chesterfield Parlour Sofa
        if "Sofa" in name:
            pygame.draw.rect(surface, (14, 14, 18), (sx + 6, sy + 10, fw, fh), border_radius=8)
            back = pygame.Rect(sx, sy, fw, 26)
            pygame.draw.rect(surface, _shade(base_col, 0.72), back, border_radius=8)
            pygame.draw.rect(surface, (214, 168, 72), back, 2, border_radius=8)
            c_w = (fw - 36) // 3
            for i in range(3):
                cush = pygame.Rect(sx + 18 + i * c_w, sy + 20, c_w - 2, fh - 24)
                pygame.draw.rect(surface, _shade(base_col, 0.92), cush, border_radius=6)
                pygame.draw.rect(surface, (32, 18, 22), cush, 2, border_radius=6)
            for ax in (sx, sx + fw - 20):
                arm = pygame.Rect(ax, sy + 10, 20, fh - 10)
                pygame.draw.rect(surface, _shade(base_col, 0.82), arm, border_radius=6)
                pygame.draw.rect(surface, (214, 168, 72), arm, 1, border_radius=6)
            return

        # 6. Guildhall Market Display Cases, Galvanic Lab Benches & Apothecary Counters
        if "Stall" in name:
            disp_key = "display_sword" if (fx // 100) % 2 == 0 else "display_books"
            d_spr = self.get_sprite(disp_key, (fw + 12, fh + 26))
            if d_spr:
                surface.blit(d_spr, (sx - 6, sy - 16))
                return
        elif "Galvanic" in name or "Apothecary" in name or "Difference" in name or "Records" in name:
            lt_plain = self.get_sprite("long_table_plain", (fw + 12, fh + 22))
            if lt_plain:
                surface.blit(lt_plain, (sx - 6, sy - 12))
            else:
                pygame.draw.rect(surface, _shade(base_col, 0.8), (sx, sy, fw, fh), border_radius=6)
            comp_spr = self.get_sprite("lab_tan_comp", (38, 52))
            hifi_spr = self.get_sprite("lab_tape_hifi", (38, 52))
            if comp_spr:
                surface.blit(comp_spr, (sx + 18, sy - 18))
            if hifi_spr and fw > 130:
                surface.blit(hifi_spr, (sx + fw - 62, sy - 18))
            for gx in range(sx + 68, sx + fw - 44, 54):
                pygame.draw.circle(surface, (88, 242, 205), (gx, sy + 18), 8)
                pygame.draw.circle(surface, (24, 48, 52), (gx, sy + 18), 8, 2)
            return

        d_open = self.get_sprite("display_open", (fw + 10, fh + 20))
        if d_open:
            surface.blit(d_open, (sx - 5, sy - 12))
        else:
            pygame.draw.rect(surface, base_col, (sx, sy, fw, fh), border_radius=6)

    def draw_quest_object(
        self,
        surface: pygame.Surface,
        wobj: dict,
        cam_x: float,
        cam_y: float,
        t_sec: float,
        is_active_hazard: bool = False,
    ):
        oid = wobj["id"]
        sx = int(wobj["x"] - cam_x)
        sy = int(wobj["y"] - cam_y)
        col = (255, 82, 82) if is_active_hazard else wobj["color"]
        bob = int(math.sin(t_sec * 4.5 + wobj["x"] * 0.02) * 3)

        pulse_r = int((28 if is_active_hazard else 22) + math.sin(t_sec * 6.0) * 3)
        glow_s = pygame.Surface((pulse_r * 2 + 12, 34), pygame.SRCALPHA)
        pygame.draw.ellipse(glow_s, (*col[:3], 68 if is_active_hazard else 42), (6, 4, pulse_r * 2, 24))
        pygame.draw.ellipse(glow_s, (*col[:3], 215), (6, 4, pulse_r * 2, 24), 2)
        surface.blit(glow_s, (sx - pulse_r - 6, sy - 12))

        if oid == "study_notebook":
            stand = self.get_sprite("book_stand", (44, 52))
            if stand:
                surface.blit(stand, (sx - 22, sy - 42 + bob))
            pygame.draw.circle(surface, (238, 192, 78), (sx, sy - 22 + bob), 12, 2)
            orb_x = sx + int(math.cos(t_sec * 3.2) * 10)
            orb_y = sy - 22 + bob + int(math.sin(t_sec * 3.2) * 5)
            pygame.draw.circle(surface, (105, 228, 245), (orb_x, orb_y), 4)

        elif oid == "cafe_counter":
            cup = pygame.Rect(sx - 11, sy - 24 + bob, 22, 20)
            pygame.draw.ellipse(surface, (224, 178, 74), (sx - 15, sy - 8 + bob, 30, 10))
            pygame.draw.rect(surface, (204, 122, 58), cup, border_radius=5)
            pygame.draw.rect(surface, (38, 24, 16), cup, 2, border_radius=5)
            for s_i in range(2):
                st_y = sy - 28 + bob - int((t_sec * 18 + s_i * 7) % 12)
                st_x = sx - 4 + s_i * 8 + int(math.sin(t_sec * 6 + s_i) * 3)
                pygame.draw.circle(surface, (242, 238, 228), (st_x, st_y), 3)

        elif oid == "school_lab_table":
            housing = pygame.Rect(sx - 18, sy - 28 + bob, 36, 26)
            pygame.draw.rect(surface, (178, 136, 66), housing, border_radius=5)
            scr = housing.inflate(-8, -8)
            pygame.draw.rect(surface, (14, 34, 32), scr, border_radius=3)
            pts = []
            for px in range(scr.left + 2, scr.right - 2, 3):
                wy = scr.centery + int(math.sin(t_sec * 10.0 + px * 0.35) * 5)
                pts.append((px, wy))
            if len(pts) >= 2:
                pygame.draw.lines(surface, (92, 252, 204), False, pts, 2)
            pygame.draw.rect(surface, (36, 24, 14), housing, 2, border_radius=5)

        elif oid == "market_ledger":
            chest = self.get_sprite("chest_open", (52, 38))
            if chest:
                surface.blit(chest, (sx - 26, sy - 30 + bob))
            else:
                reg = pygame.Rect(sx - 16, sy - 24 + bob, 32, 24)
                pygame.draw.rect(surface, (218, 168, 62), reg, border_radius=4)

        elif oid in ("office_records", "police_dispatch"):
            comp = self.get_sprite("lab_desk_pc", (42, 62))
            if comp:
                surface.blit(comp, (sx - 21, sy - 48 + bob))
            else:
                mon = pygame.Rect(sx - 17, sy - 26 + bob, 34, 24)
                pygame.draw.rect(surface, (158, 122, 64), mon, border_radius=4)

        elif oid == "power_generator":
            ped = pygame.Rect(sx - 18, sy - 28 + bob, 36, 26)
            pygame.draw.rect(surface, (64, 42, 32), ped, border_radius=5)
            pygame.draw.circle(surface, (248, 86, 86), (sx - 6, sy - 15 + bob), 5)
            pygame.draw.circle(surface, (96, 238, 158), (sx + 7, sy - 15 + bob), 5)
            pygame.draw.rect(surface, (224, 178, 74), ped, 2, border_radius=5)

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
        Executes the 3-Stage Octopath Traveler HD-2D Post-Processing Pipeline for either the
        Overworld or the Active Cutaway Interior Room Scene.
        """
        sw, sh = screen.get_size()
        lw, lh = self._light_map_lowres.get_size()
        scale_x = lw / float(sw)
        scale_y = lh / float(sh)

        hour = (sim_minutes / 60.0) % 24.0
        if active_scene != "OVERWORLD":
            # Warm, atmospheric Victorian hearth-lit interior ambient tone
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

        def blit_point_light(brush: pygame.Surface, wx: float, wy: float, radius_px: int):
            sx = int((wx - cam_x) * scale_x)
            sy = int((wy - cam_y) * scale_y)
            r_low = max(8, int(radius_px * scale_x))
            if sx + r_low < 0 or sx - r_low > lw or sy + r_low < 0 or sy - r_low > lh:
                return
            scaled_b = pygame.transform.smoothscale(brush, (r_low * 2, r_low * 2))
            self._light_map_lowres.blit(scaled_b, (sx - r_low, sy - r_low), special_flags=pygame.BLEND_RGB_ADD)

        # 1. Player Warm Brass Lantern Pool (Sole-Knower Aura)
        flicker = int(math.sin(t_sec * 7.5) * 8)
        blit_point_light(self._light_radial_warm, player_wx, player_wy - 24, 215 + flicker)

        # 2. Protected Loved-One Cyan "Thread of Fate" Light Pool
        if loved_wx is not None and loved_wy is not None:
            blit_point_light(self._light_radial_cyan, loved_wx, loved_wy - 24, 170)

        if active_scene == "OVERWORLD":
            # 3A. Outdoor Street Gaslamps & Exterior House Window Glows
            for ptype, px, py in self.street_props:
                if ptype == "lamp":
                    blit_point_light(self._light_radial_warm, px, py - 56, 175 + int(math.sin(t_sec * 4.0 + px) * 6))
            for b in BUILDINGS:
                dx, dy = b["door_x"], b["door_y"]
                blit_point_light(self._light_radial_warm, dx, dy - 40, 185)
                blit_point_light(self._light_radial_warm, dx - 140, dy - 120, 160)
                blit_point_light(self._light_radial_warm, dx + 140, dy - 120, 160)
        else:
            # 3B. Interior Room Hearth, Candelabras & Interactive Station Glows
            for b in BUILDINGS:
                if b["id"] == active_scene:
                    rx, ry, rw, rh = b["rect"]
                    blit_point_light(self._light_radial_warm, rx + rw * 0.32, ry + rh * 0.42, 260)
                    blit_point_light(self._light_radial_warm, rx + rw * 0.68, ry + rh * 0.42, 260)
                    blit_point_light(self._light_radial_warm, b["door_x"], b["door_y"], 165)

            for wobj in world_objects:
                if wobj.get("building") != active_scene:
                    continue
                if wobj["id"] == active_hazard_obj_id:
                    blit_point_light(self._light_radial_crimson, wobj["x"], wobj["y"] - 16, 195)
                elif wobj["id"] == "power_generator":
                    blit_point_light(self._light_radial_cyan, wobj["x"], wobj["y"] - 16, 220)
                else:
                    blit_point_light(self._light_radial_warm, wobj["x"], wobj["y"] - 16, 135)

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
