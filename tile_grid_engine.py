"""
2.5D Tile Matrix, Continuous Circle-vs-AABB Corner-Rolling Collision & A* Pathfinding Engine
Tailored for 1924 Dunwick-on-Severn (Medieval-Steampunk British Borough):
- Features 1920s Brass Steam-Carriages & Omni-Trams with vertical copper boiler stacks,
  rotating brass-spoked wheels, and malfunctioning brake visual warnings during Butterfly crash days.
"""

import heapq
import math
import os
import random
import pygame
from config import BUILDINGS, WORLD_HEIGHT, WORLD_OBJECTS, WORLD_WIDTH

TILE_SIZE = 32
GRID_W = WORLD_WIDTH // TILE_SIZE   # 81 tiles
GRID_H = WORLD_HEIGHT // TILE_SIZE  # 56 tiles

# Tile Types
T_GRASS = 0
T_SIDEWALK = 1
T_ROAD = 2
T_CROSSWALK = 3
T_FLOOR = 4
T_DOOR = 5
T_WALL = 6
T_FURNITURE = 7


_VEHICLE_SPRITE_CACHE: dict[str, pygame.Surface] = {}
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_VEH_DIR = os.path.join(_BASE_DIR, "assets", "hd2d_sprites", "vehicles")
_ISO_VEH_DIR = os.path.join(_BASE_DIR, "assets", "iso_sprites", "vehicles")


def _load_image_rgba(path: str) -> pygame.Surface:
    """Python 3.14-safe RGBA PNG loader with PIL fallback."""
    try:
        return pygame.image.load(path).convert_alpha()
    except Exception:
        from PIL import Image
        pil_img = Image.open(path).convert("RGBA")
        return pygame.image.frombytes(pil_img.tobytes(), pil_img.size, "RGBA")


class StreetVehicle:
    """Isometric 2:1 Pre-Rendered 1920s British Steampunk Steam-Carriage / Brass Omni-Tram along High Street."""

    def __init__(self, y_lane: float, direction: float, color: tuple, vtype: str = "car", sprite_name: str = "car_crimson.png"):
        self.y = y_lane
        self.direction = direction  # 1.0 = Eastbound (+X isometric), -1.0 = Westbound (-X isometric)
        self.x = random.uniform(100.0, WORLD_WIDTH - 100.0)
        self.color = color
        self.vtype = vtype
        self.sprite_name = sprite_name
        self.speed = 185.0 if vtype == "car" else 142.0
        self.current_speed = self.speed
        self.wheel_phase = 0.0
        self.runaway_hazard = False

    def _get_sprite(self) -> pygame.Surface | None:
        key = f"iso_{self.sprite_name}_{'E' if self.direction > 0 else 'W'}"
        if key in _VEHICLE_SPRITE_CACHE:
            return _VEHICLE_SPRITE_CACHE[key]

        # Prefer true 2:1 isometric vehicle sprite from assets/iso_sprites/vehicles
        base_stem = os.path.splitext(self.sprite_name)[0]
        iso_name = f"iso_{base_stem}_{'se' if self.direction > 0 else 'sw'}.png"
        iso_path = os.path.join(_ISO_VEH_DIR, iso_name)
        path = iso_path if os.path.exists(iso_path) else os.path.join(_VEH_DIR, self.sprite_name)

        if os.path.exists(path):
            try:
                surf = _load_image_rgba(path)
                if not os.path.exists(iso_path) and self.direction < 0:
                    surf = pygame.transform.flip(surf, True, False)
                _VEHICLE_SPRITE_CACHE[key] = surf
                return surf
            except Exception:
                _VEHICLE_SPRITE_CACHE[key] = None
        return None

    def update(self, dt: float, characters: dict):
        blocked = False
        look_ahead = 98.0 * self.direction
        if not self.runaway_hazard:
            for c in characters.values():
                if getattr(c, "arrested", False):
                    continue
                # NPC pedestrians at crosswalks make carriages slow down, but player stepping into traffic risks being struck!
                if getattr(c, "is_player", False):
                    continue
                if abs(c.y - self.y) < 46.0:
                    dx = (c.x - self.x) * self.direction
                    if 0.0 < dx < abs(look_ahead):
                        blocked = True
                        break

        target_spd = 0.0 if blocked else (self.speed * 1.32 if self.runaway_hazard else self.speed)
        self.current_speed += (target_spd - self.current_speed) * min(1.0, dt * 8.0)
        self.x += self.direction * self.current_speed * dt
        self.wheel_phase += self.current_speed * dt * 0.12

        if self.direction > 0 and self.x > WORLD_WIDTH + 120:
            self.x = -120.0
        elif self.direction < 0 and self.x < -120:
            self.x = WORLD_WIDTH + 120.0

    def draw(self, surface: pygame.Surface, cam_x: float, cam_y: float, iso_screen_pos: tuple[int, int] | None = None):
        if iso_screen_pos is not None:
            sx, sy = iso_screen_pos
        else:
            sx = int(self.x - cam_x)
            sy = int(self.y - cam_y)
        w = 104 if self.vtype == "car" else 128
        h = 74
        if sx + w < -100 or sx - w > surface.get_width() + 100 or sy + h < -100 or sy - h > surface.get_height() + 100:
            return

        # 1. Isometric Warm Additive Gaslight Headlamp Cone along the (2:1) road axis
        beam_surf = pygame.Surface((120, 76), pygame.SRCALPHA)
        if self.direction > 0:
            # Eastbound (+X isometric = South-East on screen: +dx, +0.5*dy)
            pygame.draw.polygon(beam_surf, (255, 214, 110, 48), [(10, 14), (114, 48), (88, 72), (4, 26)])
            surface.blit(beam_surf, (sx + 10, sy - 10))
        else:
            # Westbound (-X isometric = North-West on screen: -dx, -0.5*dy)
            pygame.draw.polygon(beam_surf, (255, 214, 110, 48), [(110, 62), (6, 28), (32, 4), (116, 50)])
            surface.blit(beam_surf, (sx - 126, sy - 58))

        # 2. Blit 2:1 Isometric Shaded Vehicle Sprite
        spr = self._get_sprite()
        if spr is not None:
            bob = int(math.sin(self.wheel_phase * 2.0) * (2.2 if self.runaway_hazard else 1.0))
            sh_surf = pygame.Surface((w, 34), pygame.SRCALPHA)
            pygame.draw.ellipse(sh_surf, (8, 10, 14, 145), (8, 4, w - 16, 24))
            surface.blit(sh_surf, (sx - w // 2, sy - 12))
            dest = spr.get_rect(midbottom=(sx, sy + 14 + bob))
            surface.blit(spr, dest.topleft)

            # 3. Puffing Steam Plume & Runaway Brake Hazard Sparks
            chim_x = sx + int(self.direction * 18)
            puff_off = int(math.sin(self.wheel_phase * 0.6) * 3)
            pygame.draw.circle(surface, (226, 222, 214), (chim_x - int(self.direction * 6), dest.top + 8 + puff_off), 5)
            pygame.draw.circle(surface, (195, 190, 182), (chim_x - int(self.direction * 13), dest.top + 2 - puff_off), 3)
            if self.runaway_hazard and (pygame.time.get_ticks() // 160) % 2 == 0:
                pygame.draw.circle(surface, (255, 65, 55), (sx, dest.top + 8), 6)
            return
        else:
            chassis = pygame.Rect(sx - w // 2, sy - 18, w, 30)
            pygame.draw.rect(surface, self.color, chassis, border_radius=6)

        # 3. Puffing Steam Plume & Runaway Brake Hazard Sparks
        chim_x = sx + int(self.direction * (w // 2 - 15))
        puff_off = int(math.sin(self.wheel_phase * 0.6) * 3)
        pygame.draw.circle(surface, (226, 222, 214), (chim_x - int(self.direction * 6), sy - 46 + puff_off), 6)
        pygame.draw.circle(surface, (195, 190, 182), (chim_x - int(self.direction * 13), sy - 52 - puff_off), 4)

        if self.runaway_hazard:
            pygame.draw.circle(surface, (255, 88, 58), (chim_x, sy - 40), 8, 2)

        # 4. Animated Brass-Spoked Wheels
        for wx_off in (-w // 3 + 4, w // 3 - 4):
            wx_p, wy_p = sx + wx_off, sy + 11
            pygame.draw.circle(surface, (18, 18, 22), (wx_p, wy_p), 10)
            pygame.draw.circle(surface, (224, 178, 78), (wx_p, wy_p), 8, 2)
            spoke_dx = int(math.cos(self.wheel_phase) * 6)
            spoke_dy = int(math.sin(self.wheel_phase) * 6)
            pygame.draw.line(
                surface, (218, 174, 78), (wx_p - spoke_dx, wy_p - spoke_dy), (wx_p + spoke_dx, wy_p + spoke_dy), 2
            )
            pygame.draw.line(
                surface, (218, 174, 78), (wx_p - spoke_dy, wy_p + spoke_dx), (wx_p + spoke_dy, wy_p - spoke_dx), 2
            )


class TileGridEngine:
    """
    Manages both:
    1. Continuous Circle-vs-Rounded-AABB Colliders (so characters roll smoothly around every corner)
    2. 81x56 Weighted Tile Grid for fast A* pathfinding across buildings, cobbles, and crosswalks
    """

    def __init__(self):
        self.grid = [[T_GRASS for _ in range(GRID_H)] for _ in range(GRID_W)]
        self.cost = [[2.0 for _ in range(GRID_H)] for _ in range(GRID_W)]
        self.colliders: list[pygame.Rect] = []
        self._build_town_matrix_and_colliders()

        self.vehicles = [
            StreetVehicle(y_lane=842.0, direction=-1.0, color=(158, 48, 48), vtype="car", sprite_name="car_crimson.png"),
            StreetVehicle(y_lane=842.0, direction=-1.0, color=(188, 138, 52), vtype="bus", sprite_name="tram_amber.png"),
            StreetVehicle(y_lane=918.0, direction=1.0, color=(52, 98, 148), vtype="car", sprite_name="car_navy.png"),
            StreetVehicle(y_lane=918.0, direction=1.0, color=(62, 128, 88), vtype="car", sprite_name="car_emerald.png"),
        ]
        self.vehicles[0].x = 450.0
        self.vehicles[1].x = 1750.0
        self.vehicles[2].x = 800.0
        self.vehicles[3].x = 2100.0

    def _build_town_matrix_and_colliders(self):
        self.colliders.clear()

        for tx in range(GRID_W):
            for ty in range(GRID_H):
                wx = tx * TILE_SIZE + TILE_SIZE // 2
                wy = ty * TILE_SIZE + TILE_SIZE // 2

                if 755 <= wy <= 1005 or 790 <= wx <= 950 or 1630 <= wx <= 1790:
                    self.grid[tx][ty] = T_SIDEWALK
                    self.cost[tx][ty] = 1.0

                if (
                    805 <= wy <= 955
                    or (825 <= wx <= 915 and not (755 <= wy <= 1005))
                    or (1665 <= wx <= 1755 and not (755 <= wy <= 1005))
                ):
                    self.grid[tx][ty] = T_ROAD
                    self.cost[tx][ty] = 3.5

                if 805 <= wy <= 955 and (abs(wx - 450) <= 48 or abs(wx - 1290) <= 48 or abs(wx - 2140) <= 48):
                    self.grid[tx][ty] = T_CROSSWALK
                    self.cost[tx][ty] = 1.1

        wall_t = 14
        door_half_w = 68

        for b in BUILDINGS:
            rx, ry, rw, rh = b["rect"]
            dx, dy = b["door_x"], b["door_y"]

            self.colliders.append(pygame.Rect(rx, ry, wall_t, rh))
            self.colliders.append(pygame.Rect(rx + rw - wall_t, ry, wall_t, rh))

            if abs(dy - (ry + rh)) < 30:
                self.colliders.append(pygame.Rect(rx, ry, rw, wall_t))
                left_w = max(10, (dx - door_half_w) - rx)
                right_x = dx + door_half_w
                right_w = max(10, (rx + rw) - right_x)
                self.colliders.append(pygame.Rect(rx, ry + rh - wall_t, left_w, wall_t))
                self.colliders.append(pygame.Rect(right_x, ry + rh - wall_t, right_w, wall_t))
            else:
                self.colliders.append(pygame.Rect(rx, ry + rh - wall_t, rw, wall_t))
                left_w = max(10, (dx - door_half_w) - rx)
                right_x = dx + door_half_w
                right_w = max(10, (rx + rw) - right_x)
                self.colliders.append(pygame.Rect(rx, ry, left_w, wall_t))
                self.colliders.append(pygame.Rect(right_x, ry, right_w, wall_t))

            for f in b["furniture"]:
                if "Gym Court" in f["name"]:
                    continue
                fx, fy, fw, fh = f["rect"]
                f_col_rect = pygame.Rect(fx + 10, fy + 10, max(16, fw - 20), max(16, fh - 20))
                self.colliders.append(f_col_rect)

            x0, y0 = rx // TILE_SIZE, ry // TILE_SIZE
            x1, y1 = (rx + rw) // TILE_SIZE, (ry + rh) // TILE_SIZE
            for tx in range(max(0, x0), min(GRID_W, x1 + 1)):
                for ty in range(max(0, y0), min(GRID_H, y1 + 1)):
                    if tx in (x0, x1) or ty in (y0, y1):
                        self.grid[tx][ty] = T_WALL
                        self.cost[tx][ty] = 999.0
                    else:
                        self.grid[tx][ty] = T_FLOOR
                        self.cost[tx][ty] = 1.0

            d_tx, d_ty = dx // TILE_SIZE, dy // TILE_SIZE
            for ox in range(-2, 3):
                for oy in range(-2, 3):
                    ntx, nty = d_tx + ox, d_ty + oy
                    if 0 <= ntx < GRID_W and 0 <= nty < GRID_H:
                        self.grid[ntx][nty] = T_DOOR
                        self.cost[ntx][nty] = 1.0

        for tx in range(GRID_W):
            for ty in range(GRID_H):
                if self.grid[tx][ty] in (T_WALL, T_DOOR):
                    continue
                cx = tx * TILE_SIZE + 16
                cy = ty * TILE_SIZE + 16
                if not self.is_circle_free(cx, cy, radius=9.0):
                    self.grid[tx][ty] = T_FURNITURE
                    self.cost[tx][ty] = 999.0

        for wobj in WORLD_OBJECTS:
            otx = int(wobj["x"]) // TILE_SIZE
            oty = int(wobj["y"]) // TILE_SIZE
            if 1 <= otx < GRID_W - 1 and 1 <= oty < GRID_H - 1:
                self.grid[otx][oty] = T_FLOOR
                self.cost[otx][oty] = 1.0

    def is_walkable_tile(self, tx: int, ty: int) -> bool:
        if tx < 1 or ty < 1 or tx >= GRID_W - 1 or ty >= GRID_H - 1:
            return False
        return self.grid[tx][ty] not in (T_WALL, T_FURNITURE)

    def is_circle_free(self, wx: float, wy: float, radius: float = 11.0) -> bool:
        if wx < 42.0 or wy < 42.0 or wx > WORLD_WIDTH - 42.0 or wy > WORLD_HEIGHT - 42.0:
            return False
        for rect in self.colliders:
            cx = max(float(rect.left), min(wx, float(rect.right)))
            cy = max(float(rect.top), min(wy, float(rect.bottom)))
            if (wx - cx) ** 2 + (wy - cy) ** 2 < radius * radius:
                return False
        return True

    def move_with_sliding(
        self, old_x: float, old_y: float, dx_step: float, dy_step: float, radius: float = 11.0
    ) -> tuple[float, float]:
        x = max(44.0, min(WORLD_WIDTH - 44.0, old_x + dx_step))
        y = max(44.0, min(WORLD_HEIGHT - 44.0, old_y + dy_step))

        for _ in range(2):
            for rect in self.colliders:
                if (
                    x + radius < rect.left
                    or x - radius > rect.right
                    or y + radius < rect.top
                    or y - radius > rect.bottom
                ):
                    continue

                cx = max(float(rect.left), min(x, float(rect.right)))
                cy = max(float(rect.top), min(y, float(rect.bottom)))
                vx = x - cx
                vy = y - cy
                dist_sq = vx * vx + vy * vy

                if dist_sq < radius * radius:
                    dist = math.sqrt(dist_sq)
                    if dist > 0.0001:
                        overlap = radius - dist
                        nx = vx / dist
                        ny = vy / dist
                        x += nx * overlap
                        y += ny * overlap

                        step_mag = math.hypot(dx_step, dy_step)
                        if step_mag > 0.1:
                            if abs(ny) > 0.85 and abs(dx_step) < step_mag * 0.5:
                                dist_left = abs(x - rect.left)
                                dist_right = abs(x - rect.right)
                                if dist_left < 28.0:
                                    x -= step_mag * 0.65
                                elif dist_right < 28.0:
                                    x += step_mag * 0.65
                            elif abs(nx) > 0.85 and abs(dy_step) < step_mag * 0.5:
                                dist_top = abs(y - rect.top)
                                dist_bot = abs(y - rect.bottom)
                                if dist_top < 28.0:
                                    y -= step_mag * 0.65
                                elif dist_bot < 28.0:
                                    y += step_mag * 0.65
                    else:
                        dl = abs(x - rect.left)
                        dr = abs(rect.right - x)
                        dt_edge = abs(y - rect.top)
                        db = abs(rect.bottom - y)
                        m = min(dl, dr, dt_edge, db)
                        if m == dl:
                            x = float(rect.left) - radius
                        elif m == dr:
                            x = float(rect.right) + radius
                        elif m == dt_edge:
                            y = float(rect.top) - radius
                        else:
                            y = float(rect.bottom) + radius

        return x, y

    def move_player_in_scene(
        self,
        old_x: float,
        old_y: float,
        dx_step: float,
        dy_step: float,
        active_scene: str = "OVERWORLD",
        radius: float = 11.0,
    ) -> tuple[float, float]:
        """
        Scene-aware continuous collision for the Player:
        - On `"OVERWORLD"`: All 6 houses are solid 2.5D exterior building colliders (the player walks on the
          streets, sidewalks, wynds, and courtyards outside the houses; stepping onto a doorway enters the house).
        - Inside a building (`active_scene == building_id`): The player is bounded inside that building's
          2.5D interior room and slides smoothly around its interior furniture.
        """
        if active_scene == "OVERWORLD":
            x = max(44.0, min(WORLD_WIDTH - 44.0, old_x + dx_step))
            y = max(44.0, min(WORLD_HEIGHT - 44.0, old_y + dy_step))
            house_rects = [pygame.Rect(*b["rect"]) for b in BUILDINGS]
            for _ in range(2):
                for rect in house_rects:
                    if (
                        x + radius < rect.left
                        or x - radius > rect.right
                        or y + radius < rect.top
                        or y - radius > rect.bottom
                    ):
                        continue
                    cx = max(float(rect.left), min(x, float(rect.right)))
                    cy = max(float(rect.top), min(y, float(rect.bottom)))
                    vx = x - cx
                    vy = y - cy
                    dist_sq = vx * vx + vy * vy
                    if dist_sq < radius * radius:
                        dist = math.sqrt(dist_sq)
                        if dist > 0.0001:
                            overlap = radius - dist
                            x += (vx / dist) * overlap
                            y += (vy / dist) * overlap
                        else:
                            dl = abs(x - rect.left)
                            dr = abs(rect.right - x)
                            dt_edge = abs(y - rect.top)
                            db = abs(rect.bottom - y)
                            m = min(dl, dr, dt_edge, db)
                            if m == dl:
                                x = float(rect.left) - radius
                            elif m == dr:
                                x = float(rect.right) + radius
                            elif m == dt_edge:
                                y = float(rect.top) - radius
                            else:
                                y = float(rect.bottom) + radius
            return x, y

        # Inside a Dedicated Interior Room Scene (`active_scene == building_id`)
        b = next((item for item in BUILDINGS if item["id"] == active_scene), None)
        if b is None:
            return self.move_with_sliding(old_x, old_y, dx_step, dy_step, radius=radius)

        rx, ry, rw, rh = b["rect"]
        x = max(float(rx + 26), min(float(rx + rw - 26), old_x + dx_step))
        y = max(float(ry + 54), min(float(ry + rh - 20), old_y + dy_step))

        furn_rects = []
        for f in b["furniture"]:
            if "Gym Court" in f["name"]:
                continue
            fx, fy, fw, fh = f["rect"]
            furn_rects.append(pygame.Rect(fx + 10, fy + 10, max(16, fw - 20), max(16, fh - 20)))

        for _ in range(2):
            for rect in furn_rects:
                if (
                    x + radius < rect.left
                    or x - radius > rect.right
                    or y + radius < rect.top
                    or y - radius > rect.bottom
                ):
                    continue
                cx = max(float(rect.left), min(x, float(rect.right)))
                cy = max(float(rect.top), min(y, float(rect.bottom)))
                vx = x - cx
                vy = y - cy
                dist_sq = vx * vx + vy * vy
                if dist_sq < radius * radius:
                    dist = math.sqrt(dist_sq)
                    if dist > 0.0001:
                        overlap = radius - dist
                        x += (vx / dist) * overlap
                        y += (vy / dist) * overlap
            x = max(float(rx + 26), min(float(rx + rw - 26), x))
            y = max(float(ry + 54), min(float(ry + rh - 20), y))

        return x, y

    def snap_to_nearest_walkable(self, wx: float, wy: float) -> tuple[float, float]:
        tx0 = max(1, min(GRID_W - 2, int(wx) // TILE_SIZE))
        ty0 = max(1, min(GRID_H - 2, int(wy) // TILE_SIZE))
        if self.is_walkable_tile(tx0, ty0) and self.is_circle_free(wx, wy, radius=11.0):
            return (wx, wy)
        if self.is_walkable_tile(tx0, ty0):
            return (tx0 * TILE_SIZE + 16.0, ty0 * TILE_SIZE + 16.0)
        for r in range(1, 8):
            for ox in range(-r, r + 1):
                for oy in range(-r, r + 1):
                    tx, ty = tx0 + ox, ty0 + oy
                    if self.is_walkable_tile(tx, ty):
                        return (tx * TILE_SIZE + 16.0, ty * TILE_SIZE + 16.0)
        return wx, wy

    def find_path(self, start_x: float, start_y: float, goal_x: float, goal_y: float) -> list[tuple[float, float]]:
        sx, sy = self.snap_to_nearest_walkable(start_x, start_y)
        gx, gy = self.snap_to_nearest_walkable(goal_x, goal_y)
        st = (int(sx) // TILE_SIZE, int(sy) // TILE_SIZE)
        gt = (int(gx) // TILE_SIZE, int(gy) // TILE_SIZE)

        if st == gt:
            return [(gx, gy)]

        open_heap = [(0.0, st)]
        came_from = {}
        g_score = {st: 0.0}
        visited = 0

        neighbors = [
            (1, 0, 1.0),
            (-1, 0, 1.0),
            (0, 1, 1.0),
            (0, -1, 1.0),
            (1, 1, 1.414),
            (-1, 1, 1.414),
            (1, -1, 1.414),
            (-1, -1, 1.414),
        ]

        while open_heap and visited < 4500:
            _, current = heapq.heappop(open_heap)
            visited += 1
            if current == gt:
                break

            cx, cy = current
            for ox, oy, step_dist in neighbors:
                nx, ny = cx + ox, cy + oy
                if not self.is_walkable_tile(nx, ny):
                    continue
                if ox != 0 and oy != 0:
                    if not (self.is_walkable_tile(cx + ox, cy) and self.is_walkable_tile(cx, cy + oy)):
                        continue

                tile_weight = self.cost[nx][ny]
                tentative_g = g_score[current] + step_dist * tile_weight
                nxt = (nx, ny)
                if tentative_g < g_score.get(nxt, 999999.0):
                    came_from[nxt] = current
                    g_score[nxt] = tentative_g
                    h = math.hypot(gt[0] - nx, gt[1] - ny)
                    heapq.heappush(open_heap, (tentative_g + h, nxt))

        if gt not in came_from:
            return [(gx, gy)]

        raw_tiles = []
        cur = gt
        while cur != st and cur in came_from:
            raw_tiles.append(cur)
            cur = came_from[cur]
        raw_tiles.reverse()

        waypoints = []
        for idx, (tx, ty) in enumerate(raw_tiles):
            if idx % 2 == 0 or idx == len(raw_tiles) - 1:
                waypoints.append((tx * TILE_SIZE + 16.0, ty * TILE_SIZE + 16.0))
        return waypoints
