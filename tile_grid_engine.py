"""
Tile Matrix, Smooth Sub-Tile Collision & A* Pathfinding Engine
Architected using patterns from:
- Tiny Life (Ellpeck/TinyLife): 2D Tile Matrix, multi-tile doorways, furniture footprints, YSort depth
- IsoCity (victorqribeiro/isocity): Sidewalk/Crosswalk weighted A* pathfinding & live street vehicles
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
    """IsoCity-inspired moving street vehicle that drives along Main Street and yields at crosswalks."""

    def __init__(self, y_lane: float, direction: float, color: tuple, vtype: str = "car"):
        self.y = y_lane
        self.direction = direction  # 1.0 = Eastbound, -1.0 = Westbound
        self.x = random.uniform(100.0, WORLD_WIDTH - 100.0)
        self.color = color
        self.vtype = vtype
        self.speed = 190.0 if vtype == "car" else 145.0
        self.current_speed = self.speed

    def update(self, dt: float, characters: dict):
        # Yield smoothly if any pedestrian is on the road ahead of the vehicle!
        blocked = False
        look_ahead = 95.0 * self.direction
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

        if self.direction > 0 and self.x > WORLD_WIDTH + 120:
            self.x = -120.0
        elif self.direction < 0 and self.x < -120:
            self.x = WORLD_WIDTH + 120.0

    def draw(self, surface: pygame.Surface, cam_x: float, cam_y: float):
        sx = int(self.x - cam_x)
        sy = int(self.y - cam_y)
        w = 68 if self.vtype == "car" else 88
        h = 34
        rect = pygame.Rect(sx - w // 2, sy - h // 2, w, h)

        # Shadow
        pygame.draw.rect(surface, (32, 34, 40), rect.move(4, 5), border_radius=8)
        # Body
        pygame.draw.rect(surface, self.color, rect, border_radius=8)
        pygame.draw.rect(surface, (25, 28, 36), rect, 2, border_radius=8)
        # Cabin roof & windows
        cabin = pygame.Rect(sx - w // 4, sy - h // 2 + 4, w // 2, h - 8)
        pygame.draw.rect(surface, (175, 215, 240), cabin, border_radius=5)
        pygame.draw.rect(surface, (35, 42, 55), cabin, 2, border_radius=5)


class TileGridEngine:
    """
    Manages the 2D Tile Matrix for Maplewood:
    - Guarantees smooth, bug-free player movement with corner-sliding around doorways & furniture
    - Provides fast weighted A* pathfinding along sidewalks, crosswalks, and building doors for all 24 NPCs
    """

    def __init__(self):
        self.grid = [[T_GRASS for _ in range(GRID_H)] for _ in range(GRID_W)]
        self.cost = [[2.0 for _ in range(GRID_H)] for _ in range(GRID_W)]
        self._build_town_matrix()

        self.vehicles = [
            StreetVehicle(y_lane=842.0, direction=-1.0, color=(215, 75, 75), vtype="car"),
            StreetVehicle(y_lane=842.0, direction=-1.0, color=(235, 185, 65), vtype="bus"),
            StreetVehicle(y_lane=918.0, direction=1.0, color=(75, 145, 225), vtype="car"),
            StreetVehicle(y_lane=918.0, direction=1.0, color=(85, 195, 135), vtype="car"),
        ]
        # Space vehicles apart initially
        self.vehicles[0].x = 450.0
        self.vehicles[1].x = 1750.0
        self.vehicles[2].x = 800.0
        self.vehicles[3].x = 2100.0

    def _build_town_matrix(self):
        # 1. Lay down Sidewalks & Roads
        for tx in range(GRID_W):
            for ty in range(GRID_H):
                wx = tx * TILE_SIZE + TILE_SIZE // 2
                wy = ty * TILE_SIZE + TILE_SIZE // 2

                # Sidewalks
                if 755 <= wy <= 1005 or 790 <= wx <= 950 or 1630 <= wx <= 1790:
                    self.grid[tx][ty] = T_SIDEWALK
                    self.cost[tx][ty] = 1.0  # NPCs love sidewalks!

                # Asphalt Roads
                if 805 <= wy <= 955 or (825 <= wx <= 915 and not (755 <= wy <= 1005)) or (1665 <= wx <= 1755 and not (755 <= wy <= 1005)):
                    self.grid[tx][ty] = T_ROAD
                    self.cost[tx][ty] = 3.5  # Avoid walking down middle of road unless crossing

                # Crosswalks at building entrances (x around 450, 1290, 2140)
                if 805 <= wy <= 955 and (abs(wx - 450) <= 48 or abs(wx - 1290) <= 48 or abs(wx - 2140) <= 48):
                    self.grid[tx][ty] = T_CROSSWALK
                    self.cost[tx][ty] = 1.1

        # 2. Carve out the 6 Buildings, Perimeter Walls, Wide Doorways, and Furniture
        for b in BUILDINGS:
            rx, ry, rw, rh = b["rect"]
            x0, y0 = rx // TILE_SIZE, ry // TILE_SIZE
            x1, y1 = (rx + rw) // TILE_SIZE, (ry + rh) // TILE_SIZE

            for tx in range(max(0, x0), min(GRID_W, x1 + 1)):
                for ty in range(max(0, y0), min(GRID_H, y1 + 1)):
                    is_border = tx == x0 or tx == x1 or ty == y0 or ty == y1
                    if is_border:
                        self.grid[tx][ty] = T_WALL
                        self.cost[tx][ty] = 999.0
                    else:
                        self.grid[tx][ty] = T_FLOOR
                        self.cost[tx][ty] = 1.0

            # Carve a generous 5-tile-wide open doorway at (door_x, door_y) and clear 2 tiles inside/outside!
            d_tx = b["door_x"] // TILE_SIZE
            d_ty = b["door_y"] // TILE_SIZE
            for ox in range(-2, 3):
                for oy in range(-2, 3):
                    ntx, nty = d_tx + ox, d_ty + oy
                    if 0 <= ntx < GRID_W and 0 <= nty < GRID_H:
                        self.grid[ntx][nty] = T_DOOR
                        self.cost[ntx][nty] = 1.0

            # Mark solid furniture inside building (shrunk slightly by 8px so walking between tables is effortless)
            for f in b["furniture"]:
                fx, fy, fw, fh = f["rect"]
                fx0 = (fx + 10) // TILE_SIZE
                fy0 = (fy + 10) // TILE_SIZE
                fx1 = (fx + fw - 10) // TILE_SIZE
                fy1 = (fy + fh - 10) // TILE_SIZE
                for tx in range(max(0, fx0), min(GRID_W, fx1 + 1)):
                    for ty in range(max(0, fy0), min(GRID_H, fy1 + 1)):
                        if self.grid[tx][ty] != T_DOOR:
                            self.grid[tx][ty] = T_FURNITURE
                            self.cost[tx][ty] = 999.0

        # 3. Ensure all Interactive Object terminals (and their immediate approach tiles) are walkable
        for wobj in WORLD_OBJECTS:
            otx = int(wobj["x"]) // TILE_SIZE
            oty = int(wobj["y"]) // TILE_SIZE
            for ox in (-1, 0, 1):
                for oy in (0, 1):
                    ntx, nty = otx + ox, oty + oy
                    if 1 <= ntx < GRID_W - 1 and 1 <= nty < GRID_H - 1:
                        if self.grid[ntx][nty] == T_FURNITURE:
                            self.grid[ntx][nty] = T_FLOOR
                            self.cost[ntx][nty] = 1.0

    def is_walkable_tile(self, tx: int, ty: int) -> bool:
        if tx < 1 or ty < 1 or tx >= GRID_W - 1 or ty >= GRID_H - 1:
            return False
        return self.grid[tx][ty] not in (T_WALL, T_FURNITURE)

    def is_circle_free(self, wx: float, wy: float, radius: float = 11.0) -> bool:
        """Checks if a character's foot circle at (wx, wy) is free of solid walls/furniture."""
        if wx < 48.0 or wy < 48.0 or wx > WORLD_WIDTH - 48.0 or wy > WORLD_HEIGHT - 48.0:
            return False
        # Sample 4 cardinal points + 4 diagonals on the foot collision circle
        for ang in (0.0, 0.785, 1.57, 2.356, 3.141, 3.927, 4.712, 5.497):
            px = wx + math.cos(ang) * radius
            py = wy + math.sin(ang) * radius
            tx = int(px) // TILE_SIZE
            ty = int(py) // TILE_SIZE
            if not self.is_walkable_tile(tx, ty):
                return False
        return True

    def move_with_sliding(self, old_x: float, old_y: float, dx_step: float, dy_step: float, radius: float = 11.0) -> tuple[float, float]:
        """
        Sub-tile movement with axis separation AND automatic corner-rounding slide!
        If the player clips the edge of a doorway or table while walking, this nudges them
        smoothly through the opening so movement never feels snagged or broken.
        """
        # If character somehow spawned overlapping a solid tile, nudge them to nearest open tile
        if not self.is_circle_free(old_x, old_y, radius):
            old_x, old_y = self.snap_to_nearest_walkable(old_x, old_y)

        nx = old_x + dx_step
        ny = old_y + dy_step

        if self.is_circle_free(nx, ny, radius):
            return nx, ny

        # Try X movement alone
        x_ok = self.is_circle_free(nx, old_y, radius)
        # Try Y movement alone
        y_ok = self.is_circle_free(old_x, ny, radius)

        if x_ok and not y_ok:
            # Corner-assist: if moving mostly vertically into a doorway edge, nudge X toward clear space!
            if abs(dy_step) > 0.1:
                for nudge in (-6.0, 6.0, -12.0, 12.0):
                    if self.is_circle_free(old_x + nudge, ny, radius):
                        return old_x + nudge * 0.5, ny
            return nx, old_y

        if y_ok and not x_ok:
            if abs(dx_step) > 0.1:
                for nudge in (-6.0, 6.0, -12.0, 12.0):
                    if self.is_circle_free(nx, old_y + nudge, radius):
                        return nx, old_y + nudge * 0.5
            return old_x, ny

        # Both axes blocked directly: try corner-assist on either axis
        for nudge in (-8.0, 8.0, -15.0, 15.0):
            if abs(dy_step) > abs(dx_step) and self.is_circle_free(old_x + nudge, ny, radius):
                return old_x + nudge * 0.5, ny
            if abs(dx_step) >= abs(dy_step) and self.is_circle_free(nx, old_y + nudge, radius):
                return nx, old_y + nudge * 0.5

        return old_x, old_y

    def snap_to_nearest_walkable(self, wx: float, wy: float) -> tuple[float, float]:
        tx0 = max(1, min(GRID_W - 2, int(wx) // TILE_SIZE))
        ty0 = max(1, min(GRID_H - 2, int(wy) // TILE_SIZE))
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
        """
        Weighted A* Pathfinding across the 81x56 Tile Grid (Tiny Life / IsoCity style).
        Routes NPCs out of building doors, along sidewalks, across crosswalks, and around furniture!
        """
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

        while open_heap and visited < 1800:
            _, current = heapq.heappop(open_heap)
            visited += 1
            if current == gt:
                break

            cx, cy = current
            for ox, oy, step_dist in neighbors:
                nx, ny = cx + ox, cy + oy
                if not self.is_walkable_tile(nx, ny):
                    continue
                # Prevent cutting diagonally across a solid wall corner
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

        # Reconstruct & thin waypoints
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
