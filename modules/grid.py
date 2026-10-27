"""Isometric Grid module with mathematical projection, tile management, and Dunwick sprite rendering."""

import math
from dataclasses import dataclass, field
from typing import Optional
import pygame

from modules import settings
from modules.camera import Camera
from modules.sprites import IsometricSpriteLibrary


@dataclass
class Tile:
    """Represents a single cell in the isometric grid."""
    x: int
    y: int
    elevation: int = 0
    selected: bool = False
    custom_color: Optional[tuple[int, int, int]] = None
    tile_sprite: Optional[str] = None
    object_sprite: Optional[str] = None
    data: dict = field(default_factory=dict)


class IsometricGrid:
    """Manages an isometric grid with 2:1 projection math, vector wireframe, and Dunwick sprite rendering."""

    def __init__(
        self,
        cols: int = settings.DEFAULT_GRID_COLS,
        rows: int = settings.DEFAULT_GRID_ROWS,
        tile_width: int = settings.TILE_WIDTH,
        tile_height: int = settings.TILE_HEIGHT,
        elevation_step: int = settings.TILE_ELEVATION_STEP,
        sprite_lib: Optional[IsometricSpriteLibrary] = None,
    ) -> None:
        self.cols = cols
        self.rows = rows
        self.tile_width = tile_width
        self.tile_height = tile_height
        self.elevation_step = elevation_step
        self.sprite_lib = sprite_lib

        self.tiles: dict[tuple[int, int], Tile] = {}
        for y in range(rows):
            for x in range(cols):
                self.tiles[(x, y)] = Tile(x=x, y=y)

        self._font: Optional[pygame.font.Font] = None

    def get_font(self) -> Optional[pygame.font.Font]:
        """Lazy load a small system font for rendering coordinate labels."""
        if self._font is None:
            try:
                if hasattr(pygame, "font") and pygame.font.get_init():
                    self._font = pygame.font.SysFont("monospace", 10, bold=True)
            except Exception:
                try:
                    self._font = pygame.font.Font(None, 12)
                except Exception:
                    self._font = None
        return self._font

    def is_valid_cell(self, gx: int, gy: int) -> bool:
        """Check if grid coordinate lies within grid boundaries."""
        return 0 <= gx < self.cols and 0 <= gy < self.rows

    def get_tile(self, gx: int, gy: int) -> Optional[Tile]:
        """Get Tile instance at (gx, gy) or None if out of bounds."""
        return self.tiles.get((gx, gy))

    def set_elevation(self, gx: int, gy: int, elevation: int) -> bool:
        """Set elevation level for cell at (gx, gy). Returns True if changed."""
        tile = self.get_tile(gx, gy)
        if tile:
            tile.elevation = max(0, elevation)
            return True
        return False

    def toggle_selected(self, gx: int, gy: int) -> bool:
        """Toggle selected state for cell at (gx, gy)."""
        tile = self.get_tile(gx, gy)
        if tile:
            tile.selected = not tile.selected
            return True
        return False

    def clear_selection(self) -> None:
        """Deselect all tiles."""
        for tile in self.tiles.values():
            tile.selected = False

    def reset_grid(self) -> None:
        """Reset all tile elevations, sprites, colors, and selections to defaults."""
        for tile in self.tiles.values():
            tile.elevation = 0
            tile.selected = False
            tile.custom_color = None
            tile.tile_sprite = None
            tile.object_sprite = None
            tile.data.clear()

    def populate_dunwick_demo(self) -> None:
        """Populate the grid with a sample Dunwick 1924 High Street, Tramway & Estate layout."""
        self.reset_grid()
        mid_y = self.rows // 2
        cross_x = self.cols // 2

        for y in range(self.rows):
            for x in range(self.cols):
                tile = self.tiles[(x, y)]
                # High Street road & recessed brass steam-tramway down the middle rows
                if y == mid_y:
                    tile.tile_sprite = "iso_crosswalk" if x == cross_x else "iso_tram_rail_ne"
                elif y in (mid_y - 1, mid_y + 1):
                    tile.tile_sprite = "iso_crosswalk" if x == cross_x else "iso_cobblestone"
                elif y in (mid_y - 2, mid_y + 2):
                    tile.tile_sprite = "iso_sidewalk"
                elif y < mid_y - 2:
                    # North District: Manor & Polytechnic courtyards + moorland greensward
                    if 1 <= x <= 5 and 1 <= y <= 4:
                        tile.tile_sprite = "iso_wood_planks"
                    elif 10 <= x <= 14 and 1 <= y <= 4:
                        tile.tile_sprite = "iso_stone_inset"
                    else:
                        tile.tile_sprite = "iso_moor_grass"
                else:
                    # South District: Commons park, canal water basin & bazaar flagstones
                    if 6 <= x <= 9 and self.rows - 4 <= y <= self.rows - 2:
                        tile.tile_sprite = "iso_water"
                    elif x >= 11 and y >= mid_y + 3:
                        tile.tile_sprite = "iso_stone_tile"
                    else:
                        tile.tile_sprite = "iso_moor_grass"

        # Place Dunwick landmark houses, walls, fences, gaslamps, quest stations, and vehicles
        placements = [
            # Landmarks
            (2, 2, "iso_house_home"),
            (7, 2, "iso_house_office"),
            (12, 2, "iso_house_cafe"),
            (2, self.rows - 3, "iso_house_school"),
            (13, self.rows - 3, "iso_house_market"),
            # Street gaslamps along High Street sidewalk
            (1, mid_y - 2, "iso_street_gaslamp"),
            (5, mid_y - 2, "iso_street_gaslamp"),
            (10, mid_y - 2, "iso_street_gaslamp"),
            (14, mid_y - 2, "iso_street_gaslamp"),
            (3, mid_y + 2, "iso_street_gaslamp"),
            (11, mid_y + 2, "iso_street_gaslamp"),
            # Wrought-iron fences & topiary hedges
            (0, mid_y - 3, "iso_fence_iron_sw"),
            (1, mid_y - 3, "iso_fence_iron_sw"),
            (4, mid_y - 3, "iso_topiary_hedge"),
            (9, mid_y - 3, "iso_topiary_hedge"),
            # Courtyard Gargoyle Fountain & Trees
            (7, self.rows - 3, "iso_gargoyle_fountain"),
            (5, self.rows - 2, "iso_tree_hd2d"),
            (10, self.rows - 2, "iso_tree_hd2d"),
            # Vehicles on High Street & Tramway
            (4, mid_y, "iso_tram_amber_sw"),
            (11, mid_y - 1, "iso_car_crimson_sw"),
            (2, mid_y + 1, "iso_car_emerald_sw"),
            # Interactive Quest Stations & Props
            (12, mid_y + 4, "iso_quest_market_ledger"),
            (14, mid_y + 4, "iso_quest_cafe_counter"),
            (4, self.rows - 4, "iso_quest_school_lab_table"),
            (9, 3, "iso_quest_power_generator"),
            (11, mid_y + 3, "iso_barrels"),
            (15, mid_y + 3, "iso_crates"),
        ]
        for px, py, obj_id in placements:
            if self.is_valid_cell(px, py):
                self.tiles[(px, py)].object_sprite = obj_id

    # --- Projection Math ---

    def grid_to_world(self, gx: float, gy: float, elevation: float = 0.0) -> tuple[float, float]:
        """Convert grid (gx, gy, elevation) to 2D isometric world space coordinates."""
        wx = (gx - gy) * (self.tile_width / 2.0)
        wy = (gx + gy) * (self.tile_height / 2.0) - (elevation * self.elevation_step)
        return wx, wy

    def world_to_grid(self, wx: float, wy: float, elevation: float = 0.0) -> tuple[int, int]:
        """Exact inverse mathematical projection: world coordinate to integer grid coordinate."""
        adj_wy = wy + (elevation * self.elevation_step)
        u = (wx / self.tile_width) + (adj_wy / self.tile_height)
        v = (adj_wy / self.tile_height) - (wx / self.tile_width)
        gx = math.floor(u + 0.5)
        gy = math.floor(v + 0.5)
        return gx, gy

    def screen_to_grid(
        self,
        screen_x: float,
        screen_y: float,
        camera: Camera,
    ) -> Optional[tuple[int, int]]:
        """Convert screen pixel coordinates to grid coordinate (gx, gy)."""
        wx, wy = camera.screen_to_world(screen_x, screen_y)

        max_elev = max((t.elevation for t in self.tiles.values()), default=0)
        for e in range(max_elev, 0, -1):
            gx, gy = self.world_to_grid(wx, wy, elevation=e)
            if self.is_valid_cell(gx, gy):
                tile = self.tiles.get((gx, gy))
                if tile and tile.elevation >= e:
                    return gx, gy

        gx, gy = self.world_to_grid(wx, wy, elevation=0.0)
        if self.is_valid_cell(gx, gy):
            return gx, gy

        return None

    def get_tile_diamond(
        self,
        gx: int,
        gy: int,
        elevation: float,
        camera: Camera,
    ) -> list[tuple[float, float]]:
        """Calculate the 4 screen-space vertices of the top diamond face."""
        wx, wy = self.grid_to_world(gx, gy, elevation)
        sx, sy = camera.world_to_screen(wx, wy)

        half_w = (self.tile_width / 2.0) * camera.zoom
        half_h = (self.tile_height / 2.0) * camera.zoom

        top = (sx, sy - half_h)
        right = (sx + half_w, sy)
        bottom = (sx, sy + half_h)
        left = (sx - half_w, sy)

        return [top, right, bottom, left]

    # --- Rendering ---

    def render(
        self,
        surface: pygame.Surface,
        camera: Camera,
        hovered_coord: Optional[tuple[int, int]] = None,
        show_coordinates: bool = False,
        show_axes: bool = True,
        show_sprites: bool = True,
    ) -> None:
        """Render the isometric grid with vector geometry and/or Dunwick isometric sprites."""
        # Painter's algorithm depth sort: back-to-front by (x + y, y)
        sorted_coords = sorted(self.tiles.keys(), key=lambda c: (c[0] + c[1], c[1]))

        # Pass 1: Ground & Elevated Tile Blocks
        for gx, gy in sorted_coords:
            tile = self.tiles[(gx, gy)]
            is_hovered = (hovered_coord == (gx, gy))
            is_selected = tile.selected

            rendered_sprite = False
            if show_sprites and self.sprite_lib and tile.tile_sprite:
                rendered_sprite = self._render_tile_sprite(
                    surface,
                    camera,
                    gx,
                    gy,
                    tile,
                    is_hovered,
                    is_selected,
                )

            if not rendered_sprite:
                self._render_vector_tile(surface, camera, gx, gy, tile, is_hovered, is_selected)

            # Optional coordinate label
            if show_coordinates and camera.zoom >= 0.7:
                font = self.get_font()
                if font:
                    wx, wy = self.grid_to_world(gx, gy, tile.elevation)
                    sx, sy = camera.world_to_screen(wx, wy)
                    label = font.render(f"{gx},{gy}", True, (210, 220, 235))
                    label_rect = label.get_rect(center=(int(sx), int(sy)))
                    surface.blit(label, label_rect)

        # Pass 2: Depth-Sorted 3D Object Sprites (Walls, Houses, Props, Furniture, Quests, Vehicles)
        if show_sprites and self.sprite_lib:
            for gx, gy in sorted_coords:
                tile = self.tiles[(gx, gy)]
                if tile.object_sprite:
                    self._render_object_sprite(surface, camera, gx, gy, tile)

        if show_axes:
            self._render_axes(surface, camera)

    def _render_tile_sprite(
        self,
        surface: pygame.Surface,
        camera: Camera,
        gx: int,
        gy: int,
        tile: Tile,
        is_hovered: bool,
        is_selected: bool,
    ) -> bool:
        """Render a Dunwick isometric tile sprite (and stacked elevation blocks if elevated)."""
        if not self.sprite_lib or not tile.tile_sprite:
            return False

        # Draw stacked 3D isometric blocks from elevation 0 up to tile.elevation
        max_lvl = max(0, tile.elevation)
        for lvl in range(max_lvl + 1):
            spr = self.sprite_lib.get_scaled(tile.tile_sprite, camera.zoom, flat_tile=False)
            if spr is None:
                return False
            wx, wy = self.grid_to_world(gx, gy, float(lvl))
            sx, sy = camera.world_to_screen(wx, wy)
            half_h = (self.tile_height / 2.0) * camera.zoom
            dest_x = int(round(sx - spr.get_width() / 2.0))
            dest_y = int(round(sy - half_h))
            surface.blit(spr, (dest_x, dest_y))

        if is_selected or is_hovered:
            diamond = self.get_tile_diamond(gx, gy, tile.elevation, camera)
            border_col = settings.COLOR_SELECTED_BORDER if is_selected else settings.COLOR_HOVER_BORDER
            pygame.draw.polygon(surface, border_col, diamond, 2)

        return True

    def _render_object_sprite(
        self,
        surface: pygame.Surface,
        camera: Camera,
        gx: int,
        gy: int,
        tile: Tile,
    ) -> None:
        """Render a 3D isometric object/prop/building anchored to tile (gx, gy)."""
        if not self.sprite_lib or not tile.object_sprite:
            return
        spr = self.sprite_lib.get_scaled(tile.object_sprite, camera.zoom, flat_tile=False)
        if spr is None:
            return

        wx, wy = self.grid_to_world(gx, gy, float(tile.elevation))
        sx, sy = camera.world_to_screen(wx, wy)
        half_h = (self.tile_height / 2.0) * camera.zoom

        # Anchor bottom of object sprite to the bottom vertex of the tile diamond
        dest_x = int(round(sx - spr.get_width() / 2.0))
        dest_y = int(round(sy + half_h - spr.get_height() + (4 * camera.zoom)))
        surface.blit(spr, (dest_x, dest_y))

    def _render_vector_tile(
        self,
        surface: pygame.Surface,
        camera: Camera,
        gx: int,
        gy: int,
        tile: Tile,
        is_hovered: bool,
        is_selected: bool,
    ) -> None:
        """Render pure vector wireframe diamond or 3D block."""
        if is_selected:
            fill_color = settings.COLOR_SELECTED_FILL
            border_color = settings.COLOR_SELECTED_BORDER
        elif is_hovered:
            fill_color = settings.COLOR_HOVER_FILL
            border_color = settings.COLOR_HOVER_BORDER
        elif tile.custom_color:
            fill_color = tile.custom_color
            border_color = settings.COLOR_TILE_BORDER
        else:
            fill_color = (
                settings.COLOR_TILE_FILL_A
                if (gx + gy) % 2 == 0
                else settings.COLOR_TILE_FILL_B
            )
            border_color = settings.COLOR_TILE_BORDER

        if tile.elevation > 0:
            self._render_elevated_block(
                surface,
                camera,
                gx,
                gy,
                tile.elevation,
                fill_color,
                border_color,
                is_hovered or is_selected,
            )
        else:
            diamond = self.get_tile_diamond(gx, gy, 0.0, camera)
            pygame.draw.polygon(surface, fill_color, diamond)
            pygame.draw.polygon(surface, border_color, diamond, 1)

    def _render_elevated_block(
        self,
        surface: pygame.Surface,
        camera: Camera,
        gx: int,
        gy: int,
        elevation: int,
        top_color: tuple[int, int, int],
        border_color: tuple[int, int, int],
        is_highlighted: bool,
    ) -> None:
        """Render 3D isometric block with top diamond, left side quad, and right side quad."""
        top_diamond = self.get_tile_diamond(gx, gy, elevation, camera)
        top_pt, right_pt, bottom_pt, left_pt = top_diamond
        drop = (elevation * self.elevation_step) * camera.zoom

        left_face = [
            left_pt,
            bottom_pt,
            (bottom_pt[0], bottom_pt[1] + drop),
            (left_pt[0], left_pt[1] + drop),
        ]
        right_face = [
            bottom_pt,
            right_pt,
            (right_pt[0], right_pt[1] + drop),
            (bottom_pt[0], bottom_pt[1] + drop),
        ]

        if is_highlighted:
            side_left_color = tuple(max(0, c - 30) for c in top_color)
            side_right_color = tuple(max(0, c - 50) for c in top_color)
        else:
            side_left_color = settings.COLOR_BLOCK_LEFT
            side_right_color = settings.COLOR_BLOCK_RIGHT

        side_border = border_color if is_highlighted else settings.COLOR_BLOCK_BORDER

        pygame.draw.polygon(surface, side_left_color, left_face)
        pygame.draw.polygon(surface, side_border, left_face, 1)

        pygame.draw.polygon(surface, side_right_color, right_face)
        pygame.draw.polygon(surface, side_border, right_face, 1)

        pygame.draw.polygon(surface, top_color, top_diamond)
        pygame.draw.polygon(surface, border_color, top_diamond, 1)

    def _render_axes(self, surface: pygame.Surface, camera: Camera) -> None:
        """Render subtle +X and +Y directional arrows from origin (0, 0)."""
        wx, wy = self.grid_to_world(0, 0, 0.0)
        sx, sy = camera.world_to_screen(wx, wy)

        x_wx, x_wy = self.grid_to_world(2.0, 0.0, 0.0)
        x_sx, x_sy = camera.world_to_screen(x_wx, x_wy)

        y_wx, y_wy = self.grid_to_world(0.0, 2.0, 0.0)
        y_sx, y_sy = camera.world_to_screen(y_wx, y_wy)

        pygame.draw.line(surface, settings.COLOR_AXIS_X, (sx, sy), (x_sx, x_sy), 2)
        pygame.draw.line(surface, settings.COLOR_AXIS_Y, (sx, sy), (y_sx, y_sy), 2)

        font = self.get_font()
        if font:
            x_label = font.render("+X", True, settings.COLOR_AXIS_X)
            y_label = font.render("+Y", True, settings.COLOR_AXIS_Y)
            surface.blit(x_label, (x_sx + 4, x_sy - 8))
            surface.blit(y_label, (y_sx - 18, y_sy - 8))
