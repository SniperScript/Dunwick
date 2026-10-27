"""HUD (Heads-Up Display) overlay for the isometric grid template & Dunwick sprite palette."""

from typing import Optional
import pygame

from modules import settings
from modules.camera import Camera
from modules.grid import IsometricGrid
from modules.sprites import IsometricSpriteLibrary


class HUD:
    """Renders debug information, tile inspection data, Dunwick sprite brush preview, and controls."""

    def __init__(self) -> None:
        self.show_help = True
        self.show_info = True
        self._font_title: Optional[pygame.font.Font] = None
        self._font_body: Optional[pygame.font.Font] = None
        self._font_small: Optional[pygame.font.Font] = None

    def _init_fonts(self) -> None:
        if self._font_title is None:
            try:
                if hasattr(pygame, "font") and pygame.font.get_init():
                    self._font_title = pygame.font.SysFont("sans-serif", 16, bold=True)
                    self._font_body = pygame.font.SysFont("sans-serif", 13)
                    self._font_small = pygame.font.SysFont("monospace", 11)
            except Exception:
                try:
                    self._font_title = pygame.font.Font(None, 20)
                    self._font_body = pygame.font.Font(None, 16)
                    self._font_small = pygame.font.Font(None, 14)
                except Exception:
                    pass

    def toggle_help(self) -> None:
        """Toggle controls cheat-sheet overlay."""
        self.show_help = not self.show_help

    def toggle_info(self) -> None:
        """Toggle information overlay."""
        self.show_info = not self.show_info

    def render(
        self,
        surface: pygame.Surface,
        grid: IsometricGrid,
        camera: Camera,
        fps: float,
        hovered_coord: Optional[tuple[int, int]],
        show_coordinates: bool,
        show_sprites: bool = True,
        active_category: str = "tiles",
        active_sprite_id: Optional[str] = None,
        sprite_lib: Optional[IsometricSpriteLibrary] = None,
    ) -> None:
        """Render HUD elements onto surface."""
        self._init_fonts()
        if not self._font_body:
            return

        if self.show_info:
            self._render_info_panel(
                surface,
                grid,
                camera,
                fps,
                hovered_coord,
                show_coordinates,
                show_sprites,
            )
            if sprite_lib and active_sprite_id:
                self._render_brush_panel(
                    surface,
                    sprite_lib,
                    active_category,
                    active_sprite_id,
                    show_sprites,
                )

        if self.show_help:
            self._render_help_panel(surface)

    def _render_info_panel(
        self,
        surface: pygame.Surface,
        grid: IsometricGrid,
        camera: Camera,
        fps: float,
        hovered_coord: Optional[tuple[int, int]],
        show_coordinates: bool,
        show_sprites: bool,
    ) -> None:
        """Render top-left statistics and inspector card."""
        hover_tile = grid.get_tile(*hovered_coord) if hovered_coord else None
        selected_count = sum(1 for t in grid.tiles.values() if t.selected)

        hover_text = (
            f"({hovered_coord[0]}, {hovered_coord[1]})"
            if hovered_coord
            else "None (outside)"
        )
        elev_text = f"{hover_tile.elevation}" if hover_tile else "--"
        tile_spr = hover_tile.tile_sprite if (hover_tile and hover_tile.tile_sprite) else "wireframe"
        obj_spr = hover_tile.object_sprite if (hover_tile and hover_tile.object_sprite) else "None"

        lines = [
            ("ISOENGINE + DUNWICK ASSETS", settings.COLOR_TEXT_ACCENT, True),
            (f"FPS: {round(fps)}", settings.COLOR_TEXT_PRIMARY, False),
            (f"Grid Size: {grid.cols} x {grid.rows} ({grid.cols * grid.rows} cells)", settings.COLOR_TEXT_SECONDARY, False),
            (f"Render Mode: {'DUNWICK SPRITES' if show_sprites else 'PURE WIREFRAME'} [T]", settings.COLOR_TEXT_PRIMARY, False),
            (f"Hovered Cell: {hover_text} (Elev: {elev_text})", settings.COLOR_TEXT_PRIMARY, False),
            (f"Cell Tile: {tile_spr}", settings.COLOR_TEXT_SECONDARY, False),
            (f"Cell Object: {obj_spr}", settings.COLOR_TEXT_SECONDARY, False),
            (f"Selected: {selected_count} | Zoom: {camera.zoom:.2f}x", settings.COLOR_TEXT_SECONDARY, False),
            (f"Coord Labels: {'ON' if show_coordinates else 'OFF'} [C]", settings.COLOR_TEXT_SECONDARY, False),
        ]

        padding = 12
        line_height = 20
        panel_width = 290
        panel_height = (len(lines) * line_height) + (padding * 2)

        panel_surf = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        panel_surf.fill(settings.COLOR_HUD_BG)
        pygame.draw.rect(panel_surf, settings.COLOR_HUD_BORDER, panel_surf.get_rect(), 1, border_radius=6)
        surface.blit(panel_surf, (15, 15))

        y = 15 + padding
        for text, color, is_title in lines:
            font = self._font_title if is_title else self._font_body
            if font:
                rendered = font.render(text, True, color)
                surface.blit(rendered, (15 + padding, y))
            y += line_height

    def _render_brush_panel(
        self,
        surface: pygame.Surface,
        sprite_lib: IsometricSpriteLibrary,
        active_category: str,
        active_sprite_id: str,
        show_sprites: bool,
    ) -> None:
        """Render top-right Dunwick isometric sprite palette & active brush preview."""
        panel_w, panel_h = 285, 145
        panel_x = surface.get_width() - panel_w - 15
        panel_y = 15

        panel_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel_surf.fill(settings.COLOR_HUD_BG)
        pygame.draw.rect(panel_surf, settings.COLOR_HUD_BORDER, panel_surf.get_rect(), 1, border_radius=6)
        surface.blit(panel_surf, (panel_x, panel_y))

        cat_items = sprite_lib.by_category.get(active_category, [])
        idx = (cat_items.index(active_sprite_id) + 1) if active_sprite_id in cat_items else 0
        label = sprite_lib.get_label(active_sprite_id)

        if self._font_title and self._font_body and self._font_small:
            t_surf = self._font_title.render("DUNWICK SPRITE BRUSH", True, settings.COLOR_TEXT_ACCENT)
            surface.blit(t_surf, (panel_x + 12, panel_y + 10))

            c_surf = self._font_body.render(
                f"Category [Tab]: {active_category.upper()} ({idx}/{len(cat_items)})",
                True,
                settings.COLOR_TEXT_PRIMARY,
            )
            surface.blit(c_surf, (panel_x + 12, panel_y + 34))

            l_surf = self._font_body.render(label[:26], True, settings.COLOR_TEXT_SECONDARY)
            surface.blit(l_surf, (panel_x + 12, panel_y + 56))

            id_surf = self._font_small.render(f"ID: {active_sprite_id}", True, settings.COLOR_TEXT_SECONDARY)
            surface.blit(id_surf, (panel_x + 12, panel_y + 78))

            hint_surf = self._font_small.render("[ / ]: Cycle Brush | F: Paint All", True, settings.COLOR_TEXT_ACCENT)
            surface.blit(hint_surf, (panel_x + 12, panel_y + 116))

        # Render sprite thumbnail box on the right side of the card
        preview_rect = pygame.Rect(panel_x + panel_w - 86, panel_y + 34, 72, 72)
        pygame.draw.rect(surface, (28, 33, 44), preview_rect, border_radius=4)
        pygame.draw.rect(surface, settings.COLOR_HUD_BORDER, preview_rect, 1, border_radius=4)

        spr = sprite_lib.get_surface(active_sprite_id)
        if spr:
            scale = min(64.0 / max(1, spr.get_width()), 64.0 / max(1, spr.get_height()), 1.5)
            tw = max(1, int(spr.get_width() * scale))
            th = max(1, int(spr.get_height() * scale))
            thumb = pygame.transform.smoothscale(spr, (tw, th))
            tx = preview_rect.centerx - tw // 2
            ty = preview_rect.centery - th // 2
            surface.blit(thumb, (tx, ty))

    def _render_help_panel(self, surface: pygame.Surface) -> None:
        """Render bottom-left controls cheat-sheet."""
        shortcuts = [
            ("Left Click", "Place Active Tile / Sprite"),
            ("Ctrl + L-Click", "Select / Deselect Tile"),
            ("Shift + L-Click", "Raise Elevation (+1)"),
            ("Right Click", "Clear Object / Lower Elev"),
            ("Tab", "Next Asset Category"),
            ("[ / ]", "Prev / Next Sprite Brush"),
            ("T", "Toggle Sprites / Wireframe"),
            ("P", "Load Dunwick Town Demo"),
            ("G", "Reset to Empty Wireframe"),
            ("WASD / Scroll", "Pan & Zoom Camera"),
            ("C / H / Esc", "Coords / Help / Quit"),
        ]

        padding = 10
        line_height = 18
        panel_width = 305
        panel_height = (len(shortcuts) * line_height) + (padding * 2) + 24
        panel_x = 15
        panel_y = surface.get_height() - panel_height - 15

        panel_surf = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        panel_surf.fill(settings.COLOR_HUD_BG)
        pygame.draw.rect(panel_surf, settings.COLOR_HUD_BORDER, panel_surf.get_rect(), 1, border_radius=6)
        surface.blit(panel_surf, (panel_x, panel_y))

        if self._font_title:
            title = self._font_title.render("CONTROLS", True, settings.COLOR_TEXT_ACCENT)
            surface.blit(title, (panel_x + padding, panel_y + padding))

        y = panel_y + padding + 22
        for key, action in shortcuts:
            if self._font_small and self._font_body:
                key_surf = self._font_small.render(f"[{key}]", True, settings.COLOR_TEXT_PRIMARY)
                action_surf = self._font_body.render(action, True, settings.COLOR_TEXT_SECONDARY)
                surface.blit(key_surf, (panel_x + padding, y))
                surface.blit(action_surf, (panel_x + padding + 120, y))
            y += line_height
