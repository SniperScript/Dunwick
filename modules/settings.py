"""Isometric Grid Template - Settings and Configuration."""

# Display configuration
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800
FPS = 60
WINDOW_TITLE = "Isometric Grid Template"

# Grid configuration
DEFAULT_GRID_COLS = 16  # Tiles along the X axis
DEFAULT_GRID_ROWS = 16  # Tiles along the Y axis
TILE_WIDTH = 64         # Diamond width in pixels (screen space)
TILE_HEIGHT = 32        # Diamond height in pixels (2:1 isometric ratio)
TILE_ELEVATION_STEP = 16  # Vertical pixel height for each elevation level

# Camera configuration
DEFAULT_ZOOM = 1.0
MIN_ZOOM = 0.25
MAX_ZOOM = 3.0
ZOOM_SPEED = 1.1
PAN_SPEED = 15

# Color Palette (Modern Slate Theme)
COLOR_BG = (22, 25, 33)

# Tile Surface Colors
COLOR_TILE_FILL_A = (40, 45, 58)        # Primary tile fill
COLOR_TILE_FILL_B = (34, 39, 50)        # Alternating tile fill (checker pattern)
COLOR_TILE_BORDER = (65, 75, 96)        # Grid wireframe lines

# 3D Block Side Colors (when elevation > 0)
COLOR_BLOCK_TOP = (48, 54, 70)
COLOR_BLOCK_LEFT = (32, 36, 48)         # Shadowed left face
COLOR_BLOCK_RIGHT = (24, 27, 36)        # Darker right face
COLOR_BLOCK_BORDER = (75, 86, 110)

# Hover and Selection Colors
COLOR_HOVER_FILL = (52, 105, 175)
COLOR_HOVER_BORDER = (90, 165, 255)
COLOR_SELECTED_FILL = (42, 140, 95)
COLOR_SELECTED_BORDER = (70, 215, 145)

# Axis Indicator Colors
COLOR_AXIS_X = (235, 87, 87)            # Red: +X axis
COLOR_AXIS_Y = (46, 204, 113)           # Green: +Y axis

# UI and HUD Colors
COLOR_HUD_BG = (16, 18, 24, 210)
COLOR_HUD_BORDER = (45, 52, 68)
COLOR_TEXT_PRIMARY = (230, 235, 245)
COLOR_TEXT_SECONDARY = (145, 155, 175)
COLOR_TEXT_ACCENT = (100, 180, 255)
