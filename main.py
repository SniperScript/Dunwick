"""
MAPLEWOOD LOOP // 2.5D Family Time-Loop Mystery RPG
Features:
- 2.5D Defined Pixel-Art & Timber-Town Environment (ArtEngine25D: Cobblestone streets,
  timber-frame houses with shingled roofs & flower boxes, 3D-extruded tables/chairs/market stalls,
  animated fountain, plasma generator, and animated quest items).
- Unified YSort 2.5D Depth Pipeline (FIFE / Unknown Horizons / Tiny Life style): Characters,
  furniture, trees, barrels, street lamps, and vehicles depth-sort naturally in 2.5D space.
- Continuous Circle-vs-Rounded-AABB Collision (TileGridEngine): Zero corner sticking around tables or doors.
- Sleek, Simplified Figma / Canva-Inspired Floating UI Cards, Pills & Interactive Hover States.
"""

import math
import os
import sys
import pygame

from art_engine_25d import ArtEngine25D
from config import (
    BUILDINGS,
    COLORS,
    FAMILY_LORE_PROLOGUES,
    FPS,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    TITLE,
    TOWN_LORE_PROLOGUE,
    WORLD_HEIGHT,
    WORLD_WIDTH,
)
from cloud_llm_broker import CloudLLMBroker
from simulation_world import SimulationWorld, SimCharacter
from skeletal_engine import draw_character_portrait


class MaplewoodRPGApp:
    def __init__(self, headless_test: bool = False):
        self.headless_test = headless_test
        if headless_test:
            os.environ["SDL_VIDEODRIVER"] = "dummy"
            os.environ["SDL_AUDIODRIVER"] = "dummy"

        pygame.init()
        pygame.font.init()

        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(TITLE)
        self.clock = pygame.time.Clock()

        # Modern Figma-style UI Typography Hierarchy (ASCII/English only — zero missing glyph boxes!)
        self.font_xs = pygame.font.SysFont("DejaVu Sans, Arial, sans-serif", 12, bold=True)
        self.font_sm = pygame.font.SysFont("DejaVu Sans, Arial, sans-serif", 14, bold=True)
        self.font_md = pygame.font.SysFont("DejaVu Sans, Arial, sans-serif", 17, bold=True)
        self.font_lg = pygame.font.SysFont("DejaVu Sans, Arial, sans-serif", 21, bold=True)
        self.font_xl = pygame.font.SysFont("DejaVu Sans, Arial, sans-serif", 27, bold=True)

        self.llm_broker = CloudLLMBroker()
        self.world = SimulationWorld(self.llm_broker)

        assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
        self.art_engine = ArtEngine25D(assets_dir=assets_dir)

        p = self.world.get_player()
        self.cam_x = p.x - SCREEN_WIDTH * 0.5
        self.cam_y = p.y - SCREEN_HEIGHT * 0.5

        # Active Modal: None, "FAMILY_SELECT", "LORE_PROLOGUE", "DIALOGUE", "NOTEBOOK", "API_CONFIG"
        self.active_modal = None if headless_test else "FAMILY_SELECT"
        self.has_seen_prologue = False
        self.talking_npc: SimCharacter | None = None
        self.npc_greeting = ""
        self.npc_options = []
        self.typewriter_chars = 0.0
        self.custom_input = ""
        self.typing_custom = False

        self.toast_msg = "5:00 PM in Maplewood Heights. Walk with [WASD/Arrows], [E] Interact, [1-4] Switch Family!"
        self.toast_timer = 6.5

        self.trees = [
            (860, 220), (860, 460), (860, 660),
            (1710, 220), (1710, 460), (1710, 660),
            (860, 1120), (860, 1380), (860, 1600),
            (1710, 1120), (1710, 1380), (1710, 1600),
            (1920, 1560), (2380, 1560), (2420, 1180),
        ]

        self.api_provider_choice = self.llm_broker.config.get("provider", "gemini")
        self.api_key_input = (
            self.llm_broker.config.get("gemini_api_key", "")
            if self.api_provider_choice == "gemini"
            else self.llm_broker.config.get("openai_api_key", "")
        )

    # =========================================================================
    # FIGMA / CANVA UI DESIGN PRIMITIVES (Soft Shadows, Glass Cards, Hover Pills)
    # =========================================================================
    def _draw_figma_card(
        self,
        rect: pygame.Rect,
        bg_rgba: tuple[int, int, int, int] = (20, 25, 38, 238),
        border_col: tuple[int, int, int] = (72, 88, 120),
        radius: int = 16,
        border_w: int = 2,
        shadow_offset: int = 6,
    ):
        if shadow_offset > 0:
            sh_surf = pygame.Surface((rect.width + 8, rect.height + 8), pygame.SRCALPHA)
            pygame.draw.rect(
                sh_surf, (6, 8, 14, 115), (0, 0, rect.width + 8, rect.height + 8), border_radius=radius + 2
            )
            self.screen.blit(sh_surf, (rect.x - 4 + shadow_offset // 2, rect.y + shadow_offset))

        card_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        pygame.draw.rect(card_surf, bg_rgba, (0, 0, rect.width, rect.height), border_radius=radius)
        self.screen.blit(card_surf, rect.topleft)

        if border_w > 0:
            pygame.draw.rect(self.screen, border_col, rect, border_w, border_radius=radius)

    def _draw_figma_button(
        self,
        rect: pygame.Rect,
        label: str,
        font: pygame.font.Font,
        bg_col: tuple[int, int, int] = (34, 44, 66),
        hover_col: tuple[int, int, int] = (52, 68, 98),
        border_col: tuple[int, int, int] = (95, 195, 245),
        text_col: tuple[int, int, int] = (248, 248, 245),
        radius: int = 10,
        align_left: bool = False,
    ):
        mx, my = pygame.mouse.get_pos()
        is_hover = rect.collidepoint(mx, my)
        fill = hover_col if is_hover else bg_col
        pygame.draw.rect(self.screen, (10, 14, 22), rect.move(0, 3), border_radius=radius)
        pygame.draw.rect(self.screen, fill, rect, border_radius=radius)
        pygame.draw.rect(
            self.screen,
            (255, 220, 95) if is_hover else border_col,
            rect,
            2 if is_hover else 1,
            border_radius=radius,
        )
        t_surf = font.render(label, True, text_col)
        tx = rect.x + 14 if align_left else rect.centerx - t_surf.get_width() // 2
        ty = rect.centery - t_surf.get_height() // 2
        self.screen.blit(t_surf, (tx, ty))

    def show_toast(self, text: str, duration: float = 5.0):
        self.toast_msg = text
        self.toast_timer = duration

    def open_dialogue_with(self, npc: SimCharacter):
        self.talking_npc = npc
        self.npc_greeting, self.npc_options = self.world.get_npc_greeting_and_options(npc)
        self.typewriter_chars = 0.0
        self.custom_input = ""
        self.typing_custom = False
        self.active_modal = "DIALOGUE"

    def run(self, max_frames: int = None):
        running = True
        frame_count = 0

        while running:
            dt = min(0.05, self.clock.tick(FPS) / 1000.0)
            frame_count += 1
            if max_frames and frame_count >= max_frames:
                break

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    self._handle_keydown(event)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self._handle_mouse_click(event.pos)

            if self.active_modal == "DIALOGUE":
                self.typewriter_chars = min(float(len(self.npc_greeting)), self.typewriter_chars + dt * 115.0)

            if self.active_modal in ("FAMILY_SELECT", "LORE_PROLOGUE"):
                self._render()
                pygame.display.flip()
                continue

            move_dir = (0.0, 0.0)
            if self.active_modal is None:
                keys = pygame.key.get_pressed()
                dx = float(keys[pygame.K_d] or keys[pygame.K_RIGHT]) - float(keys[pygame.K_a] or keys[pygame.K_LEFT])
                dy = float(keys[pygame.K_s] or keys[pygame.K_DOWN]) - float(keys[pygame.K_w] or keys[pygame.K_UP])
                move_dir = (dx, dy)

            self.world.update(dt, move_dir)

            if self.toast_timer > 0:
                self.toast_timer = max(0.0, self.toast_timer - dt)

            player = self.world.get_player()
            tx = max(0.0, min(WORLD_WIDTH - SCREEN_WIDTH, player.x - SCREEN_WIDTH * 0.5))
            ty = max(0.0, min(WORLD_HEIGHT - SCREEN_HEIGHT, player.y - SCREEN_HEIGHT * 0.5))
            self.cam_x += (tx - self.cam_x) * min(1.0, dt * 8.5)
            self.cam_y += (ty - self.cam_y) * min(1.0, dt * 8.5)

            self._render()
            pygame.display.flip()

        pygame.quit()

    def _choose_character_from_menu(self, char_id: str, open_lore: bool = True):
        msg = self.world.switch_active_family_member(char_id)
        p = self.world.get_player()
        self.cam_x = max(0.0, min(WORLD_WIDTH - SCREEN_WIDTH, p.x - SCREEN_WIDTH * 0.5))
        self.cam_y = max(0.0, min(WORLD_HEIGHT - SCREEN_HEIGHT, p.y - SCREEN_HEIGHT * 0.5))
        if open_lore:
            self.active_modal = "LORE_PROLOGUE"
        else:
            self.active_modal = None
            self.show_toast(msg)

    def _trigger_interact(self):
        kind, target = self.world.get_nearest_interactable(max_dist=108.0)
        if kind == "npc":
            self.open_dialogue_with(target)
        elif kind == "obj":
            msg = self.world.interact_with_object(target)
            self.show_toast(msg, duration=6.0)
        else:
            self.show_toast("Walk close to any Person or Terminal and press [E]!")

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
        if self.active_modal == "FAMILY_SELECT":
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.active_modal = "LORE_PROLOGUE"
            elif event.key == pygame.K_ESCAPE:
                self.active_modal = None if self.has_seen_prologue else "LORE_PROLOGUE"
            elif event.key == pygame.K_1:
                self._choose_character_from_menu("arthur", open_lore=True)
            elif event.key == pygame.K_2:
                self._choose_character_from_menu("elena", open_lore=True)
            elif event.key == pygame.K_3:
                self._choose_character_from_menu("maya", open_lore=True)
            elif event.key == pygame.K_4:
                self._choose_character_from_menu("leo", open_lore=True)
            elif event.key == pygame.K_n:
                self.world.start_new_campaign(player_char_id=self.world.player_char_id)
                self.active_modal = "LORE_PROLOGUE"
                self.show_toast("Generated a New Randomized Mystery Campaign!")
            return

        if self.active_modal == "LORE_PROLOGUE":
            if event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_e, pygame.K_ESCAPE):
                self.has_seen_prologue = True
                self.active_modal = None
                p = self.world.get_player()
                self.show_toast(
                    f"5:00 PM: Playing as {p.name}. Investigate the neighborhood & check your Case File [N]!"
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
                    self.world.start_new_campaign(player_char_id=self.world.player_char_id)
                    self.active_modal = "LORE_PROLOGUE"
                    self.show_toast("Started a Brand-New Mystery with a Different Saboteur & Passcode!")
                else:
                    self.world.start_loop(player_char_id=self.world.player_char_id, is_new_loop=True)
                    self.show_toast(f"Loop #{self.world.loop_id} Started at 5:00 PM! All Case File Clues Kept!")
            return

        if event.key in (pygame.K_e, pygame.K_SPACE, pygame.K_RETURN):
            self._trigger_interact()
        elif event.key == pygame.K_f:
            self.active_modal = "FAMILY_SELECT"
        elif event.key == pygame.K_l:
            self.active_modal = "LORE_PROLOGUE"
        elif event.key == pygame.K_n:
            self.active_modal = "NOTEBOOK"
        elif event.key == pygame.K_k:
            self.active_modal = "API_CONFIG"
        elif event.key == pygame.K_1:
            self._choose_character_from_menu("arthur", open_lore=False)
        elif event.key == pygame.K_2:
            self._choose_character_from_menu("elena", open_lore=False)
        elif event.key == pygame.K_3:
            self._choose_character_from_menu("maya", open_lore=False)
        elif event.key == pygame.K_4:
            self._choose_character_from_menu("leo", open_lore=False)

    def _handle_mouse_click(self, pos: tuple[int, int]):
        mx, my = pos

        if self.active_modal == "FAMILY_SELECT":
            family_ids = ["arthur", "elena", "maya", "leo"]
            for idx, fid in enumerate(family_ids):
                if pygame.Rect(110 + idx * 290, 245, 270, 405).collidepoint(mx, my):
                    self._choose_character_from_menu(fid, open_lore=True)
                    return
            if pygame.Rect(340, 685, 680, 56).collidepoint(mx, my):
                self.active_modal = "LORE_PROLOGUE"
            return

        if self.active_modal == "LORE_PROLOGUE":
            if pygame.Rect(400, 708, 560, 56).collidepoint(mx, my):
                self.has_seen_prologue = True
                self.active_modal = None
                p = self.world.get_player()
                self.show_toast(f"5:00 PM: Playing as {p.name}. Walk with [WASD/Arrows] & press [E] to investigate!")
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
            if not pygame.Rect(190, 95, 980, 650).collidepoint(mx, my):
                self.active_modal = None
            return

        # Top Floating Figma Dock Clicks
        if my <= 68:
            family_ids = ["arthur", "elena", "maya", "leo"]
            for idx, fid in enumerate(family_ids):
                if pygame.Rect(920 + idx * 54, 12, 48, 44).collidepoint(mx, my):
                    self._choose_character_from_menu(fid, open_lore=False)
                    return
            if pygame.Rect(1144, 12, 102, 44).collidepoint(mx, my):
                self.active_modal = "NOTEBOOK"
                return
            if pygame.Rect(1252, 12, 94, 44).collidepoint(mx, my):
                self.active_modal = "FAMILY_SELECT"
                return
            return

        if self.active_modal is None:
            wx = mx + self.cam_x
            wy = my + self.cam_y
            player = self.world.get_player()
            for char in self.world.characters.values():
                if not char.is_player and not char.arrested and math.hypot(wx - char.x, wy - (char.y - 24)) <= 48.0:
                    if math.hypot(player.x - char.x, player.y - char.y) <= 135.0:
                        self.open_dialogue_with(char)
                    else:
                        self.show_toast(f"Walk closer to {char.name} to talk!")
                    return

    # =========================================================================
    # 2.5D DEFINED PIXEL-ART WORLD & UNIFIED Y-SORT RENDERING PIPELINE
    # =========================================================================
    def _render(self):
        # 1. Render 2.5D Town Ground, Timber Buildings, Y-Sorted Furniture, Props & Characters
        self._render_world()

        # 2. Render Simplified Figma-Style Floating Top HUD
        self._render_top_bar()

        # 3. Render Toast Notification Pill
        if self.toast_timer > 0 and self.toast_msg and self.active_modal is None:
            self._render_toast()

        # 4. Render Active Modal
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

        # A. Blit Pre-Baked 2.5D Cobblestone, Grass & Timber-Frame Building Canvas
        view_rect = pygame.Rect(cx, cy, SCREEN_WIDTH, SCREEN_HEIGHT)
        self.screen.blit(self.art_engine.world_ground_surface, (0, 0), area=view_rect)

        # B. Draw Building Roof Signboards on Gable Headers
        for b in BUILDINGS:
            rx, ry, rw, _ = b["rect"]
            sx = rx + rw // 2 - cx
            sy = ry + 18 - cy
            if -200 <= sx <= SCREEN_WIDTH + 200 and -60 <= sy <= SCREEN_HEIGHT + 60:
                lbl = self.font_md.render(b["name"], True, (252, 245, 225))
                sign_rect = pygame.Rect(sx - lbl.get_width() // 2 - 14, sy - 11, lbl.get_width() + 28, 28)
                pygame.draw.rect(self.screen, (48, 32, 22), sign_rect, border_radius=6)
                pygame.draw.rect(self.screen, (225, 185, 95), sign_rect, 2, border_radius=6)
                self.screen.blit(lbl, (sx - lbl.get_width() // 2, sy - 7))

        # C. Build Unified YSort Depth List (Furniture, Quest Props, Trees, Street Props, Vehicles, Characters)
        renderables = []

        # 1. 3D-Extruded Furniture, Tables, Chairs, Market Stalls, Fountain & Generator
        for b in BUILDINGS:
            for f in b["furniture"]:
                fx, fy, fw, fh = f["rect"]
                sort_y = fy if "Gym Court" in f["name"] else (fy + fh - 6)
                renderables.append((sort_y, "furniture", f))

        # 2. Animated Quest Items & Interactive Terminals
        for wobj in self.world.objects.values():
            renderables.append((wobj["y"] + 4, "quest_obj", wobj))

        # 3. 2.5D Trees
        for tx, ty in self.trees:
            renderables.append((ty + 18, "tree", (tx, ty)))

        # 4. Street Props (Barrels, Crates, Flower Carts, Glowing Street Lamps)
        for ptype, px, py in self.art_engine.street_props:
            renderables.append((py, "prop", (ptype, px, py)))

        # 5. Street Vehicles
        for veh in self.world.grid_engine.vehicles:
            renderables.append((veh.y + 12, "vehicle", veh))

        # 6. All 24 Animated 2.5D Characters
        for char in self.world.characters.values():
            if not char.arrested:
                renderables.append((char.y, "char", char))

        # Sort by Y anchor only (prevents comparing dicts/objects if two Y values match!)
        renderables.sort(key=lambda item: item[0])

        # Footstep & magic particles on the ground
        self.world.particles.update_and_draw(self.screen, self.cam_x, self.cam_y, 1.0 / FPS)

        player = self.world.get_player()
        for _, kind, obj in renderables:
            if kind == "furniture":
                self.art_engine.draw_25d_furniture(self.screen, obj, self.cam_x, self.cam_y, t_sec)
            elif kind == "quest_obj":
                self.art_engine.draw_quest_object(self.screen, obj, self.cam_x, self.cam_y, t_sec)
            elif kind == "tree":
                tx, ty = obj
                self.screen.blit(self.art_engine.tree_sprite, (int(tx - self.cam_x - 48), int(ty - self.cam_y - 90)))
            elif kind == "prop":
                ptype, px, py = obj
                self.art_engine.draw_street_prop(self.screen, ptype, px, py, self.cam_x, self.cam_y, t_sec)
            elif kind == "vehicle":
                obj.draw(self.screen, self.cam_x, self.cam_y)
            elif kind == "char":
                char = obj
                has_anchor = char.memory_store.has_anchored_memory()
                has_grudge = player.id in char.grudges

                char.rig.draw(
                    surface=self.screen,
                    wx=char.x,
                    wy=char.y,
                    cam_x=self.cam_x,
                    cam_y=self.cam_y,
                    is_player=char.is_player,
                    has_quest_marker=None,
                    has_memory_anchor=has_anchor,
                )

                sx, sy = int(char.x - self.cam_x), int(char.y - self.cam_y)
                short_n = char.name.split("(")[0].strip()
                if char.is_player:
                    short_n = f"YOU: {short_n}"

                ncol = (
                    COLORS["cyan"]
                    if char.is_player
                    else (COLORS["red"] if has_grudge else (COLORS["gold"] if char.is_family else COLORS["white"]))
                )
                nlbl = self.font_xs.render(short_n, True, ncol)
                npill = pygame.Rect(sx - nlbl.get_width() // 2 - 6, sy + 7, nlbl.get_width() + 12, 18)
                pygame.draw.rect(self.screen, (16, 20, 30), npill, border_radius=6)
                pygame.draw.rect(self.screen, (52, 64, 88), npill, 1, border_radius=6)
                self.screen.blit(nlbl, (sx - nlbl.get_width() // 2, sy + 8))

                if char.speech_bubble and self.active_modal != "DIALOGUE":
                    self._draw_small_bubble(sx, sy - 72, char.speech_bubble)

        # D. Floating Context Action Pill above the single closest interactable
        nearest_kind, nearest_target = self.world.get_nearest_interactable(max_dist=108.0)
        if nearest_target is not None and self.active_modal is None:
            if nearest_kind == "npc":
                tx_p, ty_p = int(nearest_target.x - self.cam_x), int(nearest_target.y - self.cam_y - 70)
                ptxt = f"[E] Talk to {nearest_target.name.split('(')[0].strip()}"
            else:
                tx_p, ty_p = int(nearest_target["x"] - self.cam_x), int(nearest_target["y"] - self.cam_y - 44)
                ptxt = f"[E] Inspect {nearest_target['name']}"
            psurf = self.font_sm.render(ptxt, True, COLORS["gold"])
            ppill = pygame.Rect(tx_p - psurf.get_width() // 2 - 12, ty_p - 6, psurf.get_width() + 24, 28)
            self._draw_figma_card(ppill, bg_rgba=(16, 20, 32, 240), border_col=COLORS["gold"], radius=14, shadow_offset=4)
            self.screen.blit(psurf, (tx_p - psurf.get_width() // 2, ty_p - 1))

    def _draw_small_bubble(self, x: int, y: int, text: str):
        short = text[:50] + ("..." if len(text) > 50 else "")
        surf = self.font_xs.render(short, True, COLORS["white"])
        w = surf.get_width() + 18
        rect = pygame.Rect(x - w // 2, y - 24, w, 24)
        self._draw_figma_card(rect, bg_rgba=(20, 26, 40, 232), border_col=(95, 115, 150), radius=10, border_w=1, shadow_offset=3)
        self.screen.blit(surf, (x - surf.get_width() // 2, y - 19))

    # =========================================================================
    # SIMPLIFIED FIGMA / CANVA FLOATING HUD & MODALS
    # =========================================================================
    def _render_top_bar(self):
        """
        Simplified Figma-style 3-pill Floating Top HUD:
        1. Left Pill: In-Game Clock (5:00 PM -> 6:00 PM), Progress Bar & Current Zone
        2. Center Pill: Current Detective Stage & Concise Goal
        3. Right Dock: [1-4] Family Switcher Badges + [N] Case File + [F] Lore/Menu
        """
        p = self.world.get_player()
        loc_name = self.world.get_building_name_at(p.x, p.y)
        obj_info = self.world.get_current_objective()

        # 1. Top-Left Clock & Location Card
        clock_card = pygame.Rect(14, 10, 250, 50)
        self._draw_figma_card(clock_card, bg_rgba=(18, 23, 36, 236), border_col=(82, 102, 138), radius=14)
        rem = int(self.world.time_remaining)
        clock_str = self.world.get_clock_string()
        t_col = COLORS["red"] if rem < 45 else COLORS["gold"]
        self.screen.blit(self.font_md.render(f"{clock_str}  •  Loop #{self.world.loop_id}", True, t_col), (28, 15))
        self.screen.blit(self.font_xs.render(loc_name[:28], True, COLORS["cyan"]), (28, 37))

        # 2. Top-Center Detective Stage & Objective Card
        goal_card = pygame.Rect(274, 10, 634, 50)
        self._draw_figma_card(goal_card, bg_rgba=(18, 23, 36, 236), border_col=(215, 178, 85), radius=14)
        self.screen.blit(self.font_xs.render(obj_info["chapter_title"], True, COLORS["gold"]), (290, 15))
        inst_short = obj_info["instruction"]
        if len(inst_short) > 78:
            inst_short = inst_short[:75] + "..."
        self.screen.blit(self.font_xs.render(inst_short, True, COLORS["white"]), (290, 35))

        # 3. Top-Right Family Switcher Dock ([1]..[4]) + [N] Case File + [F] Menu
        family_ids = [("arthur", "Dad"), ("elena", "Mom"), ("maya", "Maya"), ("leo", "Leo")]
        for idx, (fid, short_lbl) in enumerate(family_ids):
            btn = pygame.Rect(920 + idx * 54, 12, 48, 44)
            is_act = self.world.player_char_id == fid
            self._draw_figma_button(
                btn,
                f"{idx + 1}:{short_lbl}",
                self.font_xs,
                bg_col=(42, 84, 118) if is_act else (26, 32, 46),
                border_col=COLORS["gold"] if is_act else (75, 92, 122),
                radius=10,
            )

        self._draw_figma_button(
            pygame.Rect(1144, 12, 102, 44),
            f"[N] Clues ({len(self.world.notebook_clues)})",
            self.font_xs,
            bg_col=(26, 36, 54),
            border_col=COLORS["cyan"],
            radius=10,
        )
        self._draw_figma_button(
            pygame.Rect(1252, 12, 94, 44),
            "[F] Family",
            self.font_xs,
            bg_col=(38, 34, 52),
            border_col=COLORS["gold"],
            radius=10,
        )

    def _render_toast(self):
        surf = self.font_sm.render(self.toast_msg, True, COLORS["white"])
        w = min(SCREEN_WIDTH - 40, surf.get_width() + 36)
        rect = pygame.Rect((SCREEN_WIDTH - w) // 2, SCREEN_HEIGHT - 58, w, 40)
        self._draw_figma_card(rect, bg_rgba=(16, 20, 32, 242), border_col=COLORS["gold"], radius=20)
        self.screen.blit(surf, (rect.x + 18, rect.y + 11))

    def _render_bottom_dialogue_box(self):
        """Figma-Styled Bottom RPG Dialogue Card with High-Res Portrait, Rapport Meter & Hover Pills."""
        npc = self.talking_npc
        if not npc:
            return

        player = self.world.get_player()
        fam_id = player.id

        box = pygame.Rect(46, 530, 1268, 312)
        self._draw_figma_card(box, bg_rgba=(16, 21, 34, 246), border_col=COLORS["ui_border"], radius=20, border_w=2, shadow_offset=8)

        # 1. Framed Character Bust Portrait on the Left
        p_rect = pygame.Rect(72, 554, 142, 142)
        t_phase = pygame.time.get_ticks() / 1000.0
        is_typing = self.typewriter_chars < len(self.npc_greeting)
        draw_character_portrait(self.screen, p_rect, npc.spec, anim_phase=(t_phase if is_typing else 0.0))

        # Relationship Status Pill & Visual Rapport Progress Bar
        rel_status = npc.get_relationship_status(fam_id)
        rel_col = (
            COLORS["red"]
            if "GRUDGE" in rel_status
            else (COLORS["gold"] if npc.is_family else (COLORS["green"] if "ALLY" in rel_status else COLORS["cyan"]))
        )
        r_tag = self.font_xs.render(rel_status, True, rel_col)
        self.screen.blit(r_tag, (p_rect.centerx - r_tag.get_width() // 2, 704))

        rapport_val = npc.get_rapport(fam_id)
        bar_bg = pygame.Rect(76, 724, 134, 8)
        pygame.draw.rect(self.screen, (36, 44, 62), bar_bg, border_radius=4)
        pygame.draw.rect(self.screen, rel_col, (76, 724, int(1.34 * rapport_val), 8), border_radius=4)
        trust_tag = self.font_xs.render(f"Rapport: {rapport_val}%", True, COLORS["text_dim"])
        self.screen.blit(trust_tag, (p_rect.centerx - trust_tag.get_width() // 2, 736))

        # 2. Character Name, Role & Schedule Badge
        x_text = 245
        name_hdr = self.font_lg.render(f"{npc.name}  —  {npc.role}", True, COLORS["gold"])
        self.screen.blit(name_hdr, (x_text, 548))

        sched_hdr = self.font_xs.render(
            f"Routine ({self.world.get_clock_string()}): {npc.current_schedule_label}   •   Speaking with: {player.name}",
            True,
            COLORS["cyan"],
        )
        self.screen.blit(sched_hdr, (x_text, 576))

        # Spoken Dialogue Box
        msg_panel = pygame.Rect(x_text, 598, 825, 80)
        pygame.draw.rect(self.screen, (24, 30, 46), msg_panel, border_radius=10)
        pygame.draw.rect(self.screen, (52, 66, 94), msg_panel, 1, border_radius=10)

        visible_text = self.npc_greeting[: int(self.typewriter_chars)]
        words = visible_text.split()
        lines, curr = [], ""
        for w in words:
            if len(curr) + len(w) + 1 <= 86:
                curr = f"{curr} {w}".strip()
            else:
                lines.append(curr)
                curr = w
        if curr:
            lines.append(curr)

        for idx, ln in enumerate(lines[:3]):
            self.screen.blit(self.font_md.render(ln, True, COLORS["white"]), (x_text + 14, 606 + idx * 23))

        # 3. 4 Modern Interactive Choice Pills
        if self.typing_custom:
            inp_box = pygame.Rect(x_text, 700, 825, 46)
            pygame.draw.rect(self.screen, (12, 15, 22), inp_box, border_radius=8)
            pygame.draw.rect(self.screen, COLORS["green"], inp_box, 2, border_radius=8)
            self.screen.blit(
                self.font_md.render(f"Ask AI > {self.custom_input}_", True, COLORS["white"]),
                (x_text + 14, 712),
            )
            self.screen.blit(
                self.font_xs.render("Press [ENTER] to Send to AI   |   [ESC] Cancel", True, COLORS["text_dim"]),
                (x_text, 758),
            )
        else:
            for idx, opt_txt in enumerate(self.npc_options[:4]):
                btn = pygame.Rect(x_text, 686 + idx * 34, 825, 30)
                is_accuse = idx == 3
                self._draw_figma_button(
                    btn,
                    f"[{idx + 1}]  {opt_txt}",
                    self.font_sm,
                    bg_col=(58, 32, 38) if is_accuse else (28, 36, 54),
                    hover_col=(82, 44, 52) if is_accuse else (44, 58, 86),
                    border_col=COLORS["gold"] if is_accuse else COLORS["cyan"],
                    radius=8,
                    align_left=True,
                )

        # 4. Right-Side Action Dock ([R] Deja-Vu, [T] Ask AI, [ESC] Close)
        r_btn = pygame.Rect(1085, 686, 200, 64)
        self._draw_figma_button(
            r_btn,
            f"[R] Deja-Vu ({self.world.deja_vu_charges})",
            self.font_sm,
            bg_col=(26, 62, 50),
            hover_col=(38, 86, 68),
            border_col=COLORS["green"],
            text_col=COLORS["green"],
            radius=10,
        )
        self._draw_figma_button(
            pygame.Rect(1085, 758, 200, 30),
            "[T] Ask Custom AI",
            self.font_xs,
            bg_col=(30, 42, 64),
            border_col=COLORS["cyan"],
            radius=8,
        )
        self._draw_figma_button(
            pygame.Rect(1085, 794, 200, 32),
            "[ESC] Close Dialogue",
            self.font_xs,
            bg_col=(54, 32, 40),
            border_col=COLORS["red"],
            radius=8,
        )

    def _render_family_select_modal(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((8, 12, 20, 215))
        self.screen.blit(overlay, (0, 0))

        panel = pygame.Rect(76, 46, 1208, 758)
        self._draw_figma_card(panel, bg_rgba=(18, 24, 38, 248), border_col=COLORS["gold"], radius=22, border_w=2, shadow_offset=10)

        t_surf = self.font_xl.render("MAPLEWOOD LOOP  •  SELECT YOUR FAMILY CHARACTER", True, COLORS["gold"])
        self.screen.blit(t_surf, (panel.centerx - t_surf.get_width() // 2, 72))

        sub = self.font_sm.render(
            "5:00 PM - 6:00 PM Mystery RPG  |  Switch between all 4 Mercer family members anytime with [1], [2], [3], [4]",
            True,
            COLORS["cyan"],
        )
        self.screen.blit(sub, (panel.centerx - sub.get_width() // 2, 112))

        family_ids = ["arthur", "elena", "maya", "leo"]
        t_phase = pygame.time.get_ticks() / 1000.0
        mx, my = pygame.mouse.get_pos()

        for idx, fid in enumerate(family_ids):
            char = self.world.characters[fid]
            cx = 110 + idx * 290
            cy = 165
            c_rect = pygame.Rect(cx, cy, 270, 485)
            is_sel = self.world.player_char_id == fid
            is_hov = c_rect.collidepoint(mx, my)

            self._draw_figma_card(
                c_rect,
                bg_rgba=(38, 50, 76, 250) if (is_sel or is_hov) else (26, 33, 50, 245),
                border_col=COLORS["gold"] if (is_sel or is_hov) else (72, 88, 120),
                radius=16,
                border_w=3 if is_sel else 2,
                shadow_offset=6,
            )

            badge_rect = pygame.Rect(cx + 55, cy + 16, 160, 28)
            pygame.draw.rect(self.screen, (24, 32, 48), badge_rect, border_radius=14)
            k_lbl = self.font_xs.render(
                f"PRESS [{idx + 1}] OR CLICK", True, COLORS["gold"] if is_sel else COLORS["cyan"]
            )
            self.screen.blit(k_lbl, (badge_rect.centerx - k_lbl.get_width() // 2, badge_rect.centery - k_lbl.get_height() // 2))

            # High-Res Generative AI Portrait in each Family Card!
            port_rect = pygame.Rect(cx + 45, cy + 56, 180, 180)
            draw_character_portrait(self.screen, port_rect, char.spec, anim_phase=(t_phase if is_sel else 0.0))

            n_lbl = self.font_md.render(char.name, True, COLORS["white"])
            self.screen.blit(n_lbl, (c_rect.centerx - n_lbl.get_width() // 2, cy + 250))

            r_lbl = self.font_xs.render(char.role, True, COLORS["cyan"])
            self.screen.blit(r_lbl, (c_rect.centerx - r_lbl.get_width() // 2, cy + 276))

            words = char.perk.split()
            lines, cur = [], ""
            for w in words:
                if len(cur) + len(w) + 1 <= 33:
                    cur = f"{cur} {w}".strip()
                else:
                    lines.append(cur)
                    cur = w
            if cur:
                lines.append(cur)
            for l_i, ln in enumerate(lines[:3]):
                self.screen.blit(self.font_xs.render(ln, True, COLORS["text_dim"]), (cx + 18, cy + 314 + l_i * 20))

            loc_now = self.world.get_building_name_at(char.x, char.y)
            self.screen.blit(self.font_xs.render(f"Zone: {loc_now[:24]}", True, COLORS["green"]), (cx + 18, cy + 435))

        self._draw_figma_button(
            pygame.Rect(340, 685, 680, 56),
            f"CONTINUE TO STARTING LORE AS {self.world.get_player().name.upper()} [SPACE]",
            self.font_md,
            bg_col=(32, 118, 74),
            hover_col=(44, 148, 92),
            border_col=COLORS["green"],
            radius=14,
        )

    def _render_lore_prologue_modal(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((8, 12, 20, 228))
        self.screen.blit(overlay, (0, 0))

        panel = pygame.Rect(88, 46, 1184, 762)
        self._draw_figma_card(panel, bg_rgba=(18, 24, 38, 248), border_col=COLORS["gold"], radius=22, border_w=2, shadow_offset=10)

        p = self.world.get_player()
        lore_data = FAMILY_LORE_PROLOGUES.get(p.id, FAMILY_LORE_PROLOGUES["arthur"])

        hdr = self.font_xl.render("PROLOGUE  •  THE 6:00 PM AETHER-CORE ANOMALY", True, COLORS["gold"])
        self.screen.blit(hdr, (panel.centerx - hdr.get_width() // 2, 70))

        town_box = pygame.Rect(125, 118, 1110, 275)
        self._draw_figma_card(town_box, bg_rgba=(26, 34, 50, 245), border_col=(72, 90, 124), radius=14, border_w=1, shadow_offset=4)

        for idx, line in enumerate(TOWN_LORE_PROLOGUE):
            col = COLORS["cyan"] if idx == 0 else COLORS["white"]
            font_use = self.font_md if idx == 0 else self.font_sm
            self.screen.blit(font_use.render(line, True, col), (148, 132 + idx * 20))

        char_box = pygame.Rect(125, 410, 1110, 270)
        self._draw_figma_card(char_box, bg_rgba=(30, 40, 60, 245), border_col=COLORS["gold"], radius=14, border_w=2, shadow_offset=4)

        t_phase = pygame.time.get_ticks() / 1000.0
        port_rect = pygame.Rect(148, 434, 165, 165)
        draw_character_portrait(self.screen, port_rect, p.spec, anim_phase=t_phase)

        c_hdr = self.font_lg.render(lore_data["headline"], True, COLORS["gold"])
        self.screen.blit(c_hdr, (336, 432))

        words = lore_data["story"].split()
        lines, cur = [], ""
        for w in words:
            if len(cur) + len(w) + 1 <= 86:
                cur = f"{cur} {w}".strip()
            else:
                lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)

        for idx, ln in enumerate(lines[:5]):
            self.screen.blit(self.font_md.render(ln, True, COLORS["white"]), (336, 470 + idx * 25))

        spec_lbl = self.font_sm.render(f"SPECIALTY: {lore_data['specialty']}", True, COLORS["green"])
        self.screen.blit(spec_lbl, (336, 608))

        tip_lbl = self.font_xs.render(
            "DETECTIVE TIP: Watch NPC afternoon schedules (5:00-6:00 PM), inspect cross-zone terminals, and press [N] for your Case File.",
            True,
            COLORS["cyan"],
        )
        self.screen.blit(tip_lbl, (148, 646))

        self._draw_figma_button(
            pygame.Rect(125, 708, 245, 56),
            "[F] CHANGE CHARACTER",
            self.font_sm,
            bg_col=(30, 40, 62),
            border_col=COLORS["cyan"],
            radius=12,
        )
        self._draw_figma_button(
            pygame.Rect(400, 708, 560, 56),
            "ENTER MAPLEWOOD HEIGHTS AT 5:00 PM [SPACE]",
            self.font_md,
            bg_col=(32, 118, 74),
            hover_col=(44, 148, 92),
            border_col=COLORS["green"],
            radius=14,
        )

    def _render_notebook_modal(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((8, 12, 20, 185))
        self.screen.blit(overlay, (0, 0))

        rect = pygame.Rect(190, 95, 980, 650)
        self._draw_figma_card(rect, bg_rgba=(18, 24, 38, 248), border_col=COLORS["cyan"], radius=20, border_w=2, shadow_offset=10)

        x0, y0 = rect.x + 32, rect.y + 28
        self.screen.blit(
            self.font_xl.render("MERCER FAMILY CASE FILE  •  CROSS-ZONE TRACKER", True, COLORS["gold"]),
            (x0, y0),
        )
        y0 += 44

        obj_info = self.world.get_current_objective()
        self.screen.blit(self.font_md.render(obj_info["chapter_title"], True, COLORS["cyan"]), (x0, y0))
        y0 += 26
        self.screen.blit(self.font_sm.render(obj_info["instruction"], True, COLORS["green"]), (x0, y0))
        y0 += 38

        zs = self.world.zone_state
        checks = [
            ("Cafe Witness Interviewed", zs["witness_interviewed"]),
            ("Market Hardware Register Checked", zs["market_manifest_logged"]),
            ("Suspect Identified", zs["saboteur_identified"]),
            ("High School Lab Calibrated", zs["school_lab_calibrated"]),
            ("Office Shutdown Code Unlocked", zs["office_code_unlocked"]),
            ("Physical Evidence Confiscated", zs["evidence_confiscated"]),
            ("Police Clearance Granted", zs["police_clearance_granted"]),
        ]
        self.screen.blit(self.font_md.render("Cross-Zone Investigation Milestones:", True, COLORS["gold"]), (x0, y0))
        y0 += 28
        for idx, (label, done) in enumerate(checks):
            col = COLORS["green"] if done else COLORS["text_muted"]
            mark = "[DONE]" if done else "[PENDING]"
            cx_pos = x0 + (idx % 2) * 450
            cy_pos = y0 + (idx // 2) * 25
            self.screen.blit(self.font_xs.render(f"{mark}  {label}", True, col), (cx_pos, cy_pos))
        y0 += 112

        self.screen.blit(self.font_md.render("Recorded Clues & Evidence Across Loops:", True, COLORS["gold"]), (x0, y0))
        y0 += 28
        for clue in self.world.notebook_clues[-9:]:
            self.screen.blit(self.font_sm.render(f"•  {clue}", True, COLORS["white"]), (x0 + 8, y0))
            y0 += 25

        self.screen.blit(
            self.font_xs.render(
                "Press [N] or [ESC] to Close Case File   |   Press [L] to View Starting Lore",
                True,
                COLORS["text_dim"],
            ),
            (x0, rect.bottom - 34),
        )

    def _render_api_config_modal(self):
        rect = pygame.Rect(310, 240, 740, 250)
        self._draw_figma_card(rect, bg_rgba=(18, 24, 38, 248), border_col=COLORS["gold"], radius=18)
        x0, y0 = rect.x + 28, rect.y + 28
        self.screen.blit(self.font_lg.render("CLOUD LLM API KEY ([TAB] Gemini / OpenAI)", True, COLORS["gold"]), (x0, y0))
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
        col = COLORS["green"] if is_win else COLORS["gold"]
        rect = pygame.Rect(220, 210, 920, 350)
        self._draw_figma_card(rect, bg_rgba=(18, 24, 38, 248), border_col=col, radius=20, border_w=3, shadow_offset=10)

        x0, y0 = rect.x + 34, rect.y + 30
        hdr = (
            "MYSTERY SOLVED — MAPLEWOOD HEIGHTS SAVED!"
            if is_win
            else f"6:00 PM TIME REWIND -> STARTING LOOP #{self.world.loop_id + 1}"
        )
        self.screen.blit(self.font_xl.render(hdr, True, col), (x0, y0))
        y0 += 56

        words = self.world.outcome_reason.split()
        curr = ""
        for w in words:
            if len(curr) + len(w) + 1 <= 74:
                curr = f"{curr} {w}".strip()
            else:
                self.screen.blit(self.font_md.render(curr, True, COLORS["white"]), (x0, y0))
                y0 += 28
                curr = w
        if curr:
            self.screen.blit(self.font_md.render(curr, True, COLORS["white"]), (x0, y0))
            y0 += 46

        btn_txt = (
            "Press [SPACE] to Start a Brand-New Randomized Mystery Campaign!"
            if is_win
            else f"Press [SPACE] to Resume Investigation at 5:00 PM in Loop #{self.world.loop_id + 1}!"
        )
        self.screen.blit(self.font_lg.render(btn_txt, True, COLORS["cyan"]), (x0, y0))


if __name__ == "__main__":
    headless = "--test-headless" in sys.argv
    app = MaplewoodRPGApp(headless_test=headless)
    app.run(max_frames=90 if headless else None)
