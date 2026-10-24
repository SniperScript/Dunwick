"""
2.5D Tile Matrix, Continuous Circle-vs-AABB Corner-Rolling Collision & A* Pathfinding Engine
Architected using patterns from:
- FIFE / Unknown Horizons & GemRB (from bobeff/open-source-games)
- Tiny Life (Ellpeck/TinyLife) & IsoCity (victorqribeiro/isocity)

Key Upgrade:
- Replaces discrete grid-snag collision with Continuous Circle-vs-Rounded-Box Push-Out Resolution
  plus Automatic Corner-Rounding Tangent Glide so players and NPCs NEVER get stuck on corners of
  tables, chairs, or doorways!
"""

import heapq
import math
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


class StreetVehicle:
    """2.5D Defined Pixel-Art Vintage Town Motorcar / Tram that drives along Main Street and yields at crosswalks."""

    def __init__(self, y_lane: float, direction: float, color: tuple, vtype: str = "car"):
        self.y = y_lane
        self.direction = direction  # 1.0 = Eastbound, -1.0 = Westbound
        self.x = random.uniform(100.0, WORLD_WIDTH - 100.0)
        self.color = color
        self.vtype = vtype
        self.speed = 185.0 if vtype == "car" else 142.0
        self.current_speed = self.speed
        self.wheel_phase = 0.0

    def update(self, dt: float, characters: dict):
        blocked = False
        look_ahead = 98.0 * self.direction
        for c in characters.values():
            if getattr(c, "arrested", False):
                continue
            if abs(c.y - self.y) < 46.0:
                dx = (c.x - self.x) * self.direction
                if 0.0 < dx < abs(look_ahead):
                    blocked = True
                    break

        target_spd = 0.0 if blocked else self.speed
        self.current_speed += (target_spd - self.current_speed) * min(1.0, dt * 8.0)
        self.x += self.direction * self.current_speed * dt
        self.wheel_phase += self.current_speed * dt * 0.12

        if self.direction > 0 and self.x > WORLD_WIDTH + 120:
            self.x = -120.0
        elif self.direction < 0 and self.x < -120:
            self.x = WORLD_WIDTH + 120.0

    def draw(self, surface: pygame.Surface, cam_x: float, cam_y: float):
        sx = int(self.x - cam_x)
        sy = int(self.y - cam_y)
        w = 74 if self.vtype == "car" else 98
        h = 36
        if sx + w < -60 or sx - w > surface.get_width() + 60:
            return

        # 2.5D Ground Shadow
        pygame.draw.ellipse(surface, (28, 30, 36), (sx - w // 2 + 2, sy - 6, w, 24))

        # 3D Lower Chassis
        chassis = pygame.Rect(sx - w // 2, sy - h // 2 + 2, w, h - 8)
        dark_col = (max(0, self.color[0] - 45), max(0, self.color[1] - 45), max(0, self.color[2] - 45))
        pygame.draw.rect(surface, dark_col, chassis, border_radius=8)
        pygame.draw.rect(surface, self.color, chassis.move(0, -5), border_radius=8)
        pygame.draw.rect(surface, (28, 24, 22), chassis.move(0, -5), 2, border_radius=8)

        # 2.5D Raised Cabin Roof & Paned Windows
        cab_w = int(w * 0.62)
        cabin = pygame.Rect(sx - cab_w // 2, sy - h // 2 - 11, cab_w, h - 14)
        pygame.draw.rect(surface, (238, 228, 208), cabin, border_radius=6)
        win = cabin.inflate(-10, -6)
        pygame.draw.rect(surface, (145, 208, 238), win, border_radius=4)
        pygame.draw.line(surface, (42, 36, 32), (win.centerx, win.top), (win.centerx, win.bottom), 2)
        pygame.draw.rect(surface, (32, 28, 24), cabin, 2, border_radius=6)

        # Brass Headlights
        hx = sx + (w // 2 - 3) if self.direction > 0 else sx - (w // 2 + 3)
        pygame.draw.circle(surface, (255, 235, 135), (hx, sy - 6), 4)
        pygame.draw.circle(surface, (255, 235, 135), (hx, sy + 5), 4)

        # Animated Rotating Wheels
        for wx_off in (-w // 3, w // 3):
            wx_p, wy_p = sx + wx_off, sy + 11
            pygame.draw.circle(surface, (32, 34, 38), (wx_p, wy_p), 8)
            pygame.draw.circle(surface, (215, 185, 115), (wx_p, wy_p), 4)
            spoke_dx = int(math.cos(self.wheel_phase) * 5)
            spoke_dy = int(math.sin(self.wheel_phase) * 5)
            pygame.draw.line(surface, (45, 40, 35), (wx_p - spoke_dx, wy_p - spoke_dy), (wx_p + spoke_dx, wy_p + spoke_dy), 2)


class TileGridEngine:
    """
    Manages both:
    1. Continuous Circle-vs-Rounded-AABB Colliders (so characters roll smoothly around every corner)
    2. 81x56 Weighted Tile Grid for fast A* pathfinding across buildings, sidewalks, and crosswalks
    """

    def __init__(self):
        self.grid = [[T_GRASS for _ in range(GRID_H)] for _ in range(GRID_W)]
        self.cost = [[2.0 for _ in range(GRID_H)] for _ in range(GRID_W)]
        self.colliders: list[pygame.Rect] = []
        self._build_town_matrix_and_colliders()

        self.vehicles = [
            StreetVehicle(y_lane=842.0, direction=-1.0, color=(205, 68, 62), vtype="car"),
            StreetVehicle(y_lane=842.0, direction=-1.0, color=(225, 172, 58), vtype="bus"),
            StreetVehicle(y_lane=918.0, direction=1.0, color=(68, 135, 205), vtype="car"),
            StreetVehicle(y_lane=918.0, direction=1.0, color=(75, 175, 118), vtype="car"),
        ]
        self.vehicles[0].x = 450.0
        self.vehicles[1].x = 1750.0
        self.vehicles[2].x = 800.0
        self.vehicles[3].x = 2100.0

    def _build_town_matrix_and_colliders(self):
        self.colliders.clear()

        # 1. Lay down Sidewalks & Roads on the A* tile grid
        for tx in range(GRID_W):
            for ty in range(GRID_H):
                wx = tx * TILE_SIZE + TILE_SIZE // 2
                wy = ty * TILE_SIZE + TILE_SIZE // 2

                if 755 <= wy <= 1005 or 790 <= wx <= 950 or 1630 <= wx <= 1790:
                    self.grid[tx][ty] = T_SIDEWALK
                    self.cost[tx][ty] = 1.0

                if 805 <= wy <= 955 or (825 <= wx <= 915 and not (755 <= wy <= 1005)) or (1665 <= wx <= 1755 and not (755 <= wy <= 1005)):
                    self.grid[tx][ty] = T_ROAD
                    self.cost[tx][ty] = 3.5

                if 805 <= wy <= 955 and (abs(wx - 450) <= 48 or abs(wx - 1290) <= 48 or abs(wx - 2140) <= 48):
                    self.grid[tx][ty] = T_CROSSWALK
                    self.cost[tx][ty] = 1.1

        # 2. Build Perimeter Wall Colliders (with wide 136px doorway gaps) & Furniture Colliders
        wall_t = 14
        door_half_w = 68  # 136px wide doorway so characters glide through effortlessly!

        for b in BUILDINGS:
            rx, ry, rw, rh = b["rect"]
            dx, dy = b["door_x"], b["door_y"]

            # Left & Right perimeter walls
            self.colliders.append(pygame.Rect(rx, ry, wall_t, rh))
            self.colliders.append(pygame.Rect(rx + rw - wall_t, ry, wall_t, rh))

            # Top & Bottom perimeter walls (split at the doorway!)
            if abs(dy - (ry + rh)) < 30:
                # Door is on the bottom wall (Home, Cafe, Office)
                self.colliders.append(pygame.Rect(rx, ry, rw, wall_t))
                left_w = max(10, (dx - door_half_w) - rx)
                right_x = dx + door_half_w
                right_w = max(10, (rx + rw) - right_x)
                self.colliders.append(pygame.Rect(rx, ry + rh - wall_t, left_w, wall_t))
                self.colliders.append(pygame.Rect(right_x, ry + rh - wall_t, right_w, wall_t))
            else:
                # Door is on the top wall (School, Market, Park)
                self.colliders.append(pygame.Rect(rx, ry + rh - wall_t, rw, wall_t))
                left_w = max(10, (dx - door_half_w) - rx)
                right_x = dx + door_half_w
                right_w = max(10, (rx + rw) - right_x)
                self.colliders.append(pygame.Rect(rx, ry, left_w, wall_t))
                self.colliders.append(pygame.Rect(right_x, ry, right_w, wall_t))

            # Interior Furniture Colliders (shrunk by 10px on each side so corners are generous & easy to walk around)
            for f in b["furniture"]:
                if "Gym Court" in f["name"]:
                    continue  # Basketball court lines are painted on the floor, not a solid barrier!
                fx, fy, fw, fh = f["rect"]
                f_col_rect = pygame.Rect(fx + 10, fy + 10, max(16, fw - 20), max(16, fh - 20))
                self.colliders.append(f_col_rect)

            # Mark A* grid cells for building floor, perimeter walls, and wide 5-tile doorway
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

            # Open 5-tile doorway on the A* grid
            d_tx, d_ty = dx // TILE_SIZE, dy // TILE_SIZE
            for ox in range(-2, 3):
                for oy in range(-2, 3):
                    ntx, nty = d_tx + ox, d_ty + oy
                    if 0 <= ntx < GRID_W and 0 <= nty < GRID_H:
                        self.grid[ntx][nty] = T_DOOR
                        self.cost[ntx][nty] = 1.0

        # Sync A* grid obstacles for interior furniture from self.colliders
        for tx in range(GRID_W):
            for ty in range(GRID_H):
                if self.grid[tx][ty] in (T_WALL, T_DOOR):
                    continue
                cx = tx * TILE_SIZE + 16
                cy = ty * TILE_SIZE + 16
                if not self.is_circle_free(cx, cy, radius=9.0):
                    self.grid[tx][ty] = T_FURNITURE
                    self.cost[tx][ty] = 999.0

        # Ensure all interactive WORLD_OBJECTS have walkable A* tiles
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
        """Exact continuous check against all wall & furniture colliders."""
        if wx < 42.0 or wy < 42.0 or wx > WORLD_WIDTH - 42.0 or wy > WORLD_HEIGHT - 42.0:
            return False
        for rect in self.colliders:
            # Closest point on rect to (wx, wy)
            cx = max(float(rect.left), min(wx, float(rect.right)))
            cy = max(float(rect.top), min(wy, float(rect.bottom)))
            if (wx - cx) ** 2 + (wy - cy) ** 2 < radius * radius:
                return False
        return True

    def move_with_sliding(
        self, old_x: float, old_y: float, dx_step: float, dy_step: float, radius: float = 11.0
    ) -> tuple[float, float]:
        """
        Continuous Circle-vs-AABB Push-Out Resolution + Corner-Rounding Tangent Assist!
        1. Moves character by (dx_step, dy_step).
        2. Resolves any overlap with walls/tables by pushing the circle radially outward from the closest
           point on the rectangle—meaning every corner acts like a smooth curved bumper that characters
           roll around effortlessly!
        3. If pushing straight into the end of a wall or table near a corner (< 26px from the edge),
           adds a smooth tangent glide toward the open corner so you never snag.
        """
        x = max(44.0, min(WORLD_WIDTH - 44.0, old_x + dx_step))
        y = max(44.0, min(WORLD_HEIGHT - 44.0, old_y + dy_step))

        # 2 passes of continuous circle push-out resolution handle even tight L-corners cleanly
        for _ in range(2):
            for rect in self.colliders:
                if x + radius < rect.left or x - radius > rect.right or y + radius < rect.top or y - radius > rect.bottom:
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

                        # Corner-Rounding Tangent Assist when walking into the edge of a table or doorway post!
                        step_mag = math.hypot(dx_step, dy_step)
                        if step_mag > 0.1:
                            # If hitting a horizontal face near its left or right corner (< 26px), glide toward the corner!
                            if abs(ny) > 0.85 and abs(dx_step) < step_mag * 0.5:
                                dist_left = abs(x - rect.left)
                                dist_right = abs(x - rect.right)
                                if dist_left < 28.0:
                                    x -= step_mag * 0.65
                                elif dist_right < 28.0:
                                    x += step_mag * 0.65
                            # If hitting a vertical face near its top or bottom corner (< 26px), glide toward the corner!
                            elif abs(nx) > 0.85 and abs(dy_step) < step_mag * 0.5:
                                dist_top = abs(y - rect.top)
                                dist_bot = abs(y - rect.bottom)
                                if dist_top < 28.0:
                                    y -= step_mag * 0.65
                                elif dist_bot < 28.0:
                                    y += step_mag * 0.65
                    else:
                        # Center is inside rectangle: push out toward nearest edge
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
        """Weighted A* Pathfinding across the 81x56 Tile Grid."""
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
            (1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
            (1, 1, 1.414), (-1, 1, 1.414), (1, -1, 1.414), (-1, -1, 1.414),
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
