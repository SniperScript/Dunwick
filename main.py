"""
CHRONICLES OF DUNWICK: DEFYING FATE (1924) // 2.5D Medieval-Steampunk Time-Loop RPG
Features:
1. THREE PLAYABLE SCENARIOS OF FATE:
   - Scenario I:   THE DOOMSDAY CLOCK ("The World Will End")
   - Scenario II:  THE GRIM DECREE ("You Are Going to Die")
   - Scenario III: THE THREAD OF FATE ("Your Loved One Is Going to Die")
2. SOLE-KNOWER PROTAGONIST SELECTION (Family of 4: Lord Arthur, Lady Elena, Maya, Leo):
   - Only your chosen character remembers the time loop; the other 3 family members are autonomous
     humans who do not know!
3. 7-DAY BUTTERFLY EFFECT & ANTI-WALKTHROUGH ENGINE:
   - Foiling Day d's hazard mutates the causal web for Day d+1 across an entire 7-Day Week (Mon–Sun).
   - Non-repetitive AI + procedural NPC dialogue with Subconscious Dream Echoes and Behavioral Tells.
"""

import json
import math
import os
import random
import sys
import pygame

from art_engine_25d import INTERIOR_PAD, ArtEngine25D
from config import (
    BUILDINGS,
    COLORS,
    DEFAULT_SETTINGS,
    FAMILY_LORE_PROLOGUES,
    FPS,
    SCENARIO_MODES,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    SETTINGS_FILE_PATH,
    TITLE,
    TOTAL_DAYS_IN_WEEK,
    TOWN_LORE_PROLOGUE,
    WEEK_DAYS,
    WORLD_HEIGHT,
    WORLD_WIDTH,
)
from cloud_llm_broker import CloudLLMBroker
from simulation_world import SimulationWorld, SimCharacter
from skeletal_engine import draw_character_portrait
from death_cinematics import DeathCinematicEngine


class MaplewoodRPGApp:
    def __init__(self, headless_test: bool = False):
        self.headless_test = headless_test
        if headless_test:
            os.environ["SDL_VIDEODRIVER"] = "dummy"
            os.environ["SDL_AUDIODRIVER"] = "dummy"

        pygame.init()
        pygame.font.init()

        if self.headless_test:
            self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        else:
            try:
                self.screen = pygame.display.set_mode(
                    (SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN | pygame.SCALED
                )
            except Exception:
                self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(TITLE)
        self.clock = pygame.time.Clock()

        assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
        fonts_dir = os.path.join(assets_dir, "fonts")
        font_bold_path = os.path.join(fonts_dir, "SourceSansPro-Bold.ttf")
        font_semi_path = os.path.join(fonts_dir, "SourceSansPro-Semibold.ttf")
        gothic_bold_path = os.path.join(fonts_dir, "GothicSerif-Bold.ttf")
        gothic_reg_path = os.path.join(fonts_dir, "GothicSerif-Regular.ttf")

        try:
            if os.path.exists(font_bold_path) and os.path.exists(font_semi_path):
                self.font_xs = pygame.font.Font(font_semi_path, 13)
                self.font_sm = pygame.font.Font(font_bold_path, 15)
                self.font_md = pygame.font.Font(font_bold_path, 18)
                self.font_lg = pygame.font.Font(font_bold_path, 22)
                self.font_xl = pygame.font.Font(font_bold_path, 27)
                self.font_title = pygame.font.Font(font_bold_path, 34)
            else:
                raise FileNotFoundError()
        except Exception:
            self.font_xs = pygame.font.SysFont("DejaVu Sans, Arial, sans-serif", 12, bold=True)
            self.font_sm = pygame.font.SysFont("DejaVu Sans, Arial, sans-serif", 14, bold=True)
            self.font_md = pygame.font.SysFont("DejaVu Sans, Arial, sans-serif", 17, bold=True)
            self.font_lg = pygame.font.SysFont("DejaVu Sans, Arial, sans-serif", 21, bold=True)
            self.font_xl = pygame.font.SysFont("DejaVu Sans, Arial, sans-serif", 26, bold=True)
            self.font_title = pygame.font.SysFont("DejaVu Sans, Arial, sans-serif", 34, bold=True)

        try:
            if os.path.exists(gothic_bold_path) and os.path.exists(gothic_reg_path):
                self.font_gothic_xs = pygame.font.Font(gothic_reg_path, 13)
                self.font_gothic_sm = pygame.font.Font(gothic_reg_path, 15)
                self.font_gothic_md = pygame.font.Font(gothic_bold_path, 18)
                self.font_gothic_lg = pygame.font.Font(gothic_bold_path, 22)
                self.font_gothic_xl = pygame.font.Font(gothic_bold_path, 26)
                self.font_gothic_title = pygame.font.Font(gothic_bold_path, 34)
            else:
                self.font_gothic_xs = self.font_xs
                self.font_gothic_sm = self.font_sm
                self.font_gothic_md = self.font_md
                self.font_gothic_lg = self.font_lg
                self.font_gothic_xl = self.font_xl
                self.font_gothic_title = self.font_title
        except Exception:
            self.font_gothic_xs = self.font_xs
            self.font_gothic_sm = self.font_sm
            self.font_gothic_md = self.font_md
            self.font_gothic_lg = self.font_lg
            self.font_gothic_xl = self.font_xl
            self.font_gothic_title = self.font_title

        self._load_settings()

        # Load Gothic Main Menu Backgrounds
        self.menu_bgs: dict[str, pygame.Surface] = {}
        assets_menu_dir = os.path.join(assets_dir, "menu")
        for bg_key, bg_fname in [
            ("DUNWICK_MARKET", "dunwick_market_gothic_night.png"),
            ("BLOOD_MOON_ECLIPSE", "dunwick_menu_bg.png"),
        ]:
            bg_p = os.path.join(assets_menu_dir, bg_fname)
            if os.path.exists(bg_p):
                try:
                    loaded = pygame.image.load(bg_p).convert()
                    self.menu_bgs[bg_key] = pygame.transform.smoothscale(loaded, (SCREEN_WIDTH, SCREEN_HEIGHT))
                except Exception as e:
                    print(f"Failed to load menu bg {bg_fname}: {e}")

        self.llm_broker = CloudLLMBroker()
        self.world = SimulationWorld(self.llm_broker)

        self.art_engine = ArtEngine25D(assets_dir=assets_dir)
        self.death_engine = DeathCinematicEngine()

        p = self.world.get_player()
        self.cam_x = p.x - SCREEN_WIDTH * 0.5
        self.cam_y = p.y - SCREEN_HEIGHT * 0.5

        # Active Modal: None, "MAIN_MENU", "SETTINGS", "FAMILY_SELECT", "LORE_PROLOGUE", "DIALOGUE", "NOTEBOOK", "API_CONFIG"
        self.active_modal = None if headless_test else "MAIN_MENU"
        self.menu_selected_idx = 0
        self.settings_tab_idx = 0
        self.editing_setting_key: str | None = None
        self.in_game_paused = False
        self._cached_vignette: pygame.Surface | None = None
        self._init_menu_embers()
        self.has_seen_prologue = False
        self.talking_npc: SimCharacter | None = None
        self.npc_greeting = ""
        self.npc_options = []
        self.typewriter_chars = 0.0
        self.custom_input = ""
        self.typing_custom = False

        self.toast_msg = (
            "1924 Dunwick-on-Severn: [WASD/Arrows] Walk, [E] Interact, [G] Next Day (when foiled), [N] Butterfly Journal!"
        )
        self.toast_timer = 6.5

        self.trees = [
            (860, 220),
            (860, 460),
            (860, 660),
            (1710, 220),
            (1710, 460),
            (1710, 660),
            (860, 1120),
            (860, 1380),
            (860, 1600),
            (1710, 1120),
            (1710, 1380),
            (1710, 1600),
            (1920, 1560),
            (2380, 1560),
            (2420, 1180),
        ]

        self.api_provider_choice = self.llm_broker.config.get("provider", "gemini")
        self.api_key_input = (
            self.llm_broker.config.get("gemini_api_key", "")
            if self.api_provider_choice == "gemini"
            else self.llm_broker.config.get("openai_api_key", "")
        )

    def _load_settings(self):
        self.settings = dict(DEFAULT_SETTINGS)
        if os.path.exists(SETTINGS_FILE_PATH):
            try:
                with open(SETTINGS_FILE_PATH, "r", encoding="utf-8") as f:
                    self.settings.update(json.load(f))
            except Exception:
                pass

    def _save_settings(self):
        try:
            with open(SETTINGS_FILE_PATH, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=2)
            self.show_toast("Settings saved successfully!", duration=3.0)
        except Exception:
            pass

    def _init_menu_embers(self):
        self.menu_embers = []
        for _ in range(52):
            self.menu_embers.append(
                {
                    "x": random.uniform(20, SCREEN_WIDTH - 20),
                    "y": random.uniform(20, SCREEN_HEIGHT - 20),
                    "vx": random.uniform(-14, 14),
                    "vy": random.uniform(-36, -14),
                    "size": random.uniform(1.8, 3.8),
                    "color": random.choice(
                        [
                            (195, 38, 48),  # Blood Crimson
                            (225, 68, 78),  # Bright Ember
                            (142, 28, 38),  # Deep Blood
                            (218, 142, 48),  # Gaslight Amber
                            (180, 100, 40),  # Smoldering Brass
                        ]
                    ),
                    "life": random.uniform(0.2, 1.0),
                    "max_life": random.uniform(2.5, 4.5),
                    "pulse": random.uniform(0, math.tau),
                }
            )

    def _update_menu_particles(self, dt: float):
        if not self.settings.get("atmospheric_particles", True):
            return
        for p in self.menu_embers:
            p["pulse"] = (p["pulse"] + dt * 2.5) % math.tau
            sway = math.sin(p["pulse"]) * 12.0
            p["x"] += (p["vx"] + sway) * dt
            p["y"] += p["vy"] * dt
            p["life"] -= dt
            if p["y"] < -10 or p["life"] <= 0 or p["x"] < -10 or p["x"] > SCREEN_WIDTH + 10:
                p["x"] = random.uniform(20, SCREEN_WIDTH - 20)
                p["y"] = SCREEN_HEIGHT + random.uniform(4, 24)
                p["life"] = p["max_life"]
                p["vx"] = random.uniform(-14, 14)
                p["vy"] = random.uniform(-38, -16)

    def _render_bloodborne_vignette(self, surface: pygame.Surface):
        if self._cached_vignette is None:
            vignette = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            w, h = SCREEN_WIDTH, SCREEN_HEIGHT
            cx, cy = w // 2, h // 2
            max_d = math.hypot(cx, cy)
            for rad in range(int(max_d), 220, -32):
                ratio = (rad - 220) / (max_d - 220)
                alpha = int(ratio * ratio * 200)
                rect = pygame.Rect(cx - rad, cy - int(rad * 0.65), rad * 2, int(rad * 1.3))
                pygame.draw.ellipse(vignette, (4, 5, 8, max(0, min(24, alpha // 8))), rect)

            for c_i in range(80):
                c_alpha = int((80 - c_i) / 80 * 180)
                pygame.draw.rect(vignette, (4, 5, 8, c_alpha // 6), (0, 0, SCREEN_WIDTH, c_i))
                pygame.draw.rect(vignette, (4, 5, 8, c_alpha // 6), (0, SCREEN_HEIGHT - c_i, SCREEN_WIDTH, c_i))
                pygame.draw.rect(vignette, (4, 5, 8, c_alpha // 6), (0, 0, c_i, SCREEN_HEIGHT))
                pygame.draw.rect(vignette, (4, 5, 8, c_alpha // 6), (SCREEN_WIDTH - c_i, 0, c_i, SCREEN_HEIGHT))
            self._cached_vignette = vignette

        surface.blit(self._cached_vignette, (0, 0))

    def _render_menu_embers(self, surface: pygame.Surface):
        if not self.settings.get("atmospheric_particles", True):
            return
        for p in self.menu_embers:
            alpha = int(min(1.0, p["life"] / 0.5) * 220)
            sz = int(p["size"])
            glow_surf = pygame.Surface((sz * 4, sz * 4), pygame.SRCALPHA)
            r, g, b = p["color"]
            pygame.draw.circle(glow_surf, (r, g, b, alpha // 4), (sz * 2, sz * 2), sz * 2)
            pygame.draw.circle(glow_surf, (r, g, b, alpha), (sz * 2, sz * 2), sz)
            surface.blit(glow_surf, (int(p["x"]) - sz * 2, int(p["y"]) - sz * 2))

    def _draw_figma_card(
        self,
        rect: pygame.Rect,
        bg_rgba: tuple[int, int, int, int] = (14, 16, 24, 250),
        border_col: tuple[int, int, int] = (74, 58, 48),
        radius: int = 14,
        border_w: int = 2,
        shadow_offset: int = 6,
        inner_border: bool = True,
        corner_tabs: bool = True,
    ):
        if shadow_offset > 0:
            sh_surf = pygame.Surface((rect.width + 10, rect.height + 10), pygame.SRCALPHA)
            pygame.draw.rect(
                sh_surf, (4, 5, 8, 160), (0, 0, rect.width + 10, rect.height + 10), border_radius=radius + 2
            )
            self.screen.blit(sh_surf, (rect.x - 5 + shadow_offset // 2, rect.y + shadow_offset))

        card_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        pygame.draw.rect(card_surf, bg_rgba, (0, 0, rect.width, rect.height), border_radius=radius)
        # Stone top-edge highlight
        pygame.draw.line(card_surf, (48, 52, 68, 130), (8, 2), (rect.width - 9, 2), 1)
        self.screen.blit(card_surf, rect.topleft)

        if border_w > 0:
            pygame.draw.rect(self.screen, border_col, rect, border_w, border_radius=radius)
            if inner_border and border_w >= 2:
                inner_r = rect.inflate(-6, -6)
                pygame.draw.rect(self.screen, (138, 28, 38), inner_r, 1, border_radius=max(2, radius - 3))

        if corner_tabs:
            tab_sz = 6
            corners = [
                (rect.left - 2, rect.top - 2),
                (rect.right - tab_sz + 2, rect.top - 2),
                (rect.left - 2, rect.bottom - tab_sz + 2),
                (rect.right - tab_sz + 2, rect.bottom - tab_sz + 2),
            ]
            for cx, cy in corners:
                pygame.draw.rect(self.screen, (218, 172, 78), (cx, cy, tab_sz, tab_sz))
                pygame.draw.rect(self.screen, (34, 26, 20), (cx, cy, tab_sz, tab_sz), 1)

    def _draw_figma_button(
        self,
        rect: pygame.Rect,
        label: str,
        font: pygame.font.Font,
        bg_col: tuple[int, int, int] = (24, 26, 36),
        hover_col: tuple[int, int, int] = (48, 24, 32),
        border_col: tuple[int, int, int] = (142, 114, 62),
        text_col: tuple[int, int, int] = (245, 240, 228),
        radius: int = 8,
        align_left: bool = False,
    ):
        mx, my = pygame.mouse.get_pos()
        is_hover = rect.collidepoint(mx, my)
        fill = hover_col if is_hover else bg_col
        pygame.draw.rect(self.screen, (8, 10, 14), rect.move(0, 3), border_radius=radius)
        pygame.draw.rect(self.screen, fill, rect, border_radius=radius)
        bdr_c = (218, 172, 78) if is_hover else border_col
        pygame.draw.rect(self.screen, bdr_c, rect, 2 if is_hover else 1, border_radius=radius)

        if is_hover:
            tab_sz = 4
            pygame.draw.rect(self.screen, (218, 172, 78), (rect.left - 1, rect.top - 1, tab_sz, tab_sz))
            pygame.draw.rect(self.screen, (218, 172, 78), (rect.right - tab_sz + 1, rect.top - 1, tab_sz, tab_sz))

        # Strictly bound button text within its inner width
        max_tw = max(10, rect.width - 24)
        display_label = label
        if font.size(display_label)[0] > max_tw:
            while len(display_label) > 3 and font.size(display_label + "...")[0] > max_tw:
                display_label = display_label[:-1]
            display_label = display_label + "..."

        t_surf = font.render(display_label, True, (255, 248, 235) if is_hover else text_col)
        tx = rect.x + 14 if align_left else rect.centerx - t_surf.get_width() // 2
        ty = rect.centery - t_surf.get_height() // 2
        self.screen.blit(t_surf, (tx, ty))

    def _draw_gothic_plaque(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        is_active: bool,
        text: str,
        font: pygame.font.Font,
        hotkey_tag: str = "",
    ):
        if is_active:
            # Active carved stone plaque with top bevel highlight
            p_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            pygame.draw.rect(p_surf, (16, 18, 26, 245), (0, 0, rect.width, rect.height), border_radius=6)
            pygame.draw.line(p_surf, (48, 52, 68, 180), (4, 2), (rect.width - 5, 2), 1)
            surface.blit(p_surf, rect.topleft)

            # Double border
            pygame.draw.rect(surface, (68, 56, 48), rect, 2, border_radius=6)
            inner_r = rect.inflate(-6, -6)
            pygame.draw.rect(surface, (132, 118, 102), inner_r, 1, border_radius=4)

            # 4 Corner bracket tabs in antique gold
            tab_sz = 5
            corners = [
                (rect.left - 2, rect.top - 2),
                (rect.right - tab_sz + 2, rect.top - 2),
                (rect.left - 2, rect.bottom - tab_sz + 2),
                (rect.right - tab_sz + 2, rect.bottom - tab_sz + 2),
            ]
            for cx, cy in corners:
                pygame.draw.rect(surface, (218, 172, 78), (cx, cy, tab_sz, tab_sz))
                pygame.draw.rect(surface, (54, 42, 34), (cx, cy, tab_sz, tab_sz), 1)

            # Left filigree thorn/vine curls (Image 1 style)
            pygame.draw.lines(surface, (142, 126, 108), False, [
                (rect.left, rect.top + 14),
                (rect.left - 10, rect.top + 8),
                (rect.left - 16, rect.top - 2),
                (rect.left - 12, rect.top - 8),
            ], 2)
            pygame.draw.lines(surface, (142, 126, 108), False, [
                (rect.left, rect.bottom - 14),
                (rect.left - 10, rect.bottom - 8),
                (rect.left - 16, rect.bottom + 2),
                (rect.left - 12, rect.bottom + 8),
            ], 2)
            pygame.draw.circle(surface, (218, 172, 78), (rect.left - 12, rect.top - 8), 2)
            pygame.draw.circle(surface, (218, 172, 78), (rect.left - 12, rect.bottom + 8), 2)

            # Right circular medallion seal with cross (✕)
            c_x, c_y = rect.right - 24, rect.centery
            pygame.draw.circle(surface, (14, 16, 22), (c_x, c_y), 11)
            pygame.draw.circle(surface, (132, 118, 102), (c_x, c_y), 11, 1)
            pygame.draw.line(surface, (218, 172, 78), (c_x - 4, c_y - 4), (c_x + 4, c_y + 4), 2)
            pygame.draw.line(surface, (218, 172, 78), (c_x + 4, c_y - 4), (c_x - 4, c_y + 4), 2)

            # Active text in ivory
            t_fg = font.render(text, True, (252, 248, 240))
            surface.blit(t_fg, (rect.left + 26, rect.centery - t_fg.get_height() // 2))

            if hotkey_tag:
                hk_surf = self.font_xs.render(hotkey_tag, True, (218, 172, 78))
                surface.blit(hk_surf, (rect.right - 62, rect.centery - hk_surf.get_height() // 2))
        else:
            # Unselected clean gothic text
            t_fg = font.render(text, True, (172, 166, 156))
            surface.blit(t_fg, (rect.left + 26, rect.centery - t_fg.get_height() // 2))

            if hotkey_tag:
                hk_surf = self.font_xs.render(hotkey_tag, True, (120, 114, 106))
                surface.blit(hk_surf, (rect.right - 62, rect.centery - hk_surf.get_height() // 2))

            # Subtle horizontal divider line beneath
            div_y = rect.bottom + 4
            pygame.draw.line(surface, (54, 46, 42), (rect.left + 14, div_y), (rect.right - 14, div_y), 1)
            pygame.draw.circle(surface, (98, 86, 78), (rect.centerx, div_y), 1)

    def _draw_star_emblem(self, surface: pygame.Surface, cx: int, cy: int):
        pygame.draw.circle(surface, (142, 28, 38, 110), (cx, cy), 14, 1)
        pygame.draw.line(surface, (180, 140, 70), (cx - 10, cy), (cx + 10, cy), 1)
        pygame.draw.line(surface, (180, 140, 70), (cx, cy - 10), (cx, cy + 10), 1)
        pygame.draw.line(surface, (180, 140, 70), (cx - 6, cy - 6), (cx + 6, cy + 6), 1)
        pygame.draw.line(surface, (180, 140, 70), (cx + 6, cy - 6), (cx - 6, cy + 6), 1)

    def _render_wrapped_text(
        self,
        text: str,
        font: pygame.font.Font,
        color: tuple[int, int, int],
        x: int,
        y: int,
        max_width: int,
        line_spacing: int = 22,
        max_lines: int | None = None,
    ) -> int:
        """
        Renders multi-line text strictly constrained within max_width.
        Returns the bottom Y coordinate after the last line rendered.
        """
        words = text.split(" ")
        lines: list[str] = []
        current_line = ""

        for word in words:
            if not word:
                continue
            test_line = f"{current_line} {word}".strip() if current_line else word
            if font.size(test_line)[0] <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                if font.size(word)[0] > max_width:
                    cur_part = ""
                    for ch in word:
                        if font.size(cur_part + ch)[0] <= max_width:
                            cur_part += ch
                        else:
                            lines.append(cur_part)
                            cur_part = ch
                    current_line = cur_part
                else:
                    current_line = word

        if current_line:
            lines.append(current_line)

        if max_lines is not None and len(lines) > max_lines:
            lines = lines[:max_lines]
            last = lines[-1]
            while last and font.size(last + "...")[0] > max_width:
                last = last[:-1]
            lines[-1] = last + "..."

        cur_y = y
        for line in lines:
            t_surf = font.render(line, True, color)
            self.screen.blit(t_surf, (x, cur_y))
            cur_y += line_spacing

        return cur_y

    def show_toast(self, text: str, duration: float = 5.5):
        self.toast_msg = text
        self.toast_timer = duration

    def open_dialogue_with(self, npc: SimCharacter):
        self.talking_npc = npc
        self.npc_greeting, self.npc_options = self.world.get_npc_greeting_and_options(npc)
        self.typewriter_chars = 0.0
        self.custom_input = ""
        self.typing_custom = False
        self.active_modal = "DIALOGUE"

    def _on_rewind_finished(self):
        self.world.handle_cinematic_rewind_complete()
        p = self.world.get_player()
        self.cam_x = p.x - SCREEN_WIDTH * 0.5
        self.cam_y = p.y - SCREEN_HEIGHT * 0.5
        self.show_toast(
            f"Temporal Rewind: Consciousness awakened in Ashford Manor on Monday (Loop #{self.world.loop_id})!",
            duration=6.5,
        )

    def run(self, max_frames: int = None):
        running = True
        frame_count = 0

        while running:
            target_fps = self.settings.get("target_fps", 60) or FPS
            dt = min(0.05, self.clock.tick(target_fps) / 1000.0)
            frame_count += 1
            if max_frames and frame_count >= max_frames:
                break

            self._update_menu_particles(dt)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    self._handle_keydown(event)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self._handle_mouse_click(event.pos)

            # 1. Update and Render Active Death Cinematic Cutscene
            if self.death_engine.is_active:
                self.death_engine.update(dt)
                self._render_world()
                self.death_engine.render(self.screen)
                if self.toast_timer > 0:
                    self._render_toast()
                pygame.display.flip()
                continue

            # 2. Check if Fate Catastrophe occurred in the simulation
            if self.world.pending_fatal_death and not self.death_engine.is_active:
                p = self.world.get_player()
                psx = p.x - self.cam_x
                psy = p.y - self.cam_y
                self.active_modal = None
                self.death_engine.trigger_death(
                    death_type=self.world.fatal_death_type or "CARRIAGE_CRASH",
                    day_num=self.world.current_day,
                    day_name=self.world.get_day_name(),
                    loop_id=self.world.loop_id,
                    player_name=p.name,
                    player_screen_pos=(psx, psy),
                    on_complete_callback=self._on_rewind_finished,
                )
                continue

            if self.active_modal == "DIALOGUE":
                tw_speed = 9999.0 if self.settings.get("typewriter_speed") == "INSTANT" else (240.0 if self.settings.get("typewriter_speed") == "FAST" else 115.0)
                self.typewriter_chars = min(float(len(self.npc_greeting)), self.typewriter_chars + dt * tw_speed)

            if self.active_modal in ("MAIN_MENU", "SETTINGS", "FAMILY_SELECT", "LORE_PROLOGUE"):
                self._render()
                pygame.display.flip()
                continue

            move_dir = (0.0, 0.0)
            if self.active_modal is None:
                keys = pygame.key.get_pressed()
                dx = float(keys[pygame.K_d] or keys[pygame.K_RIGHT]) - float(keys[pygame.K_a] or keys[pygame.K_LEFT])
                dy = float(keys[pygame.K_s] or keys[pygame.K_DOWN]) - float(keys[pygame.K_w] or keys[pygame.K_UP])
                move_dir = (dx, dy)

            prev_scene = self.world.active_scene
            self.world.update(dt, move_dir)
            if self.world.active_scene != prev_scene:
                self._snap_camera_to_scene()
                if self.world.scene_banner_text:
                    self.show_toast(self.world.scene_banner_text, duration=4.5)

            if self.toast_timer > 0:
                self.toast_timer = max(0.0, self.toast_timer - dt)

            tx, ty = self._get_target_camera()
            self.cam_x += (tx - self.cam_x) * min(1.0, dt * 8.5)
            self.cam_y += (ty - self.cam_y) * min(1.0, dt * 8.5)

            self._render()
            pygame.display.flip()

        pygame.quit()

    def _get_target_camera(self) -> tuple[float, float]:
        player = self.world.get_player()
        if self.world.active_scene == "OVERWORLD":
            tx = max(0.0, min(WORLD_WIDTH - SCREEN_WIDTH, player.x - SCREEN_WIDTH * 0.5))
            ty = max(0.0, min(WORLD_HEIGHT - SCREEN_HEIGHT, player.y - SCREEN_HEIGHT * 0.5))
            return tx, ty

        b = self.world.buildings.get(self.world.active_scene)
        if b:
            rx, ry, rw, rh = b["rect"]
            room_cx = rx + rw * 0.5
            room_cy = ry + rh * 0.5
            focus_x = room_cx * 0.72 + player.x * 0.28
            focus_y = room_cy * 0.72 + player.y * 0.28
            return focus_x - SCREEN_WIDTH * 0.5, focus_y - SCREEN_HEIGHT * 0.5
        return player.x - SCREEN_WIDTH * 0.5, player.y - SCREEN_HEIGHT * 0.5

    def _snap_camera_to_scene(self):
        self.cam_x, self.cam_y = self._get_target_camera()

    def _select_campaign_protagonist_or_scenario(
        self, char_id: str = None, scenario_mode: str = None, start_run: bool = False
    ):
        new_char = char_id or self.world.player_char_id
        new_scen = scenario_mode or self.world.scenario_mode
        self.world.start_new_campaign(player_char_id=new_char, scenario_mode=new_scen)
        self._snap_camera_to_scene()
        if start_run:
            self.active_modal = "LORE_PROLOGUE"

    def _trigger_interact(self):
        kind, target = self.world.get_nearest_interactable(max_dist=108.0)
        if kind == "npc":
            self.open_dialogue_with(target)
        elif kind == "obj":
            msg = self.world.interact_with_object(target)
            self.show_toast(msg, duration=6.0)
        elif kind == "door_enter":
            msg = self.world.enter_building(target["id"])
            self._snap_camera_to_scene()
            self.show_toast(msg, duration=5.5)
        elif kind == "door_exit":
            msg = self.world.exit_building()
            self._snap_camera_to_scene()
            self.show_toast(msg, duration=4.5)
        else:
            if self.world.active_scene == "OVERWORLD":
                self.show_toast("Walk up to any House Front Door or Person and press [E]!")
            else:
                self.show_toast("Walk to any Person, Station, or Exit Door [E] (or press [BACKSPACE] to Step Outside)!")

    def _select_dialogue_choice_in_box(self, option_idx: int, custom_text: str = ""):
        if not self.talking_npc:
            return
        npc = self.talking_npc
        msg = self.world.select_dialogue_option(npc, option_idx, custom_text=custom_text)
        if npc.speech_bubble:
            self.npc_greeting = npc.speech_bubble
        else:
            self.npc_greeting = msg
        _, self.npc_options = self.world.get_npc_greeting_and_options(npc)
        self.typewriter_chars = 0.0
        self.typing_custom = False
        self.show_toast(msg, duration=5.5)

    def _handle_keydown(self, event: pygame.event.Event):
        if event.key == pygame.K_F11:
            try:
                pygame.display.toggle_fullscreen()
                curr_mode = "FULLSCREEN" if (self.screen.get_flags() & pygame.FULLSCREEN) else "WINDOWED"
                self.settings["display_mode"] = curr_mode
                self._save_settings()
            except Exception:
                pass
            return

        if self.active_modal == "MAIN_MENU":
            num_items = len(self._get_main_menu_items())
            if event.key in (pygame.K_UP, pygame.K_w):
                self.menu_selected_idx = (self.menu_selected_idx - 1) % num_items
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.menu_selected_idx = (self.menu_selected_idx + 1) % num_items
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._activate_main_menu_choice(self.menu_selected_idx)
            elif event.key == pygame.K_1:
                self._activate_main_menu_choice(0)
            elif event.key == pygame.K_2:
                self._activate_main_menu_choice(1)
            elif event.key == pygame.K_3:
                self._activate_main_menu_choice(2)
            elif event.key == pygame.K_4:
                self._activate_main_menu_choice(3)
            elif event.key == pygame.K_5:
                self._activate_main_menu_choice(4)
            elif event.key == pygame.K_6:
                self._activate_main_menu_choice(5)
            elif event.key == pygame.K_b:
                curr = self.settings.get("menu_background", "DUNWICK_MARKET")
                self.settings["menu_background"] = "BLOOD_MOON_ECLIPSE" if curr == "DUNWICK_MARKET" else "DUNWICK_MARKET"
                self._save_settings()
                self.show_toast(f"Menu Background: {self.settings['menu_background']}", duration=2.5)
            elif event.key == pygame.K_ESCAPE and self.in_game_paused:
                self.active_modal = None
            return

        if self.active_modal == "SETTINGS":
            if event.key in (pygame.K_TAB, pygame.K_RIGHT):
                self.settings_tab_idx = (self.settings_tab_idx + 1) % 5
            elif event.key == pygame.K_LEFT:
                self.settings_tab_idx = (self.settings_tab_idx - 1) % 5
            elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5):
                self.settings_tab_idx = event.key - pygame.K_1
            elif event.key == pygame.K_r:
                self.settings = dict(DEFAULT_SETTINGS)
                self._save_settings()
            elif event.key in (pygame.K_ESCAPE, pygame.K_RETURN):
                self._save_settings()
                self.active_modal = "MAIN_MENU" if not self.in_game_paused else None
            return

        if self.active_modal == "FAMILY_SELECT":
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.active_modal = "LORE_PROLOGUE"
            elif event.key == pygame.K_ESCAPE:
                self.active_modal = "MAIN_MENU"
            elif event.key == pygame.K_1:
                self._select_campaign_protagonist_or_scenario(char_id="arthur", start_run=False)
            elif event.key == pygame.K_2:
                self._select_campaign_protagonist_or_scenario(char_id="elena", start_run=False)
            elif event.key == pygame.K_3:
                self._select_campaign_protagonist_or_scenario(char_id="maya", start_run=False)
            elif event.key == pygame.K_4:
                self._select_campaign_protagonist_or_scenario(char_id="leo", start_run=False)
            elif event.key in (pygame.K_F1, pygame.K_q):
                self._select_campaign_protagonist_or_scenario(scenario_mode="WORLD_END", start_run=False)
            elif event.key in (pygame.K_F2, pygame.K_w):
                self._select_campaign_protagonist_or_scenario(scenario_mode="SELF_DEATH", start_run=False)
            elif event.key in (pygame.K_F3, pygame.K_e):
                self._select_campaign_protagonist_or_scenario(scenario_mode="LOVED_ONE", start_run=False)
            return

        if self.active_modal == "LORE_PROLOGUE":
            if event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_e, pygame.K_ESCAPE):
                self.has_seen_prologue = True
                self.active_modal = None
                p = self.world.get_player()
                self.show_toast(
                    f"DAY 1/7 (MONDAY): Playing as {p.name}. ONLY YOU know what is coming! Protect {self.world.get_protected_target_label()}!"
                )
            elif event.key == pygame.K_f:
                self.active_modal = "FAMILY_SELECT"
            return

        if self.active_modal == "DIALOGUE" and self.talking_npc:
            if event.key == pygame.K_ESCAPE:
                self.active_modal = None
                return

            if self.typing_custom:
                if event.key == pygame.K_RETURN:
                    self._select_dialogue_choice_in_box(0, custom_text=self.custom_input)
                elif event.key == pygame.K_BACKSPACE:
                    self.custom_input = self.custom_input[:-1]
                elif event.unicode and event.unicode.isprintable():
                    self.custom_input += event.unicode
                return

            if event.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4):
                idx = event.key - pygame.K_1
                if idx < len(self.npc_options):
                    self._select_dialogue_choice_in_box(idx)
            elif event.key in (pygame.K_SPACE, pygame.K_RETURN):
                if self.typewriter_chars < len(self.npc_greeting) - 2:
                    self.typewriter_chars = float(len(self.npc_greeting))
                else:
                    self.active_modal = None
            elif event.key == pygame.K_e:
                self.active_modal = None
            elif event.key == pygame.K_r:
                msg = self.world.trigger_deja_vu_on_npc(self.talking_npc)
                if self.talking_npc.speech_bubble:
                    self.npc_greeting = self.talking_npc.speech_bubble
                self.typewriter_chars = 0.0
                self.show_toast(msg, duration=6.0)
            elif event.key == pygame.K_t:
                self.typing_custom = True
                self.custom_input = ""
            return

        if self.active_modal in ("NOTEBOOK", "API_CONFIG"):
            if event.key in (pygame.K_ESCAPE, pygame.K_n):
                self.active_modal = None
            elif self.active_modal == "API_CONFIG":
                if event.key == pygame.K_TAB:
                    self.api_provider_choice = "openai" if self.api_provider_choice == "gemini" else "gemini"
                elif event.key == pygame.K_RETURN:
                    self.llm_broker.update_credentials(self.api_provider_choice, self.api_key_input)
                    self.show_toast(f"Saved {self.api_provider_choice.upper()} API Key!")
                    self.active_modal = None
                elif event.key == pygame.K_BACKSPACE:
                    self.api_key_input = self.api_key_input[:-1]
                elif event.unicode and event.unicode.isprintable():
                    self.api_key_input += event.unicode
            return

        if self.world.outcome_state is not None:
            if event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_l):
                if self.world.outcome_state == "VICTORY":
                    self.world.start_new_campaign(
                        player_char_id=self.world.player_char_id,
                        scenario_mode=self.world.scenario_mode,
                    )
                    self.active_modal = "FAMILY_SELECT"
                    self.show_toast("Started a Brand-New 7-Day Butterfly Campaign!")
                else:
                    self.world.start_loop(
                        player_char_id=self.world.player_char_id,
                        is_new_loop=True,
                        reset_to_monday=True,
                    )
                    self.show_toast(
                        f"Loop #{self.world.loop_id} Rewound to Monday! NPCs carry new Subconscious Echoes & Butterfly permutations!"
                    )
            return

        if event.key in (pygame.K_e, pygame.K_SPACE, pygame.K_RETURN):
            self._trigger_interact()
        elif event.key == pygame.K_F1:
            p = self.world.get_player()
            self.death_engine.trigger_death("CARRIAGE_CRASH", self.world.current_day, self.world.get_day_name(), self.world.loop_id, p.name, (p.x - self.cam_x, p.y - self.cam_y), self._on_rewind_finished)
            return
        elif event.key == pygame.K_F2:
            p = self.world.get_player()
            self.death_engine.trigger_death("ASSASSINATION_POISON", self.world.current_day, self.world.get_day_name(), self.world.loop_id, p.name, (p.x - self.cam_x, p.y - self.cam_y), self._on_rewind_finished)
            return
        elif event.key == pygame.K_F3:
            p = self.world.get_player()
            self.death_engine.trigger_death("FOOD_CHOKING", self.world.current_day, self.world.get_day_name(), self.world.loop_id, p.name, (p.x - self.cam_x, p.y - self.cam_y), self._on_rewind_finished)
            return
        elif event.key == pygame.K_F4:
            p = self.world.get_player()
            self.death_engine.trigger_death("GARGOYLE_COLLAPSE", self.world.current_day, self.world.get_day_name(), self.world.loop_id, p.name, (p.x - self.cam_x, p.y - self.cam_y), self._on_rewind_finished)
            return
        elif event.key == pygame.K_F5:
            p = self.world.get_player()
            self.death_engine.trigger_death("GALVANIC_ARC", self.world.current_day, self.world.get_day_name(), self.world.loop_id, p.name, (p.x - self.cam_x, p.y - self.cam_y), self._on_rewind_finished)
            return
        elif event.key in (pygame.K_BACKSPACE, pygame.K_ESCAPE) and self.world.active_scene != "OVERWORLD":
            msg = self.world.exit_building()
            self._snap_camera_to_scene()
            self.show_toast(msg, duration=4.5)
        elif event.key == pygame.K_ESCAPE:
            self.in_game_paused = True
            self.active_modal = "MAIN_MENU"
            return
        elif event.key == pygame.K_g:
            msg = self.world.advance_to_next_day()
            self.show_toast(msg, duration=6.5)
        elif event.key == pygame.K_f:
            self.active_modal = "FAMILY_SELECT"
        elif event.key == pygame.K_l:
            self.active_modal = "LORE_PROLOGUE"
        elif event.key == pygame.K_n:
            self.active_modal = "NOTEBOOK"
        elif event.key in (pygame.K_k, pygame.K_TAB):
            self.active_modal = "SETTINGS"
            self.settings_tab_idx = 0
        elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4):
            fam_ids = ["arthur", "elena", "maya", "leo"]
            chosen = fam_ids[event.key - pygame.K_1]
            msg = self.world.switch_active_family_member(chosen, allow_mid_run=False)
            self.show_toast(msg, duration=6.0)

    def _handle_mouse_click(self, pos: tuple[int, int]):
        mx, my = pos

        if self.active_modal == "MAIN_MENU":
            items = self._get_main_menu_items()
            for idx in range(len(items)):
                iy = 210 + idx * 58
                r = pygame.Rect(110, iy, 340, 50)
                if r.collidepoint(mx, my):
                    self.menu_selected_idx = idx
                    self._activate_main_menu_choice(idx)
                    return
            return

        if self.active_modal == "SETTINGS":
            panel = pygame.Rect(80, 40, SCREEN_WIDTH - 160, SCREEN_HEIGHT - 80)
            for t_i in range(5):
                t_rect = pygame.Rect(panel.x + 36 + t_i * 220, panel.y + 88, 205, 42)
                if t_rect.collidepoint(mx, my):
                    self.settings_tab_idx = t_i
                    return

            back_btn = pygame.Rect(panel.x + 36, panel.bottom - 60, 240, 44)
            if back_btn.collidepoint(mx, my):
                self._save_settings()
                self.active_modal = "MAIN_MENU" if not self.in_game_paused else None
                return

            restore_btn = pygame.Rect(panel.centerx - 120, panel.bottom - 60, 240, 44)
            if restore_btn.collidepoint(mx, my):
                self.settings = dict(DEFAULT_SETTINGS)
                self._save_settings()
                return

            apply_btn = pygame.Rect(panel.right - 276, panel.bottom - 60, 240, 44)
            if apply_btn.collidepoint(mx, my):
                self._save_settings()
                self.active_modal = "MAIN_MENU" if not self.in_game_paused else None
                return

            self._handle_settings_tab_clicks(mx, my, panel)
            return

        if self.active_modal == "FAMILY_SELECT":
            # Scenario Mode Cards (Row 1)
            scen_keys = ["WORLD_END", "SELF_DEATH", "LOVED_ONE"]
            for idx, skey in enumerate(scen_keys):
                if pygame.Rect(110 + idx * 385, 130, 365, 128).collidepoint(mx, my):
                    self._select_campaign_protagonist_or_scenario(scenario_mode=skey, start_run=False)
                    return

            # Family Protagonist Cards (Row 2)
            family_ids = ["arthur", "elena", "maya", "leo"]
            for idx, fid in enumerate(family_ids):
                if pygame.Rect(110 + idx * 290, 290, 270, 385).collidepoint(mx, my):
                    self._select_campaign_protagonist_or_scenario(char_id=fid, start_run=False)
                    return

            # Back to Main Menu Button
            if pygame.Rect(110, 698, 160, 54).collidepoint(mx, my):
                self.active_modal = "MAIN_MENU"
                return

            # Start Campaign Button
            if pygame.Rect(290, 698, 810, 54).collidepoint(mx, my):
                self.active_modal = "LORE_PROLOGUE"
                return
            return

        if self.active_modal == "LORE_PROLOGUE":
            if pygame.Rect(400, 708, 560, 56).collidepoint(mx, my):
                self.has_seen_prologue = True
                self.active_modal = None
                p = self.world.get_player()
                self.show_toast(
                    f"DAY 1/7 (MONDAY): Playing as {p.name}. Protect {self.world.get_protected_target_label()}!"
                )
                return
            if pygame.Rect(125, 708, 245, 56).collidepoint(mx, my):
                self.active_modal = "FAMILY_SELECT"
                return
            return

        if self.active_modal == "DIALOGUE" and self.talking_npc:
            for idx in range(len(self.npc_options[:4])):
                if pygame.Rect(245, 686 + idx * 34, 825, 30).collidepoint(mx, my):
                    self._select_dialogue_choice_in_box(idx)
                    return
            if pygame.Rect(1085, 686, 200, 64).collidepoint(mx, my):
                msg = self.world.trigger_deja_vu_on_npc(self.talking_npc)
                if self.talking_npc.speech_bubble:
                    self.npc_greeting = self.talking_npc.speech_bubble
                self.typewriter_chars = 0.0
                self.show_toast(msg, duration=6.0)
                return
            if pygame.Rect(1085, 758, 200, 30).collidepoint(mx, my):
                self.typing_custom = True
                self.custom_input = ""
                return
            if pygame.Rect(1085, 794, 200, 32).collidepoint(mx, my):
                self.active_modal = None
                return
            return

        if self.active_modal == "NOTEBOOK":
            if not pygame.Rect(140, 75, 1080, 710).collidepoint(mx, my):
                self.active_modal = None
            return

        # Top Floating HUD Clicks
        if my <= 68:
            if pygame.Rect(980, 12, 134, 44).collidepoint(mx, my):
                msg = self.world.advance_to_next_day()
                self.show_toast(msg, duration=6.0)
                return
            if pygame.Rect(1122, 12, 114, 44).collidepoint(mx, my):
                self.active_modal = "NOTEBOOK"
                return
            if pygame.Rect(1244, 12, 102, 44).collidepoint(mx, my):
                self.active_modal = "FAMILY_SELECT"
                return
            return

        if self.active_modal is None:
            # Check Interior Scene "Step Outside [Bksp]" banner button click
            if self.world.active_scene != "OVERWORLD" and pygame.Rect(1040, 70, 306, 36).collidepoint(mx, my):
                msg = self.world.exit_building()
                self._snap_camera_to_scene()
                self.show_toast(msg, duration=4.5)
                return

            wx = mx + self.cam_x
            wy = my + self.cam_y
            player = self.world.get_player()
            for char in self.world.characters.values():
                if (
                    not char.is_player
                    and not char.arrested
                    and self.world.get_char_scene(char) == self.world.active_scene
                    and math.hypot(wx - char.x, wy - (char.y - 24)) <= 48.0
                ):
                    if math.hypot(player.x - char.x, player.y - char.y) <= 135.0:
                        self.open_dialogue_with(char)
                    else:
                        self.show_toast(f"Walk closer to {char.name} to converse!")
                    return

            # Click on a House Front Door (on Overworld) or Interior Exit Door (when inside)
            if self.world.active_scene == "OVERWORLD":
                for b in BUILDINGS:
                    if math.hypot(wx - b["door_x"], wy - b["door_y"]) <= 84.0:
                        if math.hypot(player.x - b["door_x"], player.y - b["door_y"]) <= 155.0:
                            msg = self.world.enter_building(b["id"])
                            self._snap_camera_to_scene()
                            self.show_toast(msg, duration=5.5)
                        else:
                            self.show_toast(f"Walk closer to {b['name']}'s front door to enter!")
                        return
            else:
                b = self.world.buildings.get(self.world.active_scene)
                if b and math.hypot(wx - b["door_x"], wy - b["door_y"]) <= 84.0:
                    msg = self.world.exit_building()
                    self._snap_camera_to_scene()
                    self.show_toast(msg, duration=4.5)
                    return

    # =========================================================================
    # 2.5D MEDIEVAL-STEAMPUNK WORLD & SCENE-SWITCHING RENDERING PIPELINE
    # =========================================================================
    def _render(self):
        if self.active_modal == "MAIN_MENU":
            self._render_main_menu()
            return
        elif self.active_modal == "SETTINGS":
            self._render_settings_modal()
            return

        self._render_world()
        self._render_top_bar()

        if self.toast_timer > 0 and self.toast_msg and self.active_modal is None:
            self._render_toast()

        if self.active_modal == "DIALOGUE":
            self._render_bottom_dialogue_box()
        elif self.active_modal == "FAMILY_SELECT":
            self._render_family_select_modal()
        elif self.active_modal == "LORE_PROLOGUE":
            self._render_lore_prologue_modal()
        elif self.active_modal == "NOTEBOOK":
            self._render_notebook_modal()
        elif self.active_modal == "API_CONFIG":
            self._render_api_config_modal()
        elif self.world.outcome_state is not None:
            self._render_outcome_modal()

    def _render_world(self):
        cx = int(self.cam_x)
        cy = int(self.cam_y)
        t_sec = pygame.time.get_ticks() / 1000.0
        active_scene = self.world.active_scene

        player = self.world.get_player()
        protected_id = self.world.get_protected_target_id()
        sc = self.world.scenario
        deduced = self.world.zone_state.get("threat_deduced", False)
        catalyst_id = sc.get("saboteur_id") if deduced else None

        renderables = []

        if active_scene == "OVERWORLD":
            # -----------------------------------------------------------------
            # OVERWORLD SCENE: Exterior 2.5D Houses, Cobblestone Streets & Outdoor Townsfolk
            # -----------------------------------------------------------------
            view_rect = pygame.Rect(cx, cy, SCREEN_WIDTH, SCREEN_HEIGHT)
            self.screen.blit(self.art_engine.world_ground_surface, (0, 0), area=view_rect)

            for b in BUILDINGS:
                is_north = b["door_y"] > b["rect"][1] + b["rect"][3] // 2
                sort_y = (b["door_y"] - 6) if is_north else (b["door_y"] - 24)
                renderables.append((sort_y, "house", b))

            for tx, ty in self.trees:
                renderables.append((ty + 18, "tree", (tx, ty)))

            for ptype, px, py in self.art_engine.street_props:
                renderables.append((py, "prop", (ptype, px, py)))

            for veh in self.world.grid_engine.vehicles:
                renderables.append((veh.y + 12, "vehicle", veh))

            for char in self.world.characters.values():
                if not char.arrested and self.world.get_char_scene(char) == "OVERWORLD":
                    renderables.append((char.y, "char", char))
        else:
            # -----------------------------------------------------------------
            # INTERIOR ROOM SCENE: Cutaway 2.5D Diorama & Only People Inside Building!
            # -----------------------------------------------------------------
            self.screen.fill((10, 12, 20))
            b = self.world.buildings.get(active_scene)
            if b:
                rx, ry, rw, rh = b["rect"]
                room_surf = self.art_engine.interior_room_surfaces.get(active_scene)
                if room_surf is not None:
                    self.screen.blit(room_surf, (rx - INTERIOR_PAD - cx, ry - INTERIOR_PAD - cy))

                # Glowing Interior Exit Door Beacon at `(door_x, door_y)`
                door_sx = int(b["door_x"] - self.cam_x)
                door_sy = int(b["door_y"] - self.cam_y)
                pulse = int(6 + math.sin(t_sec * 5.2) * 4)
                exit_ring = pygame.Surface((148, 38), pygame.SRCALPHA)
                pygame.draw.ellipse(exit_ring, (95, 238, 172, 68), (8 - pulse // 2, 4, 132 + pulse, 28))
                pygame.draw.ellipse(exit_ring, (95, 238, 172, 225), (8 - pulse // 2, 4, 132 + pulse, 28), 2)
                self.screen.blit(exit_ring, (door_sx - 74, door_sy - 18))

                for f in b["furniture"]:
                    fx, fy, fw, fh = f["rect"]
                    sort_y = fy if "Gym Court" in f["name"] else (fy + fh - 6)
                    renderables.append((sort_y, "furniture", f))

            for wobj in self.world.objects.values():
                if wobj.get("building") == active_scene:
                    renderables.append((wobj["y"] + 4, "quest_obj", wobj))

            for char in self.world.characters.values():
                if not char.arrested and self.world.get_char_scene(char) == active_scene:
                    renderables.append((char.y, "char", char))

        renderables.sort(key=lambda item: item[0])

        self.world.particles.update_and_draw(self.screen, self.cam_x, self.cam_y, 1.0 / FPS)

        for _, kind, obj in renderables:
            if kind == "house":
                b = obj
                occupants = self.world.get_occupants(b["id"])
                near_door = math.hypot(player.x - b["door_x"], player.y - b["door_y"]) <= 105.0
                self.art_engine.draw_exterior_house(
                    surface=self.screen,
                    b=b,
                    cam_x=self.cam_x,
                    cam_y=self.cam_y,
                    t_sec=t_sec,
                    occupants=occupants,
                    protected_id=protected_id if self.world.scenario_mode == "LOVED_ONE" else None,
                    catalyst_id=catalyst_id,
                    player_near_door=near_door,
                    font_sm=self.font_sm,
                    font_xs=self.font_xs,
                )
            elif kind == "furniture":
                self.art_engine.draw_25d_furniture(self.screen, obj, self.cam_x, self.cam_y, t_sec)
            elif kind == "quest_obj":
                is_haz = deduced and obj["id"] in (sc.get("hazard_obj"), sc.get("alt_obj"))
                self.art_engine.draw_quest_object(
                    self.screen, obj, self.cam_x, self.cam_y, t_sec, is_active_hazard=is_haz
                )
            elif kind == "tree":
                tx, ty = obj
                self.screen.blit(self.art_engine.tree_sprite, (int(tx - self.cam_x - 59), int(ty - self.cam_y - 116)))
            elif kind == "prop":
                ptype, px, py = obj
                self.art_engine.draw_street_prop(self.screen, ptype, px, py, self.cam_x, self.cam_y, t_sec)
            elif kind == "vehicle":
                obj.draw(self.screen, self.cam_x, self.cam_y)
            elif kind == "char":
                char = obj
                has_anchor = char.memory_store.has_anchored_memory()
                is_loved = self.world.scenario_mode == "LOVED_ONE" and char.id == protected_id

                char.rig.draw(
                    surface=self.screen,
                    wx=char.x,
                    wy=char.y,
                    cam_x=self.cam_x,
                    cam_y=self.cam_y,
                    is_player=char.is_player,
                    has_quest_marker=None,
                    has_memory_anchor=has_anchor,
                    is_protected_loved_one=is_loved,
                )

        # Apply Octopath Traveler HD-2D Dynamic Point Lighting, Volumetric God-Rays & Tilt-Shift Vignette Pass!
        loved_char = (
            self.world.characters.get(protected_id)
            if (self.world.scenario_mode == "LOVED_ONE" and protected_id in self.world.characters)
            else None
        )
        loved_in_same_scene = loved_char is not None and self.world.get_char_scene(loved_char) == active_scene
        active_haz_id = sc.get("hazard_obj") if deduced else None
        sim_mins = 480.0 + (self.world.elapsed_time / 180.0) * 720.0
        self.art_engine.render_hd2d_lighting_pass(
            screen=self.screen,
            cam_x=self.cam_x,
            cam_y=self.cam_y,
            sim_minutes=sim_mins,
            player_wx=player.x,
            player_wy=player.y,
            loved_wx=loved_char.x if loved_in_same_scene else None,
            loved_wy=loved_char.y if loved_in_same_scene else None,
            world_objects=list(self.world.objects.values()),
            active_hazard_obj_id=active_haz_id,
            t_sec=t_sec,
            active_scene=active_scene,
        )

        # Render crisp HD-2D UI Nameplates & Speech Bubbles ONLY for characters in the active scene!
        for char in self.world.characters.values():
            if char.arrested or self.world.get_char_scene(char) != active_scene:
                continue
            sx, sy = int(char.x - self.cam_x), int(char.y - self.cam_y)
            if sx < -80 or sx > SCREEN_WIDTH + 80 or sy < -80 or sy > SCREEN_HEIGHT + 80:
                continue
            has_grudge = player.id in char.grudges
            is_loved = self.world.scenario_mode == "LOVED_ONE" and char.id == protected_id

            short_n = char.name.split("(")[0].strip()
            if char.is_player:
                short_n = f"YOU: {short_n}"
            elif is_loved:
                short_n = f"PROTECT: {short_n}"

            ncol = (
                COLORS["gold"]
                if char.is_player
                else (
                    COLORS["cyan"]
                    if is_loved
                    else (COLORS["red"] if has_grudge else (COLORS["parchment"] if char.is_family else COLORS["white"]))
                )
            )
            nlbl = self.font_xs.render(short_n, True, ncol)
            npill = pygame.Rect(sx - nlbl.get_width() // 2 - 6, sy + 7, nlbl.get_width() + 12, 18)
            pygame.draw.rect(self.screen, (14, 16, 24), npill, border_radius=6)
            pygame.draw.rect(
                self.screen,
                (168, 134, 68) if (char.is_player or is_loved) else (58, 64, 82),
                npill,
                1,
                border_radius=6,
            )
            self.screen.blit(nlbl, (sx - nlbl.get_width() // 2, sy + 8))

            if char.speech_bubble and self.active_modal != "DIALOGUE":
                self._draw_small_bubble(sx, sy - 76, char.speech_bubble)

        # When inside a building, render the Interior Scene Header Banner & `[Bksp] Step Outside` button!
        if active_scene != "OVERWORLD":
            b = self.world.buildings.get(active_scene)
            if b:
                occupants = self.world.get_occupants(active_scene)
                occ_str = (
                    ", ".join(c.name.split("(")[0].strip() for c in occupants[:4])
                    if occupants
                    else "No other townsfolk inside right now"
                )
                hdr_rect = pygame.Rect(14, 70, 1018, 36)
                self._draw_figma_card(hdr_rect, bg_rgba=(18, 22, 34, 240), border_col=COLORS["gold"], radius=12)
                hdr_txt = f"INTERIOR SCENE: {b['name']}   •   People in Building ({len(occupants)}): {occ_str}"
                self.screen.blit(self.font_sm.render(hdr_txt[:98], True, COLORS["gold"]), (28, 79))

                self._draw_figma_button(
                    pygame.Rect(1040, 70, 306, 36),
                    "[Bksp / Door] Step Outside to Overworld",
                    self.font_xs,
                    bg_col=(36, 78, 62),
                    hover_col=(48, 108, 86),
                    border_col=COLORS["green"],
                    radius=10,
                )

        # Render Contextual Interaction Prompt (`[E] Enter House`, `[E] Step Outside`, `[E] Converse`, `[E] Inspect`)
        nearest_kind, nearest_target = self.world.get_nearest_interactable(max_dist=108.0)
        if nearest_target is not None and self.active_modal is None:
            if nearest_kind == "npc":
                tx_p, ty_p = int(nearest_target.x - self.cam_x), int(nearest_target.y - self.cam_y - 70)
                ptxt = f"[E] Converse with {nearest_target.name.split('(')[0].strip()}"
                b_col = COLORS["gold"]
            elif nearest_kind == "obj":
                tx_p, ty_p = int(nearest_target["x"] - self.cam_x), int(nearest_target["y"] - self.cam_y - 44)
                ptxt = f"[E] Inspect {nearest_target['name']}"
                b_col = COLORS["gold"]
            elif nearest_kind == "door_enter":
                tx_p, ty_p = int(nearest_target["door_x"] - self.cam_x), int(nearest_target["door_y"] - self.cam_y - 42)
                occ_cnt = len(self.world.get_occupants(nearest_target["id"]))
                ptxt = f"[E / Walk In] Enter {nearest_target['name']} ({occ_cnt} inside)"
                b_col = COLORS["green"]
            else:
                tx_p, ty_p = int(nearest_target["door_x"] - self.cam_x), int(nearest_target["door_y"] - self.cam_y - 42)
                ptxt = "[E / Walk Out] Step Outside to Dunwick-on-Severn Overworld"
                b_col = COLORS["green"]
            psurf = self.font_sm.render(ptxt, True, b_col)
            ppill = pygame.Rect(tx_p - psurf.get_width() // 2 - 12, ty_p - 6, psurf.get_width() + 24, 28)
            self._draw_figma_card(ppill, bg_rgba=(16, 18, 28, 244), border_col=b_col, radius=14, shadow_offset=4)
            self.screen.blit(psurf, (tx_p - psurf.get_width() // 2, ty_p - 1))

    def _draw_small_bubble(self, x: int, y: int, text: str):
        short = text[:54] + ("..." if len(text) > 54 else "")
        surf = self.font_xs.render(short, True, COLORS["white"])
        w = surf.get_width() + 18
        rect = pygame.Rect(x - w // 2, y - 24, w, 24)
        self._draw_figma_card(rect, bg_rgba=(20, 24, 36, 236), border_col=(158, 128, 72), radius=10, border_w=1, shadow_offset=3)
        self.screen.blit(surf, (x - surf.get_width() // 2, y - 19))

    # =========================================================================
    # MINIMALIST 1924 CHRONOMETER & 7-DAY EVENT PROGRESSION TOP BAR
    # =========================================================================
    def _render_top_bar(self):
        obj_info = self.world.get_current_objective()
        foiled = self.world.zone_state.get("day_threat_foiled", False)
        player = self.world.get_player()
        rem = int(self.world.time_remaining)
        clock_str = self.world.get_clock_string()

        # 1. Main Minimalist Translucent Frosted Glass Bar
        bar_rect = pygame.Rect(14, 8, SCREEN_WIDTH - 28, 54)
        self._draw_figma_card(bar_rect, bg_rgba=(14, 16, 24, 235), border_col=(142, 114, 62), radius=14, border_w=1, shadow_offset=4)

        # 2. Left Section: Sole-Knower Protagonist Badge & Composure
        p_first = player.name.split("(")[0].strip().upper()
        p_badge = f"{p_first} • LOOP #{self.world.loop_id} • SOLE-KNOWER"
        self.screen.blit(self.font_sm.render(p_badge, True, COLORS["gold"]), (26, 14))

        item_txt = self.world.held_counter_item or ("Earl Grey Tea" if self.world.has_warm_coffee else "No Tool")
        comp_col = COLORS["green"] if self.world.credibility >= 60 else COLORS["red"]
        sub_badge = f"Composure: {self.world.credibility}%  •  Tool: {item_txt[:18]}"
        self.screen.blit(self.font_xs.render(sub_badge, True, comp_col), (26, 36))

        # 3. Center Section: CLEAR 7-DAY BUTTERFLY PROGRESSION TIMELINE
        # Displays: Mon -> Tue -> Wed -> Thu -> Fri -> Sat -> Sun with threat vectors & status
        day_blueprints = [
            ("Mon", "Poison Tea"),
            ("Tue", "Steam Lorry"),
            ("Wed", "Mutton Pie"),
            ("Thu", "Gargoyle"),
            ("Fri", "Galvanic Arc"),
            ("Sat", "Coal Damp"),
            ("Sun", "7th Bell"),
        ]
        curr_d = self.world.current_day
        timeline_x0 = 310
        node_spacing = 98

        for idx, (d_abbr, d_hazard) in enumerate(day_blueprints):
            day_num = idx + 1
            nx = timeline_x0 + idx * node_spacing
            ny = 22

            # Connecting line to next day
            if idx < 6:
                line_col = COLORS["green"] if day_num < curr_d else ((188, 142, 62) if day_num == curr_d else (62, 58, 68))
                pygame.draw.line(self.screen, line_col, (nx + 40, ny + 8), (nx + node_spacing - 6, ny + 8), 2)

            if day_num < curr_d:
                # Survived Day
                pygame.draw.circle(self.screen, (28, 98, 62), (nx + 14, ny + 8), 10)
                pygame.draw.circle(self.screen, COLORS["green"], (nx + 14, ny + 8), 10, 1)
                chk = self.font_xs.render("✓", True, COLORS["white"])
                self.screen.blit(chk, (nx + 10, ny + 1))
                lbl = self.font_xs.render(d_abbr, True, COLORS["green"])
                self.screen.blit(lbl, (nx + 28, ny + 1))
                hz = self.font_xs.render(d_hazard[:9], True, (145, 215, 165))
                self.screen.blit(hz, (nx, ny + 18))
            elif day_num == curr_d:
                # Active Today
                active_pill = pygame.Rect(nx - 4, ny - 4, 88, 38)
                pill_bg = (38, 78, 52) if foiled else (58, 42, 28)
                pill_bdr = COLORS["green"] if foiled else COLORS["gold"]
                pygame.draw.rect(self.screen, pill_bg, active_pill, border_radius=8)
                pygame.draw.rect(self.screen, pill_bdr, active_pill, 2, border_radius=8)
                status_txt = "FOILED ✓" if foiled else clock_str
                self.screen.blit(self.font_xs.render(f"{d_abbr} • {status_txt}", True, pill_bdr), (nx + 2, ny - 1))
                self.screen.blit(self.font_xs.render(d_hazard[:11], True, COLORS["white"]), (nx + 2, ny + 17))
            else:
                # Future Locked Day
                pygame.draw.circle(self.screen, (34, 36, 46), (nx + 14, ny + 8), 8)
                pygame.draw.circle(self.screen, (72, 68, 78), (nx + 14, ny + 8), 8, 1)
                lbl = self.font_xs.render(d_abbr, True, COLORS["text_muted"])
                self.screen.blit(lbl, (nx + 28, ny + 1))
                hz = self.font_xs.render(d_hazard[:9], True, (95, 90, 102))
                self.screen.blit(hz, (nx, ny + 18))

        # 4. Right Section: Action Controls
        self._draw_figma_button(
            pygame.Rect(1005, 13, 115, 42),
            f"[G] Next Day" if foiled else f"Day {self.world.current_day}/7",
            self.font_xs,
            bg_col=(28, 98, 62) if foiled else (32, 34, 48),
            hover_col=(38, 128, 82) if foiled else (44, 48, 66),
            border_col=COLORS["green"] if foiled else (98, 92, 82),
            radius=8,
        )
        self._draw_figma_button(
            pygame.Rect(1126, 13, 108, 42),
            f"[N] Journal",
            self.font_xs,
            bg_col=(28, 36, 54),
            border_col=COLORS["cyan"],
            radius=8,
        )
        self._draw_figma_button(
            pygame.Rect(1240, 13, 94, 42),
            "[F] Fate",
            self.font_xs,
            bg_col=(44, 34, 52),
            border_col=COLORS["gold"],
            radius=8,
        )

        # 5. Minimalist Bottom Control Strip (Only drawn when no modal is active)
        if self.active_modal is None:
            prompt_str = "[WASD] Walk  |  [E] Interact  |  [G] Next Day  |  [N] Foresight Journal  |  [F1-F5] Death FX  |  [ESC] Exit"
            p_surf = self.font_xs.render(prompt_str, True, (188, 178, 162))
            pw, ph = p_surf.get_width() + 24, 24
            strip_rect = pygame.Rect((SCREEN_WIDTH - pw) // 2, SCREEN_HEIGHT - 32, pw, ph)
            pygame.draw.rect(self.screen, (12, 14, 20, 210), strip_rect, border_radius=10)
            pygame.draw.rect(self.screen, (108, 86, 48), strip_rect, 1, border_radius=10)
            self.screen.blit(p_surf, ((SCREEN_WIDTH - p_surf.get_width()) // 2, SCREEN_HEIGHT - 28))

    def _render_toast(self):
        surf = self.font_sm.render(self.toast_msg, True, COLORS["white"])
        w = min(SCREEN_WIDTH - 40, surf.get_width() + 36)
        rect = pygame.Rect((SCREEN_WIDTH - w) // 2, SCREEN_HEIGHT - 58, w, 40)
        self._draw_figma_card(rect, bg_rgba=(16, 18, 28, 244), border_col=COLORS["gold"], radius=20)
        self.screen.blit(surf, (rect.x + 18, rect.y + 11))

    def _render_bottom_dialogue_box(self):
        npc = self.talking_npc
        if not npc:
            return

        player = self.world.get_player()
        fam_id = player.id

        box = pygame.Rect(46, 530, 1268, 312)
        self._draw_figma_card(
            box, bg_rgba=(16, 19, 30, 248), border_col=COLORS["ui_border"], radius=20, border_w=2, shadow_offset=8
        )

        p_rect = pygame.Rect(72, 554, 142, 142)
        t_phase = pygame.time.get_ticks() / 1000.0
        is_typing = self.typewriter_chars < len(self.npc_greeting)
        draw_character_portrait(self.screen, p_rect, npc.spec, anim_phase=(t_phase if is_typing else 0.0))

        rel_status = npc.get_relationship_status(fam_id)
        rel_col = (
            COLORS["red"]
            if "ALARMED" in rel_status
            else (COLORS["gold"] if npc.is_family else (COLORS["green"] if "CONFIDANT" in rel_status else COLORS["cyan"]))
        )
        r_tag = self.font_xs.render(rel_status, True, rel_col)
        self.screen.blit(r_tag, (p_rect.centerx - r_tag.get_width() // 2, 704))

        rapport_val = npc.get_rapport(fam_id)
        bar_bg = pygame.Rect(76, 724, 134, 8)
        pygame.draw.rect(self.screen, (36, 40, 56), bar_bg, border_radius=4)
        pygame.draw.rect(self.screen, rel_col, (76, 724, int(1.34 * rapport_val), 8), border_radius=4)
        trust_tag = self.font_xs.render(
            f"Rapport: {rapport_val}% | Composure: {self.world.credibility}%", True, COLORS["text_dim"]
        )
        self.screen.blit(trust_tag, (p_rect.centerx - trust_tag.get_width() // 2, 736))

        x_text = 245
        name_hdr = self.font_gothic_lg.render(f"{npc.name}  —  {npc.role}", True, COLORS["gold"])
        self.screen.blit(name_hdr, (x_text, 548))

        sched_hdr = self.font_xs.render(
            f"{self.world.get_day_name()} ({self.world.get_clock_string()}): {npc.current_schedule_label}  •  Sole Knower: {player.name}",
            True,
            COLORS["cyan"],
        )
        self.screen.blit(sched_hdr, (x_text, 576))

        msg_panel = pygame.Rect(x_text, 598, 825, 80)
        pygame.draw.rect(self.screen, (24, 28, 42), msg_panel, border_radius=10)
        pygame.draw.rect(self.screen, (118, 96, 58), msg_panel, 1, border_radius=10)

        visible_text = self.npc_greeting[: int(self.typewriter_chars)]
        self._render_wrapped_text(
            visible_text, self.font_md, COLORS["white"], x_text + 14, 606, max_width=msg_panel.width - 28, line_spacing=23, max_lines=3
        )

        if self.typing_custom:
            inp_box = pygame.Rect(x_text, 700, 825, 46)
            pygame.draw.rect(self.screen, (12, 15, 22), inp_box, border_radius=8)
            pygame.draw.rect(self.screen, COLORS["green"], inp_box, 2, border_radius=8)
            self.screen.blit(
                self.font_md.render(f"Speak to {npc.name.split('(')[0].strip()} > {self.custom_input}_", True, COLORS["white"]),
                (x_text + 14, 712),
            )
            self.screen.blit(
                self.font_xs.render(
                    "Press [ENTER] to Speak (Avoid raving without proof!)   |   [ESC] Cancel", True, COLORS["text_dim"]
                ),
                (x_text, 758),
            )
        else:
            for idx, opt_txt in enumerate(self.npc_options[:4]):
                btn = pygame.Rect(x_text, 686 + idx * 34, 825, 30)
                is_intervene = idx == 3
                self._draw_figma_button(
                    btn,
                    f"[{idx + 1}]  {opt_txt}",
                    self.font_sm,
                    bg_col=(58, 34, 38) if is_intervene else (28, 34, 50),
                    hover_col=(84, 46, 52) if is_intervene else (44, 54, 78),
                    border_col=COLORS["gold"] if is_intervene else COLORS["cyan"],
                    radius=8,
                    align_left=True,
                )

        r_btn = pygame.Rect(1085, 686, 200, 64)
        self._draw_figma_button(
            r_btn,
            f"[R] Premonition ({self.world.deja_vu_charges})",
            self.font_sm,
            bg_col=(26, 62, 50),
            hover_col=(38, 86, 68),
            border_col=COLORS["green"],
            text_col=COLORS["green"],
            radius=10,
        )
        self._draw_figma_button(
            pygame.Rect(1085, 758, 200, 30),
            "[T] Custom AI Speech",
            self.font_xs,
            bg_col=(30, 42, 64),
            border_col=COLORS["cyan"],
            radius=8,
        )
        self._draw_figma_button(
            pygame.Rect(1085, 794, 200, 32),
            "[ESC] Step Away",
            self.font_xs,
            bg_col=(54, 32, 40),
            border_col=COLORS["red"],
            radius=8,
        )

    # =========================================================================
    # BLOODBORNE DARK MAIN MENU & R.E.P.O. SPECIFICATION SETTINGS MATRIX
    # =========================================================================
    def _activate_main_menu_choice(self, idx: int):
        if idx == 0:
            # START NEW CAMPAIGN / NEW GAME
            self.active_modal = "FAMILY_SELECT"
        elif idx == 1:
            # CONTINUE TIMELINE
            self.active_modal = None
            self.in_game_paused = False
            p = self.world.get_player()
            self.show_toast(
                f"TIMELINE ACTIVE: Playing as {p.name} (Day {self.world.current_day}/7 • {self.world.get_day_name()})",
                duration=5.0,
            )
        elif idx == 2:
            # THE THREE FATES (Scenario Selection)
            self.active_modal = "FAMILY_SELECT"
        elif idx == 3:
            # OPTIONS & SETTINGS
            self.active_modal = "SETTINGS"
            self.settings_tab_idx = 0
        elif idx == 4:
            # FORESIGHT CODEX & JOURNAL
            self.active_modal = "NOTEBOOK"
        elif idx == 5:
            # QUIT TO DESKTOP
            pygame.event.post(pygame.event.Event(pygame.QUIT))

    def _get_main_menu_items(self) -> list[tuple[str, str, str]]:
        return [
            ("New Game", "Initiate a new 7-Day Time Loop • Choose Scenario & Family Hero", "[1]"),
            ("Continue", f"Resume {self.world.get_day_name()} (Loop #{self.world.loop_id})", "[2]"),
            ("The Three Fates", "The Doomsday Clock • The Grim Decree • The Thread of Fate", "[3]"),
            ("Options", "Graphics, Audio, Gameplay, Controls & AI Broker", "[4]"),
            ("Foresight Codex", "Review 7-Day Butterfly Chain, Death Log & Clues", "[5]"),
            ("Quit Game", "Preserve Timeline Progress & Exit to Desktop", "[ESC]"),
        ]

    def _render_main_menu(self):
        # 1. Background Surface (Dunwick Market Square or Blood Moon Eclipse)
        active_bg_key = self.settings.get("menu_background", "DUNWICK_MARKET")
        bg_surf = self.menu_bgs.get(active_bg_key) or self.menu_bgs.get("BLOOD_MOON_ECLIPSE")
        if bg_surf:
            self.screen.blit(bg_surf, (0, 0))
        else:
            self.screen.fill((10, 11, 15))

        # 2. Left Atmospheric Shadow Gradient (Guarantees menu text legibility)
        shadow = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        for x in range(int(SCREEN_WIDTH * 0.46)):
            factor = x / (SCREEN_WIDTH * 0.46)
            alpha = int(235 * (1.0 - factor * factor))
            pygame.draw.line(shadow, (8, 9, 14, alpha), (x, 0), (x, SCREEN_HEIGHT))
        self.screen.blit(shadow, (0, 0))

        # 3. Rising Crimson Ember Particles & Radial Dark Vignette
        self._render_menu_embers(self.screen)
        self._render_bloodborne_vignette(self.screen)

        # 4. Flanking Gothic Star Watermarks on Screen Borders (Image 1 style)
        self._draw_star_emblem(self.screen, 36, SCREEN_HEIGHT // 2)
        self._draw_star_emblem(self.screen, SCREEN_WIDTH - 36, SCREEN_HEIGHT // 2)

        # 5. Top Branding Header (Gothic Serif)
        hx, hy = 110, 68
        t_sh = self.font_gothic_title.render("CHRONICLES OF DUNWICK", True, (138, 26, 36))
        t_fg = self.font_gothic_title.render("CHRONICLES OF DUNWICK", True, (218, 172, 78))
        self.screen.blit(t_sh, (hx + 2, hy + 2))
        self.screen.blit(t_fg, (hx, hy))

        sub = self.font_gothic_sm.render("DEFYING FATE  •  ANNO DOMINI 1924", True, (185, 175, 160))
        self.screen.blit(sub, (hx, hy + 44))

        # Gothic ornamental divider line
        pygame.draw.line(self.screen, (138, 26, 36), (hx, hy + 72), (hx + 380, hy + 72), 2)
        pygame.draw.polygon(self.screen, (218, 172, 78), [(hx + 190, hy + 67), (hx + 195, hy + 72), (hx + 190, hy + 77), (hx + 185, hy + 72)])

        # 6. Left Connecting Spine Line (Image 1 style)
        spine_x = 94
        pygame.draw.line(self.screen, (72, 60, 52), (spine_x, 210), (spine_x, 570), 2)

        # 7. Menu Options
        menu_items = self._get_main_menu_items()
        mx, my = pygame.mouse.get_pos()

        for idx, (label, desc, hk) in enumerate(menu_items):
            iy = 210 + idx * 58
            r = pygame.Rect(110, iy, 340, 50)
            if r.collidepoint(mx, my):
                self.menu_selected_idx = idx

            is_act = (idx == self.menu_selected_idx)
            # Connector from spine to plaque
            pygame.draw.line(self.screen, (72, 60, 52), (spine_x, r.centery), (r.left - 4, r.centery), 1)
            self._draw_gothic_plaque(self.screen, r, is_act, label, self.font_gothic_md if is_act else self.font_gothic_sm, hotkey_tag=hk)

        # 8. Active Item Subtitle Ribbon (Bottom Left, Cinematic)
        sel_idx = max(0, min(len(menu_items) - 1, self.menu_selected_idx))
        active_label, active_desc, _ = menu_items[sel_idx]
        rib_rect = pygame.Rect(110, 580, 480, 56)
        rib_surf = pygame.Surface((rib_rect.width, rib_rect.height), pygame.SRCALPHA)
        pygame.draw.rect(rib_surf, (12, 14, 20, 215), (0, 0, rib_rect.width, rib_rect.height), border_radius=8)
        self.screen.blit(rib_surf, rib_rect.topleft)
        pygame.draw.rect(self.screen, (74, 58, 48), rib_rect, 1, border_radius=8)

        self.screen.blit(self.font_gothic_sm.render(active_desc, True, (218, 172, 78)), (rib_rect.x + 16, rib_rect.y + 9))
        prompt_txt = "[ENTER] or Click to Select  •  [B] Toggle Background  •  [F11] Fullscreen"
        self.screen.blit(self.font_xs.render(prompt_txt, True, (168, 160, 150)), (rib_rect.x + 16, rib_rect.y + 32))

    def _render_settings_row(self, x: int, y: int, width: int, title: str, description: str, options: list[tuple[str, bool]]):
        self.screen.blit(self.font_md.render(title, True, (218, 172, 78)), (x, y + 2))
        self.screen.blit(self.font_xs.render(description, True, (150, 144, 136)), (x, y + 28))

        rx = x + 440
        mx, my = pygame.mouse.get_pos()
        for opt_label, is_selected in options:
            btn_w = max(110, self.font_xs.size(opt_label)[0] + 32)
            btn_rect = pygame.Rect(rx, y + 8, btn_w, 36)
            is_hov = btn_rect.collidepoint(mx, my)

            bg = (48, 16, 22) if is_selected else ((34, 26, 32) if is_hov else (26, 28, 38))
            bdr = (195, 38, 48) if is_selected else ((142, 68, 62) if is_hov else (74, 68, 62))

            pygame.draw.rect(self.screen, bg, btn_rect, border_radius=6)
            pygame.draw.rect(self.screen, bdr, btn_rect, 2 if is_selected else 1, border_radius=6)

            txt_col = (255, 240, 210) if is_selected else ((220, 210, 195) if is_hov else (160, 154, 142))
            t_surf = self.font_xs.render(opt_label, True, txt_col)
            self.screen.blit(t_surf, (btn_rect.centerx - t_surf.get_width() // 2, btn_rect.centery - t_surf.get_height() // 2))

            rx += btn_w + 14

    def _render_settings_modal(self):
        # 1. Dark Background & Vignette
        self.screen.fill((10, 11, 15))
        self._render_menu_embers(self.screen)
        self._render_bloodborne_vignette(self.screen)

        panel = pygame.Rect(80, 40, SCREEN_WIDTH - 160, SCREEN_HEIGHT - 80)
        self._draw_figma_card(panel, bg_rgba=(14, 16, 24, 252), border_col=(142, 28, 38), radius=16, border_w=2, shadow_offset=8)

        # Header in Gothic Serif
        hdr = self.font_gothic_xl.render("SYSTEM CONFIGURATION  •  R.E.P.O. SPECIFICATION MATRIX", True, (218, 172, 78))
        self.screen.blit(hdr, (panel.x + 36, panel.y + 22))

        sub = self.font_gothic_xs.render("Bloodborne Dark Aesthetic  •  Dunwick 1924 Clockwork Engine  •  Defying Fate", True, (160, 150, 138))
        self.screen.blit(sub, (panel.x + 36, panel.y + 56))

        # 5 Tabs: GRAPHICS, AUDIO, GAMEPLAY, CONTROLS, AI BROKER
        tabs = ["GRAPHICS", "AUDIO", "GAMEPLAY", "CONTROLS", "AI BROKER"]
        mx, my = pygame.mouse.get_pos()

        for t_i, t_name in enumerate(tabs):
            tx = panel.x + 36 + t_i * 220
            ty = panel.y + 86
            t_rect = pygame.Rect(tx, ty, 205, 42)
            is_act = (t_i == self.settings_tab_idx)
            if t_rect.collidepoint(mx, my) and pygame.mouse.get_pressed()[0]:
                self.settings_tab_idx = t_i

            self._draw_gothic_plaque(self.screen, t_rect, is_act, f"[{t_i + 1}] {t_name}", self.font_gothic_sm)

        # Content Box
        c_box = pygame.Rect(panel.x + 36, panel.y + 140, panel.width - 72, panel.height - 216)
        self._draw_figma_card(c_box, bg_rgba=(18, 20, 30, 248), border_col=(68, 56, 48), radius=12, border_w=1, shadow_offset=4)

        cx0 = c_box.x + 36
        cy0 = c_box.y + 20
        cw = c_box.width - 72

        # Draw content by tab
        tab = self.settings_tab_idx
        if tab == 0:
            # GRAPHICS TAB
            self._render_settings_row(cx0, cy0, cw, "DISPLAY MODE", "Select fullscreen display or windowed presentation.",
                                      [("FULLSCREEN (SCALED)", self.settings.get("display_mode") == "FULLSCREEN"),
                                       ("WINDOWED (1360x860)", self.settings.get("display_mode") == "WINDOWED")])
            cy0 += 74
            self._render_settings_row(cx0, cy0, cw, "MENU BACKGROUND THEME", "Tudor Borough market square pixel-art or Blood Moon Eclipse.",
                                      [("DUNWICK MARKET", self.settings.get("menu_background", "DUNWICK_MARKET") == "DUNWICK_MARKET"),
                                       ("BLOOD MOON ECLIPSE", self.settings.get("menu_background") == "BLOOD_MOON_ECLIPSE")])
            cy0 += 74
            self._render_settings_row(cx0, cy0, cw, "ATMOSPHERIC EMBERS & SMOKE", "Simulate drifting coal embers and steam fog.",
                                      [("ENABLED", self.settings.get("atmospheric_particles", True)),
                                       ("DISABLED", not self.settings.get("atmospheric_particles", True))])
            cy0 += 74
            self._render_settings_row(cx0, cy0, cw, "DARKNESS VIGNETTE", "Radial gothic darkness around overworld view.",
                                      [("BLOODBORNE DARK", self.settings.get("darkness_vignette", "BLOODBORNE_DARK") == "BLOODBORNE_DARK"),
                                       ("STANDARD (SOFT)", self.settings.get("darkness_vignette") == "STANDARD")])
            cy0 += 74
            self._render_settings_row(cx0, cy0, cw, "TARGET FRAMERATE", "Framerate governor (60 FPS standard).",
                                      [("60 FPS", self.settings.get("target_fps", 60) == 60),
                                       ("120 FPS", self.settings.get("target_fps") == 120),
                                       ("UNCAPPED", self.settings.get("target_fps") == 0)])

        elif tab == 1:
            # AUDIO TAB
            m_vol = self.settings.get("master_volume", 80)
            self._render_settings_row(cx0, cy0, cw, "MASTER VOLUME", "Global acoustic gain level.",
                                      [("0%", m_vol == 0), ("25%", m_vol == 25), ("50%", m_vol == 50), ("75%", m_vol == 75), ("100%", m_vol == 100)])
            cy0 += 88
            s_vol = self.settings.get("sfx_volume", 75)
            self._render_settings_row(cx0, cy0, cw, "SFX & MACHINERY AMBIENCE", "Steam lorry engines, foundry boiler hum & footsteps.",
                                      [("0%", s_vol == 0), ("50%", s_vol == 50), ("75%", s_vol == 75), ("100%", s_vol == 100)])
            cy0 += 88
            self._render_settings_row(cx0, cy0, cw, "CLOCKTOWER BELL CHIMES", "Acoustic bells sounding hour marks and 7th bell doom.",
                                      [("ENABLED", self.settings.get("ambient_bells", True)),
                                       ("MUTED", not self.settings.get("ambient_bells", True))])
            cy0 += 88
            self._render_settings_row(cx0, cy0, cw, "TYPEWRITER DIALOGUE AUDIO", "Audible keystroke clicks when characters converse.",
                                      [("ENABLED", self.settings.get("typewriter_sound", True)),
                                       ("MUTED", not self.settings.get("typewriter_sound", True))])

        elif tab == 2:
            # GAMEPLAY TAB
            tw_spd = self.settings.get("typewriter_speed", "NORMAL")
            self._render_settings_row(cx0, cy0, cw, "DIALOGUE TYPEWRITER SPEED", "Speed of revelation for character speech.",
                                      [("NORMAL (115 CPS)", tw_spd == "NORMAL"),
                                       ("FAST (240 CPS)", tw_spd == "FAST"),
                                       ("INSTANT", tw_spd == "INSTANT")])
            cy0 += 88
            cam_sm = self.settings.get("camera_smoothing", "SMOOTH")
            self._render_settings_row(cx0, cy0, cw, "CAMERA TRACKING INERTIA", "2.5D Octopath Traveler camera follow behavior.",
                                      [("SMOOTH INERTIA", cam_sm == "SMOOTH"),
                                       ("INSTANT SNAP", cam_sm == "SNAP")])
            cy0 += 88
            self._render_settings_row(cx0, cy0, cw, "HIGH STREET TRAFFIC HAZARD", "Stepping in front of moving steam-carriages.",
                                      [("REALISTIC (LETHAL DEATH)", True)])
            cy0 += 88
            self._render_settings_row(cx0, cy0, cw, "CROSS-LOOP MEMORY SYSTEM", "Retain past deaths and observed clues across timelines.",
                                      [("FULL PERSISTENCE", True)])

        elif tab == 3:
            # CONTROLS TAB (R.E.P.O. keybinding matrix)
            self.screen.blit(self.font_md.render("DUNWICK 1924 KEYMAP & ACTION SCHEMA", True, COLORS["gold"]), (cx0, cy0))
            cy0 += 32

            key_binds_left = [
                ("[ W A S D ] / [ Arrows ]", "2.5D Isometric Walk Cycle"),
                ("[ E ]", "Interact with NPCs, Doors & Machinery"),
                ("[ SPACE ] / [ RETURN ]", "Advance Dialogue / Confirm Selection"),
                ("[ 1 ] - [ 4 ]", "Select Dialogue Response Option"),
                ("[ ESC ]", "Main Menu / Pause / Close Active Modal"),
            ]
            key_binds_right = [
                ("[ R ]", "Trigger Sole-Knower Premonition Scan"),
                ("[ T ]", "Open Custom AI Dialogue Speech Terminal"),
                ("[ G ]", "Advance to Next Day (when threat foiled)"),
                ("[ N ]", "Open Foresight Journal & Butterfly Web"),
                ("[ F11 ]", "Toggle Fullscreen Presentation"),
            ]

            col_w = cw // 2 - 16
            for idx, (k_lbl, k_act) in enumerate(key_binds_left):
                ky = cy0 + idx * 56
                k_box = pygame.Rect(cx0, ky, col_w, 46)
                pygame.draw.rect(self.screen, (28, 30, 42), k_box, border_radius=8)
                pygame.draw.rect(self.screen, (74, 68, 62), k_box, 1, border_radius=8)
                self.screen.blit(self.font_sm.render(k_lbl, True, COLORS["gold"]), (k_box.x + 14, ky + 12))
                self.screen.blit(self.font_xs.render(k_act, True, (220, 215, 205)), (k_box.x + 210, ky + 14))

            for idx, (k_lbl, k_act) in enumerate(key_binds_right):
                ky = cy0 + idx * 56
                k_box = pygame.Rect(cx0 + col_w + 32, ky, col_w, 46)
                pygame.draw.rect(self.screen, (28, 30, 42), k_box, border_radius=8)
                pygame.draw.rect(self.screen, (74, 68, 62), k_box, 1, border_radius=8)
                self.screen.blit(self.font_sm.render(k_lbl, True, COLORS["cyan"]), (k_box.x + 14, ky + 12))
                self.screen.blit(self.font_xs.render(k_act, True, (220, 215, 205)), (k_box.x + 175, ky + 14))

        elif tab == 4:
            # AI BROKER TAB
            prov = self.settings.get("ai_provider", "gemini")
            self._render_settings_row(cx0, cy0, cw, "ACTIVE LLM PROVIDER", "Cloud neural intelligence for dynamic procedural NPCs.",
                                      [("GEMINI", prov == "gemini"),
                                       ("OPENAI", prov == "openai"),
                                       ("LOCAL HYBRID", prov == "hybrid")])
            cy0 += 88
            key_val = self.api_key_input
            masked = (key_val[:6] + "••••••••••••" + key_val[-4:]) if len(key_val) > 10 else ("NOT CONFIGURED" if not key_val else "••••••••")
            self._render_settings_row(cx0, cy0, cw, "CLOUD API KEY CREDENTIAL", "Key stored securely in llm_config.json.",
                                      [(f"KEY: {masked}", False), ("[TAB / CLICK EDIT]", True)])
            cy0 += 88

            st_box = pygame.Rect(cx0, cy0, cw, 100)
            pygame.draw.rect(self.screen, (28, 30, 42), st_box, border_radius=8)
            pygame.draw.rect(self.screen, (74, 68, 62), st_box, 1, border_radius=8)
            self.screen.blit(self.font_sm.render("VECTOR MEMORY & LOCAL YARN FALLBACK ENGINE:", True, COLORS["gold"]), (cx0 + 16, cy0 + 14))
            info_txt = (
                "The game includes full local deterministic Yarn Spinner dialogue trees and vector memory caches. "
                "Even without a live internet connection or API key, all Butterfly effects, character routines, "
                "investigations, and premonitions function completely offline."
            )
            self._render_wrapped_text(info_txt, self.font_xs, (200, 195, 185), cx0 + 16, cy0 + 40, max_width=cw - 32, line_spacing=18)

        # Bottom Buttons
        self._draw_figma_button(pygame.Rect(panel.x + 36, panel.bottom - 60, 240, 44),
                                "[ESC] BACK TO MENU", self.font_sm, bg_col=(44, 28, 34), border_col=COLORS["red"])
        self._draw_figma_button(pygame.Rect(panel.centerx - 120, panel.bottom - 60, 240, 44),
                                "[R] RESTORE DEFAULTS", self.font_sm, bg_col=(34, 36, 48), border_col=(102, 92, 78))
        self._draw_figma_button(pygame.Rect(panel.right - 276, panel.bottom - 60, 240, 44),
                                "[ENTER] APPLY & CLOSE", self.font_sm, bg_col=(32, 98, 62), border_col=COLORS["green"])

    def _handle_settings_tab_clicks(self, mx: int, my: int, panel: pygame.Rect):
        tab = self.settings_tab_idx
        cx0 = panel.x + 36
        cy0 = panel.y + 144 + 24
        cw = panel.width - 72

        if tab == 0:
            # GRAPHICS
            if pygame.Rect(cx0 + 440, cy0 + 8, 200, 36).collidepoint(mx, my):
                self.settings["display_mode"] = "FULLSCREEN"
                if not (self.screen.get_flags() & pygame.FULLSCREEN):
                    pygame.display.toggle_fullscreen()
                self._save_settings()
            elif pygame.Rect(cx0 + 440 + 214, cy0 + 8, 200, 36).collidepoint(mx, my):
                self.settings["display_mode"] = "WINDOWED"
                if self.screen.get_flags() & pygame.FULLSCREEN:
                    pygame.display.toggle_fullscreen()
                self._save_settings()

            r_bg_y = cy0 + 74
            if pygame.Rect(cx0 + 440, r_bg_y + 8, 180, 36).collidepoint(mx, my):
                self.settings["menu_background"] = "DUNWICK_MARKET"
                self._save_settings()
            elif pygame.Rect(cx0 + 440 + 194, r_bg_y + 8, 200, 36).collidepoint(mx, my):
                self.settings["menu_background"] = "BLOOD_MOON_ECLIPSE"
                self._save_settings()

            r1_y = cy0 + 148
            if pygame.Rect(cx0 + 440, r1_y + 8, 140, 36).collidepoint(mx, my):
                self.settings["atmospheric_particles"] = True
                self._save_settings()
            elif pygame.Rect(cx0 + 440 + 154, r1_y + 8, 140, 36).collidepoint(mx, my):
                self.settings["atmospheric_particles"] = False
                self._save_settings()

            r2_y = cy0 + 222
            if pygame.Rect(cx0 + 440, r2_y + 8, 220, 36).collidepoint(mx, my):
                self.settings["darkness_vignette"] = "BLOODBORNE_DARK"
                self._cached_vignette = None
                self._save_settings()
            elif pygame.Rect(cx0 + 440 + 234, r2_y + 8, 180, 36).collidepoint(mx, my):
                self.settings["darkness_vignette"] = "STANDARD"
                self._cached_vignette = None
                self._save_settings()

            r3_y = cy0 + 296
            if pygame.Rect(cx0 + 440, r3_y + 8, 110, 36).collidepoint(mx, my):
                self.settings["target_fps"] = 60
                self._save_settings()
            elif pygame.Rect(cx0 + 440 + 124, r3_y + 8, 110, 36).collidepoint(mx, my):
                self.settings["target_fps"] = 120
                self._save_settings()
            elif pygame.Rect(cx0 + 440 + 248, r3_y + 8, 140, 36).collidepoint(mx, my):
                self.settings["target_fps"] = 0
                self._save_settings()

        elif tab == 1:
            # AUDIO
            vol_step = 80
            for i, v in enumerate([0, 25, 50, 75, 100]):
                if pygame.Rect(cx0 + 440 + i * vol_step, cy0 + 8, 68, 36).collidepoint(mx, my):
                    self.settings["master_volume"] = v
                    self._save_settings()
                    break

            r1_y = cy0 + 88
            for i, v in enumerate([0, 50, 75, 100]):
                if pygame.Rect(cx0 + 440 + i * 88, r1_y + 8, 74, 36).collidepoint(mx, my):
                    self.settings["sfx_volume"] = v
                    self._save_settings()
                    break

            r2_y = cy0 + 176
            if pygame.Rect(cx0 + 440, r2_y + 8, 140, 36).collidepoint(mx, my):
                self.settings["ambient_bells"] = True
                self._save_settings()
            elif pygame.Rect(cx0 + 440 + 154, r2_y + 8, 140, 36).collidepoint(mx, my):
                self.settings["ambient_bells"] = False
                self._save_settings()

            r3_y = cy0 + 264
            if pygame.Rect(cx0 + 440, r3_y + 8, 140, 36).collidepoint(mx, my):
                self.settings["typewriter_sound"] = True
                self._save_settings()
            elif pygame.Rect(cx0 + 440 + 154, r3_y + 8, 140, 36).collidepoint(mx, my):
                self.settings["typewriter_sound"] = False
                self._save_settings()

        elif tab == 2:
            # GAMEPLAY
            spds = [("NORMAL", 180), ("FAST", 160), ("INSTANT", 130)]
            sx = cx0 + 440
            for spd_key, btn_w in spds:
                if pygame.Rect(sx, cy0 + 8, btn_w, 36).collidepoint(mx, my):
                    self.settings["typewriter_speed"] = spd_key
                    self._save_settings()
                    break
                sx += btn_w + 14

            r1_y = cy0 + 88
            if pygame.Rect(cx0 + 440, r1_y + 8, 180, 36).collidepoint(mx, my):
                self.settings["camera_smoothing"] = "SMOOTH"
                self._save_settings()
            elif pygame.Rect(cx0 + 440 + 194, r1_y + 8, 160, 36).collidepoint(mx, my):
                self.settings["camera_smoothing"] = "SNAP"
                self._save_settings()

        elif tab == 4:
            # AI BROKER
            provs = [("gemini", 120), ("openai", 120), ("hybrid", 160)]
            px = cx0 + 440
            for p_key, btn_w in provs:
                if pygame.Rect(px, cy0 + 8, btn_w, 36).collidepoint(mx, my):
                    self.settings["ai_provider"] = p_key
                    self.llm_broker.config["provider"] = p_key
                    self.api_provider_choice = p_key
                    self._save_settings()
                    break
                px += btn_w + 14

            r1_y = cy0 + 88
            if pygame.Rect(cx0 + 440 + 260, r1_y + 8, 180, 36).collidepoint(mx, my):
                self.active_modal = "API_CONFIG"


    def _render_family_select_modal(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((8, 10, 18, 225))
        self.screen.blit(overlay, (0, 0))

        panel = pygame.Rect(72, 34, 1216, 788)
        self._draw_figma_card(
            panel, bg_rgba=(14, 16, 24, 252), border_col=COLORS["gold"], radius=20, border_w=2, shadow_offset=10
        )

        t_surf = self.font_gothic_xl.render(
            "CHRONICLES OF DUNWICK (1924)  •  CHOOSE YOUR FATE SCENARIO & PROTAGONIST", True, COLORS["gold"]
        )
        self.screen.blit(t_surf, (panel.centerx - t_surf.get_width() // 2, 50))

        sub = self.font_xs.render(
            "STEP 1: Select 1 of the 3 Fate Scenarios ([F1]-[F3] or Click)   •   STEP 2: Choose 1 of the 4 Family Members ([1]-[4] — ONLY THEY WILL KNOW!)",
            True,
            COLORS["cyan"],
        )
        self.screen.blit(sub, (panel.centerx - sub.get_width() // 2, 88))

        mx, my = pygame.mouse.get_pos()

        # ROW 1: The 3 Playable Fate Scenarios
        scen_keys = ["WORLD_END", "SELF_DEATH", "LOVED_ONE"]
        for idx, skey in enumerate(scen_keys):
            sdata = SCENARIO_MODES[skey]
            sx = 110 + idx * 385
            sy = 122
            s_rect = pygame.Rect(sx, sy, 365, 134)
            is_sel = self.world.scenario_mode == skey
            is_hov = s_rect.collidepoint(mx, my)

            self._draw_figma_card(
                s_rect,
                bg_rgba=(44, 38, 62, 250) if (is_sel or is_hov) else (26, 28, 42, 245),
                border_col=sdata["badge_color"] if (is_sel or is_hov) else (82, 78, 92),
                radius=14,
                border_w=3 if is_sel else 1,
                shadow_offset=4,
            )
            hdr = self.font_sm.render(f"[F{idx + 1}] {sdata['short_title']}", True, sdata["badge_color"])
            self.screen.blit(hdr, (sx + 14, sy + 12))
            sub_t = self.font_md.render(sdata["subtitle"], True, COLORS["white"])
            self.screen.blit(sub_t, (sx + 14, sy + 34))

            # Wrap summary
            self._render_wrapped_text(
                sdata["summary"], self.font_xs, COLORS["text_dim"], sx + 14, sy + 64, max_width=s_rect.width - 28, line_spacing=18, max_lines=3
            )

        # ROW 2: The 4 Playable Ashford-Mercer Family Members
        family_ids = ["arthur", "elena", "maya", "leo"]
        t_phase = pygame.time.get_ticks() / 1000.0

        for idx, fid in enumerate(family_ids):
            char = self.world.characters[fid]
            cx = 110 + idx * 290
            cy = 278
            c_rect = pygame.Rect(cx, cy, 270, 398)
            is_sel = self.world.player_char_id == fid
            is_hov = c_rect.collidepoint(mx, my)

            self._draw_figma_card(
                c_rect,
                bg_rgba=(38, 44, 68, 250) if (is_sel or is_hov) else (24, 28, 42, 245),
                border_col=COLORS["gold"] if (is_sel or is_hov) else (78, 82, 104),
                radius=16,
                border_w=3 if is_sel else 2,
                shadow_offset=6,
            )

            badge_rect = pygame.Rect(cx + 45, cy + 12, 180, 24)
            pygame.draw.rect(self.screen, (20, 24, 36), badge_rect, border_radius=12)
            k_lbl = self.font_xs.render(
                f"SOLE KNOWER [{idx + 1}]" if is_sel else f"SELECT [{idx + 1}]",
                True,
                COLORS["gold"] if is_sel else COLORS["cyan"],
            )
            self.screen.blit(
                k_lbl, (badge_rect.centerx - k_lbl.get_width() // 2, badge_rect.centery - k_lbl.get_height() // 2)
            )

            port_rect = pygame.Rect(cx + 55, cy + 44, 160, 160)
            draw_character_portrait(self.screen, port_rect, char.spec, anim_phase=(t_phase if is_sel else 0.0))

            n_lbl = self.font_md.render(char.name, True, COLORS["white"])
            self.screen.blit(n_lbl, (c_rect.centerx - n_lbl.get_width() // 2, cy + 214))

            r_lbl = self.font_xs.render(char.role, True, COLORS["cyan"])
            self.screen.blit(r_lbl, (c_rect.centerx - r_lbl.get_width() // 2, cy + 238))

            self._render_wrapped_text(
                char.perk, self.font_xs, COLORS["text_dim"], cx + 16, cy + 268, max_width=c_rect.width - 32, line_spacing=19, max_lines=3
            )

            # Show who they protect if Scenario 3 is selected!
            from config import PROTAGONIST_LOVED_ONE
            loved_txt = (
                f"Loved One: {PROTAGONIST_LOVED_ONE[fid]['relation'].split(',')[-1].strip()}"
                if self.world.scenario_mode == "LOVED_ONE"
                else "Only this character knows the truth!"
            )
            self._render_wrapped_text(
                loved_txt, self.font_xs, COLORS["green"], cx + 16, cy + 356, max_width=c_rect.width - 32, max_lines=2
            )

        cur_scen = SCENARIO_MODES[self.world.scenario_mode]["subtitle"]
        self._draw_figma_button(
            pygame.Rect(110, 698, 160, 54),
            "[ESC] MENU",
            self.font_sm,
            bg_col=(44, 28, 34),
            border_col=COLORS["red"],
            radius=12,
        )
        self._draw_figma_button(
            pygame.Rect(290, 698, 810, 54),
            f"BEGIN 7-DAY CAMPAIGN: '{cur_scen.upper()}' AS {self.world.get_player().name.upper()} [SPACE]",
            self.font_md,
            bg_col=(32, 112, 72),
            hover_col=(44, 142, 92),
            border_col=COLORS["green"],
            radius=14,
        )

    def _render_lore_prologue_modal(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((8, 10, 18, 235))
        self.screen.blit(overlay, (0, 0))

        panel = pygame.Rect(88, 36, 1184, 768)
        self._draw_figma_card(
            panel, bg_rgba=(18, 22, 34, 250), border_col=COLORS["gold"], radius=22, border_w=2, shadow_offset=10
        )

        p = self.world.get_player()
        lore_data = FAMILY_LORE_PROLOGUES.get(p.id, FAMILY_LORE_PROLOGUES["arthur"])
        scen_data = SCENARIO_MODES[self.world.scenario_mode]

        hdr = self.font_gothic_xl.render(
            f"{scen_data['short_title']}  •  {scen_data['subtitle'].upper()}", True, scen_data["badge_color"]
        )
        self.screen.blit(hdr, (panel.centerx - hdr.get_width() // 2, 54))

        town_box = pygame.Rect(125, 96, 1110, 260)
        self._draw_figma_card(
            town_box, bg_rgba=(24, 28, 44, 245), border_col=(138, 112, 64), radius=14, border_w=1, shadow_offset=4
        )

        ty = 110
        ty = self._render_wrapped_text(TOWN_LORE_PROLOGUE[0], self.font_md, COLORS["gold"], 148, ty, max_width=1060, line_spacing=24)
        ty += 4
        town_body = [p_text for p_text in TOWN_LORE_PROLOGUE[1:] if p_text]
        for para in town_body:
            ty = self._render_wrapped_text(para, self.font_sm, COLORS["white"], 148, ty, max_width=1060, line_spacing=20)
            ty += 6

        char_box = pygame.Rect(125, 372, 1110, 310)
        self._draw_figma_card(
            char_box, bg_rgba=(28, 34, 52, 245), border_col=COLORS["gold"], radius=14, border_w=2, shadow_offset=4
        )

        t_phase = pygame.time.get_ticks() / 1000.0
        port_rect = pygame.Rect(148, 396, 160, 160)
        draw_character_portrait(self.screen, port_rect, p.spec, anim_phase=t_phase)

        rx = 328
        rw = char_box.right - 24 - rx  # 879 px available width inside card
        cy = 388

        cy = self._render_wrapped_text(lore_data["headline"], self.font_lg, COLORS["gold"], rx, cy, max_width=rw, line_spacing=24)
        cy += 6
        cy = self._render_wrapped_text(lore_data["story"], self.font_sm, COLORS["white"], rx, cy, max_width=rw, line_spacing=20, max_lines=4)
        cy += 8

        target_lbl = self.world.get_protected_target_label()
        fate_txt = f"7-DAY FATE TARGET: Protect {target_lbl} from Monday through Sunday ({scen_data['victory_condition']})"
        cy = self._render_wrapped_text(fate_txt, self.font_sm, COLORS["cyan"], rx, cy, max_width=rw, line_spacing=20)
        cy += 6

        perk_txt = f"PROTAGONIST PERK: {lore_data['specialty']}"
        cy = self._render_wrapped_text(perk_txt, self.font_sm, COLORS["green"], rx, cy, max_width=rw, line_spacing=20)

        tip_lbl = (
            "SOLE-KNOWER RULE: Nobody else knows! Observe human habits, foil today's hazard, "
            "then press [G] for the next day's Butterfly twist!"
        )
        self._render_wrapped_text(tip_lbl, self.font_xs, COLORS["gold"], 148, char_box.bottom - 28, max_width=1060)

        self._draw_figma_button(
            pygame.Rect(125, 700, 270, 56),
            "[F] CHANGE SCENARIO / HERO",
            self.font_sm,
            bg_col=(34, 38, 58),
            border_col=COLORS["cyan"],
            radius=12,
        )
        self._draw_figma_button(
            pygame.Rect(420, 700, 815, 56),
            "STEP INTO MONDAY MORNING (1924 DUNWICK) [SPACE]",
            self.font_md,
            bg_col=(32, 118, 74),
            hover_col=(44, 148, 92),
            border_col=COLORS["green"],
            radius=14,
        )

    def _render_notebook_modal(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((8, 10, 18, 198))
        self.screen.blit(overlay, (0, 0))

        rect = pygame.Rect(140, 75, 1080, 710)
        self._draw_figma_card(
            rect, bg_rgba=(18, 22, 34, 250), border_col=COLORS["gold"], radius=20, border_w=2, shadow_offset=10
        )

        x0, y0 = rect.x + 32, rect.y + 24
        scen_title = SCENARIO_MODES[self.world.scenario_mode]["short_title"]
        self.screen.blit(
            self.font_gothic_xl.render(f"FORESIGHT JOURNAL & 7-DAY BUTTERFLY WEB  •  {scen_title}", True, COLORS["gold"]),
            (x0, y0),
        )
        y0 += 38

        obj_info = self.world.get_current_objective()
        self.screen.blit(self.font_md.render(obj_info["chapter_title"], True, COLORS["cyan"]), (x0, y0))
        y0 += 24
        self.screen.blit(self.font_sm.render(obj_info["instruction"], True, COLORS["green"]), (x0, y0))
        y0 += 34

        # 7-Day Week Butterfly Chain Visualization!
        self.screen.blit(
            self.font_md.render(
                f"The 7-Day Butterfly Chain (Protecting: {self.world.get_protected_target_label()}):",
                True,
                COLORS["gold"],
            ),
            (x0, y0),
        )
        y0 += 26

        hist_by_day = {h["day"]: h for h in self.world.butterfly_history}
        for d_idx in range(1, TOTAL_DAYS_IN_WEEK + 1):
            d_name = WEEK_DAYS[d_idx - 1]
            if d_idx in hist_by_day:
                h = hist_by_day[d_idx]
                txt = f"[SURVIVED] Day {d_idx} ({d_name}): {h['threat']}  -->  Foiled via [{h['method']}]"
                col = COLORS["green"]
            elif d_idx == self.world.current_day:
                txt = f"[ACTIVE NOW] Day {d_idx} ({d_name}): {self.world.scenario['title']}  —  {self.world.scenario['motive']}"
                col = COLORS["gold"]
            else:
                txt = f"[LOCKED FUTURE] Day {d_idx} ({d_name}): Unwritten Butterfly Effect (Will mutate from Day {d_idx - 1}'s intervention!)"
                col = COLORS["text_muted"]
            y0 = self._render_wrapped_text(txt, self.font_xs, col, x0 + 8, y0, max_width=rect.width - 64, line_spacing=18, max_lines=2)
            y0 += 4

        y0 += 10
        if self.world.death_journal:
            self.screen.blit(
                self.font_md.render("Sole-Knower Temporal Inscriptions (Past Deaths Remembered):", True, COLORS["red"]),
                (x0, y0),
            )
            y0 += 24
            for dj in self.world.death_journal[-3:]:
                txt = f"• Loop #{dj['loop']}: Struck down on {dj['day_name']} via [{dj['hazard']}] ({dj['hazard_type']})."
                y0 = self._render_wrapped_text(txt, self.font_xs, (245, 175, 175), x0 + 8, y0, max_width=rect.width - 64, line_spacing=18, max_lines=2)
                y0 += 2
            y0 += 6

        self.screen.blit(
            self.font_md.render("Observed Human Behavioral Tells & Cross-Loop Deductions:", True, COLORS["gold"]),
            (x0, y0),
        )
        y0 += 24
        for clue in self.world.notebook_clues[-5:]:
            y0 = self._render_wrapped_text(f"•  {clue}", self.font_xs, COLORS["white"], x0 + 8, y0, max_width=rect.width - 64, line_spacing=18, max_lines=2)
            y0 += 2

        self.screen.blit(
            self.font_xs.render(
                "Press [N] or [ESC] to Close Journal   |   Press [G] When Today's Threat is Foiled to Advance to Next Day",
                True,
                COLORS["text_dim"],
            ),
            (x0, rect.bottom - 30),
        )

    def _render_api_config_modal(self):
        rect = pygame.Rect(310, 240, 740, 250)
        self._draw_figma_card(rect, bg_rgba=(18, 22, 34, 248), border_col=COLORS["gold"], radius=18)
        x0, y0 = rect.x + 28, rect.y + 28
        self.screen.blit(
            self.font_lg.render("CLOUD LLM API KEY ([TAB] Gemini / OpenAI)", True, COLORS["gold"]), (x0, y0)
        )
        y0 += 48
        self.screen.blit(
            self.font_sm.render(
                f"Provider: {self.api_provider_choice.upper()}  |  Key: {self.api_key_input[:12]}...",
                True,
                COLORS["white"],
            ),
            (x0, y0),
        )
        y0 += 48
        self.screen.blit(
            self.font_xs.render("Press [ENTER] Save & Close  |  [ESC] Cancel", True, COLORS["green"]), (x0, y0)
        )

    def _render_outcome_modal(self):
        is_win = self.world.outcome_state == "VICTORY"
        col = COLORS["green"] if is_win else COLORS["red"]
        rect = pygame.Rect(190, 200, 980, 370)
        self._draw_figma_card(
            rect, bg_rgba=(18, 22, 34, 250), border_col=col, radius=20, border_w=3, shadow_offset=10
        )

        x0, y0 = rect.x + 34, rect.y + 30
        hdr = (
            "FATE DEFIED — ALL 7 DAYS SURVIVED!"
            if is_win
            else f"FATE CLAIMED ITS TOLL ON {self.world.get_day_name().upper()}  -->  REWINDING TO LOOP #{self.world.loop_id + 1}"
        )
        self.screen.blit(self.font_gothic_xl.render(hdr, True, col), (x0, y0))
        y0 += 54

        y0 = self._render_wrapped_text(
            self.world.outcome_reason, self.font_md, COLORS["white"], x0, y0, max_width=rect.width - 68, line_spacing=26
        )
        y0 += 18

        btn_txt = (
            "Press [SPACE] to Choose a New Fate Scenario or Family Protagonist!"
            if is_win
            else f"Press [SPACE] to Awaken on Monday in Loop #{self.world.loop_id + 1} (New Butterfly Permutations & Echoes)!"
        )
        self._render_wrapped_text(
            btn_txt, self.font_lg, COLORS["cyan"], x0, y0, max_width=rect.width - 68, line_spacing=28
        )


if __name__ == "__main__":
    headless = "--test-headless" in sys.argv
    app = MaplewoodRPGApp(headless_test=headless)
    app.run(max_frames=90 if headless else None)
