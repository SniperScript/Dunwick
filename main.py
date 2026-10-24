"""
MAPLEWOOD LOOP // 2.5D Family Time-Loop Mystery RPG
Architected using patterns from:
- Tiny Life: Live multi-character household switching ([1-4]) & 5:00 PM - 6:00 PM schedules
- IsoCity: Tile-grid sidewalk/crosswalk navigation & yielding street vehicles
- Unknown Horizons: Cross-zone terminal state persistence
- IslandEscape: Per-character rapport & grudge memory tables
- OpenPixel-RPG: Starting Lore Prologue screen & classic bottom RPG dialogue box with portrait
"""

import math
import os
import sys
import pygame

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

        # Clean sans-serif fonts (ASCII/English only — zero missing glyph boxes!)
        self.font_xs = pygame.font.SysFont("DejaVu Sans, Arial, sans-serif", 13, bold=True)
        self.font_sm = pygame.font.SysFont("DejaVu Sans, Arial, sans-serif", 15, bold=True)
        self.font_md = pygame.font.SysFont("DejaVu Sans, Arial, sans-serif", 18, bold=True)
        self.font_lg = pygame.font.SysFont("DejaVu Sans, Arial, sans-serif", 22, bold=True)
        self.font_xl = pygame.font.SysFont("DejaVu Sans, Arial, sans-serif", 28, bold=True)

        self.llm_broker = CloudLLMBroker()
        self.world = SimulationWorld(self.llm_broker)

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

        self.toast_msg = "5:00 PM in Maplewood Heights. Walk with [WASD/Arrows], press [E] to interact, [1-4] to switch family!"
        self.toast_timer = 7.0

        # Decorative trees outside buildings (placed clear of sidewalks and doorways)
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
                self.typewriter_chars = min(float(len(self.npc_greeting)), self.typewriter_chars + dt * 110.0)

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
            self.show_toast(msg, duration=6.5)
        else:
            self.show_toast("Walk up to any Person or Terminal Table and press [E]!")

    def _select_dialogue_choice_in_box(self, option_idx: int, custom_text: str = ""):
        """Executes the player's question and updates the RPG dialogue box with the NPC's spoken reply!"""
        if not self.talking_npc:
            return
        npc = self.talking_npc
        msg = self.world.select_dialogue_option(npc, option_idx, custom_text=custom_text)
        # Update the dialogue box text to the NPC's new spoken line so the player can read it in the box
        if npc.speech_bubble:
            self.npc_greeting = npc.speech_bubble
        else:
            self.npc_greeting = msg
        # Refresh options in case evidence state changed
        _, self.npc_options = self.world.get_npc_greeting_and_options(npc)
        self.typewriter_chars = 0.0
        self.typing_custom = False
        self.show_toast(msg, duration=6.0)

    def _handle_keydown(self, event: pygame.event.Event):
        # 1. Family Select Screen -> Transitions to Starting Lore Prologue!
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

        # 2. Starting Lore Prologue Screen (Shown after Character Selection!)
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

        # 3. Classic Bottom RPG Dialogue Box
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
                self.show_toast(msg, duration=6.5)
            elif event.key == pygame.K_t:
                self.typing_custom = True
                self.custom_input = ""
            return

        # 4. Case File Notebook or API Modal
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

        # 5. Outcome Modal
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

        # 6. Normal Gameplay Hotkeys (Including Live Tiny-Life Family Switching [1-4]!)
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

        # 1. Family Select Clicks
        if self.active_modal == "FAMILY_SELECT":
            family_ids = ["arthur", "elena", "maya", "leo"]
            for idx, fid in enumerate(family_ids):
                if pygame.Rect(110 + idx * 290, 255, 270, 395).collidepoint(mx, my):
                    self._choose_character_from_menu(fid, open_lore=True)
                    return
            if pygame.Rect(420, 685, 520, 56).collidepoint(mx, my):
                self.active_modal = "LORE_PROLOGUE"
            return

        # 2. Starting Lore Prologue Clicks
        if self.active_modal == "LORE_PROLOGUE":
            if pygame.Rect(400, 710, 560, 56).collidepoint(mx, my):
                self.has_seen_prologue = True
                self.active_modal = None
                p = self.world.get_player()
                self.show_toast(f"5:00 PM: Playing as {p.name}. Walk with [WASD/Arrows] & press [E] to investigate!")
                return
            if pygame.Rect(120, 710, 240, 56).collidepoint(mx, my):
                self.active_modal = "FAMILY_SELECT"
                return
            return

        # 3. Bottom RPG Dialogue Box Clicks
        if self.active_modal == "DIALOGUE" and self.talking_npc:
            for idx in range(len(self.npc_options)):
                if pygame.Rect(245, 686 + idx * 34, 820, 30).collidepoint(mx, my):
                    self._select_dialogue_choice_in_box(idx)
                    return
            if pygame.Rect(1085, 686, 195, 64).collidepoint(mx, my):
                msg = self.world.trigger_deja_vu_on_npc(self.talking_npc)
                if self.talking_npc.speech_bubble:
                    self.npc_greeting = self.talking_npc.speech_bubble
                self.typewriter_chars = 0.0
                self.show_toast(msg, duration=6.5)
                return
            if pygame.Rect(1085, 760, 195, 30).collidepoint(mx, my):
                self.typing_custom = True
                self.custom_input = ""
                return
            if pygame.Rect(1085, 796, 195, 32).collidepoint(mx, my):
                self.active_modal = None
                return
            return

        # 4. Case File Notebook Close Click
        if self.active_modal == "NOTEBOOK":
            if not pygame.Rect(200, 110, 960, 620).collidepoint(mx, my):
                self.active_modal = None
            return

        # 5. Top Bar Buttons
        if my <= 58:
            if pygame.Rect(985, 10, 175, 38).collidepoint(mx, my):
                self.active_modal = "NOTEBOOK"
            elif pygame.Rect(1170, 10, 175, 38).collidepoint(mx, my):
                self.active_modal = "FAMILY_SELECT"
            return

        # 6. Click on a nearby person in the world
        if self.active_modal is None:
            wx = mx + self.cam_x
            wy = my + self.cam_y
            player = self.world.get_player()
            for char in self.world.characters.values():
                if not char.is_player and not char.arrested and math.hypot(wx - char.x, wy - (char.y - 20)) <= 45.0:
                    if math.hypot(player.x - char.x, player.y - char.y) <= 135.0:
                        self.open_dialogue_with(char)
                    else:
                        self.show_toast(f"Walk closer to {char.name} to talk!")
                    return

    # =========================================================================
    # CLEAN, UNCLUTTERED RENDERING PIPELINE (NO SPOILER ARROWS!)
    # =========================================================================
    def _render(self):
        self.screen.fill(COLORS["grass"])

        # 1. Draw Town Environment, Crosswalks, Vehicles, Buildings & 24 Y-Sorted Characters
        self._render_world()

        # 2. Draw Top Detective & Clock Bar
        self._render_top_bar()

        # 3. Draw Toast Message (when no dialogue modal is open)
        if self.toast_timer > 0 and self.toast_msg and self.active_modal is None:
            self._render_toast()

        # 4. Draw Active Modal
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
        cx = self.cam_x
        cy = self.cam_y
        t_sec = pygame.time.get_ticks() / 1000.0

        # A. Sidewalks & Asphalt Roads (IsoCity Grid Layout)
        pygame.draw.rect(self.screen, COLORS["sidewalk"], pygame.Rect(int(-cx), int(755 - cy), WORLD_WIDTH, 250))
        pygame.draw.rect(self.screen, COLORS["sidewalk"], pygame.Rect(int(790 - cx), int(-cy), 160, WORLD_HEIGHT))
        pygame.draw.rect(self.screen, COLORS["sidewalk"], pygame.Rect(int(1630 - cx), int(-cy), 160, WORLD_HEIGHT))

        pygame.draw.rect(self.screen, COLORS["road"], pygame.Rect(int(-cx), int(805 - cy), WORLD_WIDTH, 150))
        pygame.draw.rect(self.screen, COLORS["road"], pygame.Rect(int(825 - cx), int(-cy), 90, WORLD_HEIGHT))
        pygame.draw.rect(self.screen, COLORS["road"], pygame.Rect(int(1665 - cx), int(-cy), 90, WORLD_HEIGHT))

        # Center dashed road divider line
        for rx in range(60, WORLD_WIDTH, 100):
            pygame.draw.rect(
                self.screen, COLORS["road_line"], pygame.Rect(int(rx - cx), int(877 - cy), 48, 6), border_radius=2
            )

        # Pedestrian Crosswalks aligned with Building Entrances (x=450, 1290, 2140)
        for cw_x in (450, 1290, 2140):
            for stripe_y in range(814, 948, 22):
                stripe_rect = pygame.Rect(int(cw_x - 36 - cx), int(stripe_y - cy), 72, 12)
                pygame.draw.rect(self.screen, (232, 232, 228), stripe_rect, border_radius=2)

        # B. Draw the 6 Neighborhood Buildings with Wide Open Doorways
        for b in BUILDINGS:
            rx, ry, rw, rh = b["rect"]
            b_rect = pygame.Rect(int(rx - cx), int(ry - cy), int(rw), int(rh))

            # Shadow & Floor
            pygame.draw.rect(self.screen, (42, 78, 48), b_rect.move(8, 8), border_radius=12)
            pygame.draw.rect(self.screen, b["floor_color"], b_rect, border_radius=12)

            # Roof Header Banner with Clean Building Name
            roof_rect = pygame.Rect(int(rx - cx), int(ry - cy), int(rw), 42)
            pygame.draw.rect(
                self.screen, b["roof_color"], roof_rect, border_top_left_radius=12, border_top_right_radius=12
            )
            pygame.draw.rect(self.screen, (32, 36, 46), b_rect, 4, border_radius=12)

            # Wide 5-Tile Open Doorway Threshold (128px wide opening so walking in/out is effortless!)
            door_gap = pygame.Rect(int(b["door_x"] - 64 - cx), int(b["door_y"] - 14 - cy), 128, 28)
            pygame.draw.rect(self.screen, b["floor_color"], door_gap, border_radius=4)
            door_mat = pygame.Rect(int(b["door_x"] - 48 - cx), int(b["door_y"] - 10 - cy), 96, 20)
            pygame.draw.rect(self.screen, COLORS["gold"], door_mat, border_radius=4)
            pygame.draw.rect(self.screen, (40, 35, 20), door_mat, 2, border_radius=4)

            b_lbl = self.font_md.render(b["name"], True, COLORS["white"])
            self.screen.blit(b_lbl, (b_rect.centerx - b_lbl.get_width() // 2, int(ry - cy + 10)))

            # Furniture inside Building
            for f in b["furniture"]:
                fx, fy, fw, fh = f["rect"]
                f_rect = pygame.Rect(int(fx - cx), int(fy - cy), int(fw), int(fh))
                pygame.draw.rect(self.screen, f["color"], f_rect, border_radius=7)
                pygame.draw.rect(self.screen, (35, 40, 50), f_rect, 2, border_radius=7)
                flbl = self.font_xs.render(f["name"], True, COLORS["white"])
                self.screen.blit(
                    flbl, (f_rect.centerx - flbl.get_width() // 2, f_rect.centery - flbl.get_height() // 2)
                )

        # C. Draw Trees
        for tx, ty in self.trees:
            sx, sy = int(tx - cx), int(ty - cy)
            pygame.draw.circle(self.screen, (38, 72, 44), (sx + 4, sy + 6), 26)
            pygame.draw.circle(self.screen, (52, 132, 66), (sx, sy), 25)
            pygame.draw.circle(self.screen, (82, 168, 88), (sx - 6, sy - 6), 15)

        # D. Draw Interactive Cross-Zone Terminals
        for oid, wobj in self.world.objects.items():
            ox, oy = int(wobj["x"] - cx), int(wobj["y"] - cy)
            pulse = int(math.sin(t_sec * 4.0) * 2)
            pygame.draw.circle(self.screen, (25, 30, 42), (ox, oy), 16 + pulse)
            pygame.draw.circle(self.screen, wobj["color"], (ox, oy), 16 + pulse, 3)
            pygame.draw.circle(self.screen, wobj["color"], (ox, oy), 7)

        # E. Draw Moving Street Vehicles (IsoCity Traffic)
        for veh in self.world.grid_engine.vehicles:
            veh.draw(self.screen, cx, cy)

        # F. Particles
        self.world.particles.update_and_draw(self.screen, cx, cy, 1.0 / FPS)

        # G. YSort Depth-Sorted Characters (No spoiler quest markers!)
        player = self.world.get_player()
        nearest_kind, nearest_target = self.world.get_nearest_interactable(max_dist=108.0)
        sorted_chars = sorted([c for c in self.world.characters.values() if not c.arrested], key=lambda c: c.y)

        for char in sorted_chars:
            has_anchor = char.memory_store.has_anchored_memory()
            has_grudge = player.id in char.grudges

            char.rig.draw(
                surface=self.screen,
                wx=char.x,
                wy=char.y,
                cam_x=cx,
                cam_y=cy,
                is_player=char.is_player,
                has_quest_marker=None,  # No spoiler markers!
                has_memory_anchor=has_anchor,
            )

            sx, sy = int(char.x - cx), int(char.y - cy)
            short_n = char.name.split("(")[0].strip()
            if char.is_player:
                short_n = f"YOU: {short_n}"
            elif char.is_family:
                short_n = f"[FAMILY] {short_n}"

            ncol = (
                COLORS["cyan"]
                if char.is_player
                else (COLORS["red"] if has_grudge else (COLORS["gold"] if char.is_family else COLORS["white"]))
            )
            nlbl = self.font_xs.render(short_n, True, ncol)
            npill = pygame.Rect(sx - nlbl.get_width() // 2 - 5, sy + 6, nlbl.get_width() + 10, 18)
            pygame.draw.rect(self.screen, (18, 22, 32), npill, border_radius=4)
            self.screen.blit(nlbl, (sx - nlbl.get_width() // 2, sy + 8))

            if char.speech_bubble and self.active_modal != "DIALOGUE":
                self._draw_small_bubble(sx, sy - 64, char.speech_bubble)

        # H. Single Crisp "[E] Talk / Inspect" Prompt on the Closest Interactable
        if nearest_target is not None and self.active_modal is None:
            if nearest_kind == "npc":
                tx_p, ty_p = int(nearest_target.x - cx), int(nearest_target.y - cy - 58)
                ptxt = f"Press [E] to Talk to {nearest_target.name}"
            else:
                tx_p, ty_p = int(nearest_target["x"] - cx), int(nearest_target["y"] - cy - 36)
                ptxt = f"Press [E] to Use {nearest_target['name']}"
            psurf = self.font_sm.render(ptxt, True, COLORS["gold"])
            ppill = pygame.Rect(tx_p - psurf.get_width() // 2 - 10, ty_p - 6, psurf.get_width() + 20, 28)
            pygame.draw.rect(self.screen, (16, 20, 30), ppill, border_radius=6)
            pygame.draw.rect(self.screen, COLORS["gold"], ppill, 2, border_radius=6)
            self.screen.blit(psurf, (tx_p - psurf.get_width() // 2, ty_p - 1))

    def _draw_small_bubble(self, x: int, y: int, text: str):
        short = text[:52] + ("..." if len(text) > 52 else "")
        surf = self.font_xs.render(short, True, COLORS["white"])
        w = surf.get_width() + 14
        rect = pygame.Rect(x - w // 2, y - 22, w, 24)
        pygame.draw.rect(self.screen, (20, 25, 38), rect, border_radius=6)
        pygame.draw.rect(self.screen, COLORS["ui_border_soft"], rect, 1, border_radius=6)
        self.screen.blit(surf, (x - surf.get_width() // 2, y - 18))

    def _render_top_bar(self):
        bar = pygame.Rect(0, 0, SCREEN_WIDTH, 58)
        pygame.draw.rect(self.screen, COLORS["ui_panel"], bar)
        pygame.draw.line(self.screen, COLORS["ui_border"], (0, 57), (SCREEN_WIDTH, 57), 2)

        p = self.world.get_player()
        loc_name = self.world.get_building_name_at(p.x, p.y)
        obj_info = self.world.get_current_objective()

        top_line = f"{obj_info['chapter_title']}   |   LOCATION: {loc_name}   |   [1-4] SWITCH FAMILY"
        ch_lbl = self.font_xs.render(top_line, True, COLORS["cyan"])
        self.screen.blit(ch_lbl, (16, 8))

        inst_lbl = self.font_sm.render(obj_info["instruction"], True, COLORS["gold"])
        self.screen.blit(inst_lbl, (16, 29))

        # In-Game Clock (5:00 PM -> 6:00 PM) + Loop Counter
        rem = int(self.world.time_remaining)
        clock_str = self.world.get_clock_string()
        t_col = COLORS["red"] if rem < 45 else COLORS["white"]
        t_lbl = self.font_lg.render(f"{clock_str}  (Loop #{self.world.loop_id})", True, t_col)
        self.screen.blit(t_lbl, (775, 16))

        # [N] Case File Button
        n_btn = pygame.Rect(985, 10, 175, 38)
        pygame.draw.rect(self.screen, COLORS["ui_card"], n_btn, border_radius=6)
        pygame.draw.rect(self.screen, COLORS["cyan"], n_btn, 2, border_radius=6)
        nlbl = self.font_xs.render(f"[N] CASE FILE ({len(self.world.notebook_clues)})", True, COLORS["cyan"])
        self.screen.blit(nlbl, (n_btn.centerx - nlbl.get_width() // 2, n_btn.centery - nlbl.get_height() // 2))

        # [F] Family & Lore Button
        f_btn = pygame.Rect(1170, 10, 175, 38)
        pygame.draw.rect(self.screen, COLORS["ui_card"], f_btn, border_radius=6)
        pygame.draw.rect(self.screen, COLORS["gold"], f_btn, 2, border_radius=6)
        flbl = self.font_xs.render("[F] FAMILY & LORE", True, COLORS["gold"])
        self.screen.blit(flbl, (f_btn.centerx - flbl.get_width() // 2, f_btn.centery - flbl.get_height() // 2))

    def _render_toast(self):
        surf = self.font_md.render(self.toast_msg, True, COLORS["white"])
        w = min(SCREEN_WIDTH - 40, surf.get_width() + 36)
        rect = pygame.Rect((SCREEN_WIDTH - w) // 2, SCREEN_HEIGHT - 62, w, 44)
        pygame.draw.rect(self.screen, COLORS["ui_dark"], rect, border_radius=8)
        pygame.draw.rect(self.screen, COLORS["gold"], rect, 2, border_radius=8)
        self.screen.blit(surf, (rect.x + 18, rect.y + 11))

    def _render_bottom_dialogue_box(self):
        """
        OpenPixel-RPG & IslandEscape Bottom Dialogue Window:
        - Framed 135x135 Character Bust Portrait on the Left
        - Relationship / Grudge Status Badge & Rapport % with current family member
        - Character Name, Role & Current 5:00 PM - 6:00 PM Schedule
        - Typewriter-revealed Dialogue Text
        - 4 Unspoiled Investigative Questions + Deja-Vu Memory Pulse [R]
        """
        npc = self.talking_npc
        if not npc:
            return

        player = self.world.get_player()
        fam_id = player.id

        box = pygame.Rect(50, 535, 1260, 305)
        pygame.draw.rect(self.screen, (18, 22, 34), box, border_radius=12)
        pygame.draw.rect(self.screen, COLORS["ui_border"], box, 3, border_radius=12)

        # 1. Framed Character Bust Portrait on the Left
        p_rect = pygame.Rect(75, 558, 135, 135)
        t_phase = pygame.time.get_ticks() / 1000.0
        is_typing = self.typewriter_chars < len(self.npc_greeting)
        draw_character_portrait(self.screen, p_rect, npc.spec, anim_phase=(t_phase if is_typing else 0.0))

        # Relationship Status Badge under Portrait (IslandEscape Grudge/Rapport system)
        rel_status = npc.get_relationship_status(fam_id)
        rel_col = (
            COLORS["red"]
            if "GRUDGE" in rel_status
            else (COLORS["gold"] if npc.is_family else (COLORS["green"] if "ALLY" in rel_status else COLORS["cyan"]))
        )
        r_tag = self.font_xs.render(rel_status, True, rel_col)
        self.screen.blit(r_tag, (p_rect.centerx - r_tag.get_width() // 2, 702))

        rapport_val = npc.get_rapport(fam_id)
        trust_tag = self.font_xs.render(f"Rapport: {rapport_val}%", True, COLORS["white"])
        self.screen.blit(trust_tag, (p_rect.centerx - trust_tag.get_width() // 2, 722))

        if self.world.has_warm_coffee:
            c_tag = self.font_xs.render("Holding Espresso", True, COLORS["gold"])
            self.screen.blit(c_tag, (p_rect.centerx - c_tag.get_width() // 2, 742))

        # 2. Character Name, Role, Schedule & Typewriter Spoken Text
        x_text = 235
        name_hdr = self.font_lg.render(f"{npc.name}  —  {npc.role}", True, COLORS["gold"])
        self.screen.blit(name_hdr, (x_text, 550))

        sched_hdr = self.font_xs.render(
            f"Schedule ({self.world.get_clock_string()}): {npc.current_schedule_label}   |   Speaking with: {player.name}",
            True,
            COLORS["cyan"],
        )
        self.screen.blit(sched_hdr, (x_text, 578))

        visible_text = self.npc_greeting[: int(self.typewriter_chars)]
        words = visible_text.split()
        lines, curr = [], ""
        for w in words:
            if len(curr) + len(w) + 1 <= 88:
                curr = f"{curr} {w}".strip()
            else:
                lines.append(curr)
                curr = w
        if curr:
            lines.append(curr)

        for idx, ln in enumerate(lines[:3]):
            self.screen.blit(self.font_md.render(ln, True, COLORS["white"]), (x_text, 604 + idx * 24))

        # 3. 4 Unspoiled Player Investigative Questions
        if self.typing_custom:
            inp_box = pygame.Rect(x_text, 700, 825, 46)
            pygame.draw.rect(self.screen, (12, 15, 22), inp_box, border_radius=6)
            pygame.draw.rect(self.screen, COLORS["green"], inp_box, 2, border_radius=6)
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
                bg = (54, 32, 38) if is_accuse else (30, 38, 56)
                bdr = COLORS["gold"] if is_accuse else COLORS["cyan"]
                pygame.draw.rect(self.screen, bg, btn, border_radius=6)
                pygame.draw.rect(self.screen, bdr, btn, 1, border_radius=6)
                self.screen.blit(
                    self.font_sm.render(f"[{idx + 1}] {opt_txt}", True, COLORS["white"]),
                    (x_text + 12, 691 + idx * 34),
                )

        # 4. Right-Side Action Buttons ([R] Deja-Vu, [T] Ask AI, [ESC] Close)
        r_btn = pygame.Rect(1085, 686, 200, 64)
        pygame.draw.rect(self.screen, (28, 62, 52), r_btn, border_radius=8)
        pygame.draw.rect(self.screen, COLORS["green"], r_btn, 2, border_radius=8)
        self.screen.blit(self.font_xs.render("[R] DEJA-VU PULSE", True, COLORS["green"]), (1112, 698))
        self.screen.blit(
            self.font_xs.render(f"({self.world.deja_vu_charges} Charges Left)", True, COLORS["white"]),
            (1118, 720),
        )

        t_btn = pygame.Rect(1085, 758, 200, 30)
        pygame.draw.rect(self.screen, (32, 44, 68), t_btn, border_radius=6)
        pygame.draw.rect(self.screen, COLORS["cyan"], t_btn, 1, border_radius=6)
        self.screen.blit(self.font_xs.render("[T] Type Custom Question", True, COLORS["cyan"]), (1098, 765))

        c_btn = pygame.Rect(1085, 794, 200, 32)
        pygame.draw.rect(self.screen, (52, 34, 42), c_btn, border_radius=6)
        pygame.draw.rect(self.screen, COLORS["red"], c_btn, 1, border_radius=6)
        self.screen.blit(self.font_xs.render("[ESC / E] End Conversation", True, COLORS["white"]), (1096, 802))

    def _render_family_select_modal(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((10, 14, 22, 236))
        self.screen.blit(overlay, (0, 0))

        panel = pygame.Rect(80, 50, 1200, 750)
        pygame.draw.rect(self.screen, COLORS["ui_panel"], panel, border_radius=14)
        pygame.draw.rect(self.screen, COLORS["gold"], panel, 3, border_radius=14)

        t_surf = self.font_xl.render("MAPLEWOOD LOOP // CHOOSE YOUR MERCER FAMILY MEMBER", True, COLORS["gold"])
        self.screen.blit(t_surf, (panel.centerx - t_surf.get_width() // 2, 74))

        rules = [
            "5:00 PM TO 6:00 PM TIME LOOP: Someone in town is sabotaging the Aether-Core Generator at 6:00 PM sharp!",
            "DYNAMIC WORLD & SCHEDULES: Watch 20 townspeople commute across buildings, cross-check ledgers, and avoid false accusations!",
            "TINY-LIFE HOUSEHOLD SWITCHING: Switch between Dad [1], Mom [2], Maya [3], and Leo [4] at any time during the loop!",
        ]
        for idx, r_line in enumerate(rules):
            col = COLORS["cyan"] if idx == 2 else COLORS["white"]
            self.screen.blit(self.font_sm.render(r_line, True, col), (118, 128 + idx * 28))

        family_ids = ["arthur", "elena", "maya", "leo"]
        t_phase = pygame.time.get_ticks() / 1000.0
        for idx, fid in enumerate(family_ids):
            char = self.world.characters[fid]
            cx = 110 + idx * 290
            cy = 245
            c_rect = pygame.Rect(cx, cy, 270, 405)
            is_sel = self.world.player_char_id == fid

            pygame.draw.rect(self.screen, (42, 54, 80) if is_sel else COLORS["ui_card"], c_rect, border_radius=10)
            pygame.draw.rect(
                self.screen,
                COLORS["gold"] if is_sel else COLORS["ui_border_soft"],
                c_rect,
                3 if is_sel else 2,
                border_radius=10,
            )

            k_lbl = self.font_md.render(
                f"PRESS [{idx + 1}] OR CLICK", True, COLORS["gold"] if is_sel else COLORS["cyan"]
            )
            self.screen.blit(k_lbl, (c_rect.centerx - k_lbl.get_width() // 2, cy + 14))

            port_rect = pygame.Rect(cx + 68, cy + 48, 134, 134)
            draw_character_portrait(self.screen, port_rect, char.spec, anim_phase=(t_phase if is_sel else 0.0))

            n_lbl = self.font_md.render(char.name, True, COLORS["white"])
            self.screen.blit(n_lbl, (c_rect.centerx - n_lbl.get_width() // 2, cy + 196))

            r_lbl = self.font_xs.render(char.role, True, COLORS["cyan"])
            self.screen.blit(r_lbl, (c_rect.centerx - r_lbl.get_width() // 2, cy + 222))

            words = char.perk.split()
            lines, cur = [], ""
            for w in words:
                if len(cur) + len(w) + 1 <= 32:
                    cur = f"{cur} {w}".strip()
                else:
                    lines.append(cur)
                    cur = w
            if cur:
                lines.append(cur)
            for l_i, ln in enumerate(lines[:3]):
                self.screen.blit(self.font_xs.render(ln, True, COLORS["text_dim"]), (cx + 16, cy + 256 + l_i * 20))

            loc_now = self.world.get_building_name_at(char.x, char.y)
            self.screen.blit(self.font_xs.render(f"Location: {loc_now[:22]}", True, COLORS["green"]), (cx + 16, cy + 355))

        start_btn = pygame.Rect(400, 685, 560, 56)
        pygame.draw.rect(self.screen, (35, 125, 78), start_btn, border_radius=10)
        pygame.draw.rect(self.screen, COLORS["green"], start_btn, 2, border_radius=10)
        st_lbl = self.font_md.render(
            f"CONTINUE TO STARTING LORE AS {self.world.get_player().name.upper()} [SPACE]",
            True,
            COLORS["white"],
        )
        self.screen.blit(
            st_lbl, (start_btn.centerx - st_lbl.get_width() // 2, start_btn.centery - st_lbl.get_height() // 2)
        )

    def _render_lore_prologue_modal(self):
        """
        Displays the atmospheric Starting Lore of Maplewood Heights + the chosen family member's
        personal perspective right after character selection!
        """
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((8, 12, 20, 242))
        self.screen.blit(overlay, (0, 0))

        panel = pygame.Rect(90, 48, 1180, 760)
        pygame.draw.rect(self.screen, (20, 26, 38), panel, border_radius=14)
        pygame.draw.rect(self.screen, COLORS["gold"], panel, 3, border_radius=14)

        p = self.world.get_player()
        lore_data = FAMILY_LORE_PROLOGUES.get(p.id, FAMILY_LORE_PROLOGUES["arthur"])

        # Header
        hdr = self.font_xl.render("PROLOGUE // THE 6:00 PM AETHER-CORE ANOMALY", True, COLORS["gold"])
        self.screen.blit(hdr, (panel.centerx - hdr.get_width() // 2, 72))

        # Section 1: Town Lore Box
        town_box = pygame.Rect(125, 122, 1110, 275)
        pygame.draw.rect(self.screen, (28, 35, 50), town_box, border_radius=10)
        pygame.draw.rect(self.screen, COLORS["ui_border_soft"], town_box, 2, border_radius=10)

        for idx, line in enumerate(TOWN_LORE_PROLOGUE):
            col = COLORS["cyan"] if idx == 0 else COLORS["white"]
            font_use = self.font_md if idx == 0 else self.font_sm
            self.screen.blit(font_use.render(line, True, col), (148, 136 + idx * 20))

        # Section 2: Selected Character's Personal Prologue & Specialty
        char_box = pygame.Rect(125, 415, 1110, 265)
        pygame.draw.rect(self.screen, (32, 42, 62), char_box, border_radius=10)
        pygame.draw.rect(self.screen, COLORS["gold"], char_box, 2, border_radius=10)

        t_phase = pygame.time.get_ticks() / 1000.0
        port_rect = pygame.Rect(150, 442, 155, 155)
        draw_character_portrait(self.screen, port_rect, p.spec, anim_phase=t_phase)

        c_hdr = self.font_lg.render(lore_data["headline"], True, COLORS["gold"])
        self.screen.blit(c_hdr, (330, 435))

        # Wrap personal story text
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
            self.screen.blit(self.font_md.render(ln, True, COLORS["white"]), (330, 474 + idx * 26))

        spec_lbl = self.font_sm.render(f"UNIQUE ADVANTAGE: {lore_data['specialty']}", True, COLORS["green"])
        self.screen.blit(spec_lbl, (330, 610))

        tip_lbl = self.font_xs.render(
            "DETECTIVE TIP: There are no hand-holding arrows! Observe NPC schedules (5:00-6:00 PM), cross-check terminals, and press [N] for your Case File.",
            True,
            COLORS["cyan"],
        )
        self.screen.blit(tip_lbl, (150, 646))

        # Bottom Buttons
        back_btn = pygame.Rect(125, 708, 245, 56)
        pygame.draw.rect(self.screen, COLORS["ui_card"], back_btn, border_radius=10)
        pygame.draw.rect(self.screen, COLORS["cyan"], back_btn, 2, border_radius=10)
        b_lbl = self.font_sm.render("[F] CHANGE CHARACTER", True, COLORS["cyan"])
        self.screen.blit(b_lbl, (back_btn.centerx - b_lbl.get_width() // 2, back_btn.centery - b_lbl.get_height() // 2))

        enter_btn = pygame.Rect(400, 708, 560, 56)
        pygame.draw.rect(self.screen, (35, 125, 78), enter_btn, border_radius=10)
        pygame.draw.rect(self.screen, COLORS["green"], enter_btn, 2, border_radius=10)
        e_lbl = self.font_md.render("ENTER MAPLEWOOD HEIGHTS AT 5:00 PM [PRESS SPACE]", True, COLORS["white"])
        self.screen.blit(
            e_lbl, (enter_btn.centerx - e_lbl.get_width() // 2, enter_btn.centery - e_lbl.get_height() // 2)
        )

    def _render_notebook_modal(self):
        rect = pygame.Rect(200, 110, 960, 620)
        pygame.draw.rect(self.screen, COLORS["ui_panel"], rect, border_radius=12)
        pygame.draw.rect(self.screen, COLORS["cyan"], rect, 3, border_radius=12)

        x0, y0 = rect.x + 28, rect.y + 24
        self.screen.blit(
            self.font_xl.render("MERCER FAMILY DETECTIVE CASE FILE & CROSS-ZONE STATUS", True, COLORS["gold"]),
            (x0, y0),
        )
        y0 += 44

        obj_info = self.world.get_current_objective()
        self.screen.blit(self.font_md.render(obj_info["chapter_title"], True, COLORS["cyan"]), (x0, y0))
        y0 += 26
        self.screen.blit(self.font_sm.render(obj_info["instruction"], True, COLORS["green"]), (x0, y0))
        y0 += 36

        # Cross-Zone System Checklist (Unknown Horizons persistence)
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
        self.screen.blit(self.font_md.render("Cross-Zone Investigation Checklist:", True, COLORS["gold"]), (x0, y0))
        y0 += 26
        for idx, (label, done) in enumerate(checks):
            col = COLORS["green"] if done else COLORS["text_muted"]
            mark = "[DONE]" if done else "[PENDING]"
            cx_pos = x0 + (idx % 2) * 450
            cy_pos = y0 + (idx // 2) * 24
            self.screen.blit(self.font_xs.render(f"{mark} {label}", True, col), (cx_pos, cy_pos))
        y0 += 108

        self.screen.blit(self.font_md.render("Clues & Evidence Recorded Across Loops:", True, COLORS["gold"]), (x0, y0))
        y0 += 28
        for clue in self.world.notebook_clues[-9:]:
            self.screen.blit(self.font_sm.render(f"- {clue}", True, COLORS["white"]), (x0 + 8, y0))
            y0 += 25

        self.screen.blit(
            self.font_xs.render(
                "Press [N] or [ESC] to Close Case File   |   Press [L] to Re-Read Starting Lore",
                True,
                COLORS["text_dim"],
            ),
            (x0, rect.bottom - 34),
        )

    def _render_api_config_modal(self):
        rect = pygame.Rect(310, 240, 740, 250)
        pygame.draw.rect(self.screen, COLORS["ui_panel"], rect, border_radius=12)
        pygame.draw.rect(self.screen, COLORS["gold"], rect, 2, border_radius=12)
        x0, y0 = rect.x + 24, rect.y + 24
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
        pygame.draw.rect(self.screen, COLORS["ui_panel"], rect, border_radius=14)
        pygame.draw.rect(self.screen, col, rect, 3, border_radius=14)

        x0, y0 = rect.x + 32, rect.y + 28
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
