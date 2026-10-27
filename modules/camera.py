"""Camera system with pan, zoom, and viewport transformations."""

from modules import settings


class Camera:
    """Manages 2D viewport pan and zoom for the isometric world."""

    def __init__(self, screen_width: int, screen_height: int) -> None:
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.offset_x: float = screen_width / 2.0
        self.offset_y: float = screen_height / 3.0
        self.zoom: float = settings.DEFAULT_ZOOM
        self.min_zoom: float = settings.MIN_ZOOM
        self.max_zoom: float = settings.MAX_ZOOM

    def pan(self, dx: float, dy: float) -> None:
        """Pan the camera view by pixel delta."""
        self.offset_x += dx
        self.offset_y += dy

    def zoom_at(self, screen_x: float, screen_y: float, factor: float) -> None:
        """Zoom in or out anchored at a specific screen coordinate (e.g. mouse cursor)."""
        new_zoom = max(self.min_zoom, min(self.max_zoom, self.zoom * factor))
        if new_zoom == self.zoom:
            return

        # Keep the world coordinate under the cursor stationary
        world_x = (screen_x - self.offset_x) / self.zoom
        world_y = (screen_y - self.offset_y) / self.zoom

        self.zoom = new_zoom
        self.offset_x = screen_x - (world_x * self.zoom)
        self.offset_y = screen_y - (world_y * self.zoom)

    def center_on_grid(
        self,
        grid_cols: int,
        grid_rows: int,
        tile_width: int = settings.TILE_WIDTH,
        tile_height: int = settings.TILE_HEIGHT,
    ) -> None:
        """Center camera view on the center of the isometric grid."""
        self.zoom = settings.DEFAULT_ZOOM
        # In isometric projection:
        # World X of grid center (gx=(cols-1)/2, gy=(rows-1)/2) is (gx - gy) * (w/2) = 0 (if square)
        # World Y is (gx + gy) * (h/2)
        center_gx = (grid_cols - 1) / 2.0
        center_gy = (grid_rows - 1) / 2.0
        center_world_x = (center_gx - center_gy) * (tile_width / 2.0)
        center_world_y = (center_gx + center_gy) * (tile_height / 2.0)

        self.offset_x = (self.screen_width / 2.0) - (center_world_x * self.zoom)
        self.offset_y = (self.screen_height / 2.0) - (center_world_y * self.zoom)

    def world_to_screen(self, wx: float, wy: float) -> tuple[float, float]:
        """Convert world coordinates to screen pixel coordinates."""
        sx = (wx * self.zoom) + self.offset_x
        sy = (wy * self.zoom) + self.offset_y
        return sx, sy

    def screen_to_world(self, sx: float, sy: float) -> tuple[float, float]:
        """Convert screen pixel coordinates to world coordinates."""
        wx = (sx - self.offset_x) / self.zoom
        wy = (sy - self.offset_y) / self.zoom
        return wx, wy

