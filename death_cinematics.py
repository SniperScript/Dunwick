"""
death_cinematics.py
Cinematic Visual Death & Temporal Rewind Engine for CHRONICLES OF DUNWICK: DEFYING FATE (1924)
Provides explicit, high-impact death cutscenes:
1. CARRIAGE_CRASH / STEAM_LORRY: Roaring runaway steam-lorry, screeching iron brakes, shattering impact, debris.
2. ASSASSINATION_POISON: Toxic aconite mist, whistling dart / venom strike, coughing convulsions, necrotic vignette.
3. FOOD_CHOKING: Dropped porcelain plate shattering, gasping/clutching throat, asphyxiation tunnel-vision.
4. GARGOYLE_COLLAPSE: Growing ground shadow, crumbling mortar, plunging 300-lb Norman stone gargoyle.
5. GALVANIC_ARC: High-voltage crackling lightning bolt, blinding strobes, expanding electric shockwaves.
Followed by the TEMPORAL REWIND sequence (spinning clock hands, rewind vortex, memory journal inscription).
"""

import math
import os
import random
import pygame

from config import COLORS, SCREEN_HEIGHT, SCREEN_WIDTH


class DeathDebris:
    def __init__(self, x: float, y: float, vx: float, vy: float, color: tuple, size: float, shape: str = "rect"):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.size = size
        self.shape = shape  # "rect", "circle", "shard", "smoke"
        self.life = random.uniform(1.2, 2.5)
        self.max_life = self.life
        self.angle = random.uniform(0, 360)
        self.rot_speed = random.uniform(-360, 360)
        self.gravity = 420.0

    def update(self, dt: float):
        self.life -= dt
        self.vx *= 0.96
        self.vy += self.gravity * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.angle += self.rot_speed * dt

    def draw(self, surface: pygame.Surface):
        if self.life <= 0:
            return
        ratio = max(0.1, self.life / self.max_life)
        alpha = int(255 * ratio)
        col = (*self.color[:3], alpha)

        s = int(self.size * ratio)
        if s <= 1:
            return

        if self.shape == "shard":
            # Glass / porcelain / stone triangle shard
            shard_surf = pygame.Surface((s * 3, s * 3), pygame.SRCALPHA)
            pts = [(s, 0), (s * 2, s * 2), (0, s * 2)]
            pygame.draw.polygon(shard_surf, col, pts)
            rot = pygame.transform.rotate(shard_surf, self.angle)
            surface.blit(rot, (int(self.x - rot.get_width() // 2), int(self.y - rot.get_height() // 2)))
        elif self.shape == "smoke":
            sm_surf = pygame.Surface((s * 4, s * 4), pygame.SRCALPHA)
            pygame.draw.circle(sm_surf, (*self.color[:3], int(alpha * 0.45)), (s * 2, s * 2), s * 2)
            surface.blit(sm_surf, (int(self.x - s * 2), int(self.y - s * 2)))
        else:
            r_surf = pygame.Surface((s * 2, s * 2), pygame.SRCALPHA)
            pygame.draw.rect(r_surf, col, (0, 0, s * 2, s))
            rot = pygame.transform.rotate(r_surf, self.angle)
            surface.blit(rot, (int(self.x - rot.get_width() // 2), int(self.y - rot.get_height() // 2)))


class DeathCinematicEngine:
    """
    Manages active death cutscenes and temporal rewinds.
    """

    def __init__(self):
        self.is_active = False
        self.death_type: str = "CARRIAGE_CRASH"
        self.day_name: str = "Monday"
        self.day_num: int = 1
        self.loop_id: int = 1
        self.player_name: str = "Lord Arthur"
        self.timer: float = 0.0
        self.total_duration: float = 4.8

        # Player screen coordinates at time of death
        self.player_sx: float = SCREEN_WIDTH * 0.5
        self.player_sy: float = SCREEN_HEIGHT * 0.5

        # Visual FX containers
        self.debris: list[DeathDebris] = []
        self.shake_mag: float = 0.0
        self.shake_offset: tuple[float, float] = (0.0, 0.0)
        self.impact_occurred: bool = False

        # Fonts
        self.font_title = pygame.font.SysFont("Georgia, Times, serif", 34, bold=True)
        self.font_subtitle = pygame.font.SysFont("Georgia, Times, serif", 22, bold=True)
        self.font_body = pygame.font.SysFont("DejaVu Sans, Arial, sans-serif", 16)
        self.font_clock = pygame.font.SysFont("Georgia, Times, serif", 48, bold=True)

        # Lorry / projectile animation coords
        self.hazard_actor_x: float = -200.0
        self.hazard_actor_y: float = 0.0

        # Finished callback
        self.on_rewind_complete = None

    def trigger_death(
        self,
        death_type: str,
        day_num: int,
        day_name: str,
        loop_id: int,
        player_name: str,
        player_screen_pos: tuple[float, float],
        on_complete_callback=None,
    ):
        """Starts a visual cinematic death sequence."""
        self.is_active = True
        self.death_type = death_type
        self.day_num = day_num
        self.day_name = day_name
        self.loop_id = loop_id
        self.player_name = player_name
        self.player_sx, self.player_sy = player_screen_pos
        self.on_rewind_complete = on_complete_callback
        self.timer = 0.0
        self.impact_occurred = False
        self.debris.clear()
        self.shake_mag = 0.0

        # Setup hazard initial position
        if death_type in ("CARRIAGE_CRASH", "CAR_CRASH"):
            self.hazard_actor_x = -260.0
            self.hazard_actor_y = self.player_sy
        elif death_type in ("GARGOYLE_COLLAPSE", "COLLAPSE"):
            self.hazard_actor_x = self.player_sx
            self.hazard_actor_y = -180.0
        elif death_type in ("ASSASSINATION_POISON", "ASSASSINATION"):
            self.hazard_actor_x = SCREEN_WIDTH + 100.0
            self.hazard_actor_y = self.player_sy - 30.0

    def update(self, dt: float):
        if not self.is_active:
            return

        self.timer += dt

        # Screen shake dampening
        if self.shake_mag > 0.05:
            self.shake_offset = (
                random.uniform(-self.shake_mag, self.shake_mag),
                random.uniform(-self.shake_mag, self.shake_mag),
            )
            self.shake_mag *= 0.91
        else:
            self.shake_offset = (0.0, 0.0)

        # Update debris
        for d in self.debris:
            d.update(dt)
        self.debris = [d for d in self.debris if d.life > 0]

        # Stage 1: Hazard trajectory & impact (0.0s to 1.6s)
        if self.timer < 1.6:
            progress = min(1.0, self.timer / 1.0)
            if self.death_type in ("CARRIAGE_CRASH", "CAR_CRASH"):
                self.hazard_actor_x = -260.0 + progress * (self.player_sx - (-260.0))
                if progress >= 0.95 and not self.impact_occurred:
                    self._create_lorry_impact()
            elif self.death_type in ("GARGOYLE_COLLAPSE", "COLLAPSE"):
                # Accelerating fall
                fall_p = (self.timer / 1.1) ** 2
                self.hazard_actor_y = -180.0 + fall_p * (self.player_sy - (-180.0))
                if fall_p >= 0.95 and not self.impact_occurred:
                    self._create_gargoyle_impact()
            elif self.death_type in ("ASSASSINATION_POISON", "ASSASSINATION"):
                self.hazard_actor_x = (SCREEN_WIDTH + 100.0) - progress * ((SCREEN_WIDTH + 100.0) - self.player_sx)
                if progress >= 0.95 and not self.impact_occurred:
                    self._create_assassin_impact()
            elif self.death_type in ("FOOD_CHOKING", "CHOKING"):
                if self.timer > 0.4 and not self.impact_occurred:
                    self._create_choking_impact()
            elif self.death_type in ("GALVANIC_ARC", "ELECTROCUTION"):
                if self.timer > 0.4 and not self.impact_occurred:
                    self._create_galvanic_impact()
            elif not self.impact_occurred:
                self._create_generic_impact()

        # Check completion
        if self.timer >= self.total_duration:
            self.is_active = False
            if self.on_rewind_complete:
                self.on_rewind_complete()

    def _create_lorry_impact(self):
        self.impact_occurred = True
        self.shake_mag = 24.0
        # Glass shards, wooden splinters, sparks, steam
        for _ in range(35):
            ang = random.uniform(0, math.tau)
            spd = random.uniform(140.0, 480.0)
            self.debris.append(
                DeathDebris(
                    self.player_sx,
                    self.player_sy,
                    math.cos(ang) * spd,
                    math.sin(ang) * spd,
                    color=(218, 238, 248),
                    size=random.uniform(5.0, 11.0),
                    shape="shard",
                )
            )
        for _ in range(25):
            ang = random.uniform(0, math.tau)
            spd = random.uniform(100.0, 360.0)
            self.debris.append(
                DeathDebris(
                    self.player_sx,
                    self.player_sy,
                    math.cos(ang) * spd,
                    math.sin(ang) * spd,
                    color=(168, 112, 62),
                    size=random.uniform(6.0, 14.0),
                    shape="rect",
                )
            )
        for _ in range(20):
            ang = random.uniform(-math.pi, 0)
            spd = random.uniform(60.0, 220.0)
            self.debris.append(
                DeathDebris(
                    self.player_sx,
                    self.player_sy,
                    math.cos(ang) * spd,
                    math.sin(ang) * spd,
                    color=(240, 235, 225),
                    size=random.uniform(12.0, 26.0),
                    shape="smoke",
                )
            )

    def _create_gargoyle_impact(self):
        self.impact_occurred = True
        self.shake_mag = 28.0
        # Heavy stone rubble blocks and mortar dust
        for _ in range(40):
            ang = random.uniform(0, math.tau)
            spd = random.uniform(110.0, 420.0)
            self.debris.append(
                DeathDebris(
                    self.player_sx,
                    self.player_sy,
                    math.cos(ang) * spd,
                    math.sin(ang) * spd,
                    color=(142, 138, 134),
                    size=random.uniform(8.0, 18.0),
                    shape="shard",
                )
            )
        for _ in range(30):
            ang = random.uniform(-math.pi, 0)
            spd = random.uniform(40.0, 180.0)
            self.debris.append(
                DeathDebris(
                    self.player_sx,
                    self.player_sy,
                    math.cos(ang) * spd,
                    math.sin(ang) * spd,
                    color=(190, 182, 172),
                    size=random.uniform(14.0, 30.0),
                    shape="smoke",
                )
            )

    def _create_assassin_impact(self):
        self.impact_occurred = True
        self.shake_mag = 14.0
        # Toxic violet/crimson droplets and misty plumes
        for _ in range(35):
            ang = random.uniform(0, math.tau)
            spd = random.uniform(80.0, 260.0)
            self.debris.append(
                DeathDebris(
                    self.player_sx,
                    self.player_sy,
                    math.cos(ang) * spd,
                    math.sin(ang) * spd,
                    color=(195, 45, 68),
                    size=random.uniform(4.0, 9.0),
                    shape="circle",
                )
            )
        for _ in range(25):
            ang = random.uniform(0, math.tau)
            spd = random.uniform(30.0, 140.0)
            self.debris.append(
                DeathDebris(
                    self.player_sx,
                    self.player_sy,
                    math.cos(ang) * spd,
                    math.sin(ang) * spd,
                    color=(148, 62, 188),
                    size=random.uniform(10.0, 24.0),
                    shape="smoke",
                )
            )

    def _create_choking_impact(self):
        self.impact_occurred = True
        self.shake_mag = 12.0
        # Porcelain plate shattering + pie crust fragments
        for _ in range(28):
            ang = random.uniform(0, math.tau)
            spd = random.uniform(60.0, 280.0)
            self.debris.append(
                DeathDebris(
                    self.player_sx,
                    self.player_sy + 15,
                    math.cos(ang) * spd,
                    math.sin(ang) * spd,
                    color=(245, 242, 235),
                    size=random.uniform(4.0, 10.0),
                    shape="shard",
                )
            )
        for _ in range(20):
            ang = random.uniform(0, math.tau)
            spd = random.uniform(40.0, 180.0)
            self.debris.append(
                DeathDebris(
                    self.player_sx,
                    self.player_sy + 15,
                    math.cos(ang) * spd,
                    math.sin(ang) * spd,
                    color=(182, 122, 68),
                    size=random.uniform(5.0, 11.0),
                    shape="rect",
                )
            )

    def _create_galvanic_impact(self):
        self.impact_occurred = True
        self.shake_mag = 22.0
        # Electric cyan sparks and expanding arcs
        for _ in range(45):
            ang = random.uniform(0, math.tau)
            spd = random.uniform(160.0, 520.0)
            self.debris.append(
                DeathDebris(
                    self.player_sx,
                    self.player_sy,
                    math.cos(ang) * spd,
                    math.sin(ang) * spd,
                    color=(92, 235, 255),
                    size=random.uniform(3.0, 7.0),
                    shape="shard",
                )
            )

    def _create_generic_impact(self):
        self.impact_occurred = True
        self.shake_mag = 16.0
        for _ in range(25):
            ang = random.uniform(0, math.tau)
            spd = random.uniform(80.0, 300.0)
            self.debris.append(
                DeathDebris(
                    self.player_sx,
                    self.player_sy,
                    math.cos(ang) * spd,
                    math.sin(ang) * spd,
                    color=(220, 80, 80),
                    size=random.uniform(5.0, 12.0),
                    shape="circle",
                )
            )

    def render(self, surface: pygame.Surface):
        if not self.is_active:
            return

        t = self.timer
        ox, oy = self.shake_offset

        # 1. Render Hazard Actor during approach (0.0s to 1.2s)
        if t < 1.4:
            if self.death_type in ("CARRIAGE_CRASH", "CAR_CRASH"):
                self._draw_steam_lorry(surface, self.hazard_actor_x + ox, self.hazard_actor_y + oy)
            elif self.death_type in ("GARGOYLE_COLLAPSE", "COLLAPSE"):
                self._draw_falling_gargoyle(surface, self.hazard_actor_x + ox, self.hazard_actor_y + oy)
            elif self.death_type in ("ASSASSINATION_POISON", "ASSASSINATION"):
                self._draw_assassin_projectile(surface, self.hazard_actor_x + ox, self.hazard_actor_y + oy)
            elif self.death_type in ("GALVANIC_ARC", "ELECTROCUTION"):
                self._draw_lightning_arcs(surface, self.player_sx + ox, self.player_sy + oy)

        # 2. Render Debris Particles
        for d in self.debris:
            d.draw(surface)

        # 3. Vignette & Chromatic Blur Overlay
        vig_alpha = min(220, int((t / 2.0) * 220)) if t < 2.0 else 220
        self._draw_vignette(surface, vig_alpha)

        # 4. Fallen Character Pose (Stagger / Collapse / Shock)
        if self.impact_occurred:
            self._draw_fallen_character_fx(surface, self.player_sx + ox, self.player_sy + oy, t)

        # 5. Stage 2: Fate Title Banner (1.5s to 3.2s)
        if 1.4 <= t < 3.2:
            self._render_fate_banner(surface, t - 1.4)

        # 6. Stage 3: Temporal Rewind Sequence (3.2s to 4.8s)
        if t >= 3.2:
            self._render_temporal_rewind(surface, t - 3.2)

    def _draw_steam_lorry(self, surface: pygame.Surface, x: float, y: float):
        """Draws a heavy 1920s British Brass Steam-Lorry charging at high velocity."""
        w, h = 170, 95
        rect = pygame.Rect(int(x - w // 2), int(y - h // 2), w, h)
        # Vehicle shadow
        pygame.draw.ellipse(surface, (10, 10, 14, 160), rect.move(0, 36).inflate(24, 0))
        # Heavy boiler body (tarnished dark steel and riveted brass)
        pygame.draw.rect(surface, (44, 48, 54), rect, border_radius=12)
        pygame.draw.rect(surface, (208, 154, 62), rect, 3, border_radius=12)
        # Front brass radiator grille & cowl
        rad_rect = pygame.Rect(rect.right - 28, rect.y + 16, 26, h - 32)
        pygame.draw.rect(surface, (188, 138, 52), rad_rect, border_radius=6)
        for gy in range(rad_rect.top + 6, rad_rect.bottom - 4, 6):
            pygame.draw.line(surface, (26, 24, 22), (rad_rect.left + 3, gy), (rad_rect.right - 3, gy), 2)
        # Glaring brass headlamps emitting beam cones
        headlamp_y = rect.centery
        lamp_surf = pygame.Surface((220, 100), pygame.SRCALPHA)
        pts = [(0, 50), (220, 0), (220, 100)]
        pygame.draw.polygon(lamp_surf, (255, 235, 140, 75), pts)
        surface.blit(lamp_surf, (rect.right - 10, headlamp_y - 50))
        # Iron spoke wheels with motion blur sparks
        for wx_c in (rect.left + 32, rect.right - 38):
            wy_c = rect.bottom - 4
            pygame.draw.circle(surface, (28, 26, 28), (wx_c, wy_c), 20)
            pygame.draw.circle(surface, (178, 138, 62), (wx_c, wy_c), 12, 3)
            # Wheel sparks
            if random.random() < 0.7:
                pygame.draw.circle(surface, (255, 210, 90), (wx_c + random.randint(-12, 12), wy_c + 16), 3)

    def _draw_falling_gargoyle(self, surface: pygame.Surface, x: float, y: float):
        """Draws a plummeting carved Norman stone gargoyle masonry block."""
        # Ground shadow expanding beneath player
        progress = max(0.1, min(1.0, (y + 180.0) / (self.player_sy + 180.0)))
        sh_rad = int( progress * 42 )
        sh_surf = pygame.Surface((sh_rad * 2 + 10, sh_rad + 6), pygame.SRCALPHA)
        pygame.draw.ellipse(sh_surf, (8, 8, 12, int(progress * 220)), (5, 3, sh_rad * 2, sh_rad))
        surface.blit(sh_surf, (int(self.player_sx - sh_rad - 5), int(self.player_sy - sh_rad // 2 - 3)))

        # Plunging carved gargoyle block
        w, h = 88, 96
        rect = pygame.Rect(int(x - w // 2), int(y - h // 2), w, h)
        pygame.draw.rect(surface, (88, 84, 82), rect, border_radius=14)
        pygame.draw.rect(surface, (48, 44, 42), rect, 3, border_radius=14)
        # Carved demonic stone visage details
        pygame.draw.circle(surface, (22, 20, 20), (rect.left + 26, rect.y + 34), 9)
        pygame.draw.circle(surface, (22, 20, 20), (rect.right - 26, rect.y + 34), 9)
        pygame.draw.polygon(surface, (44, 40, 38), [(rect.centerx, rect.y + 38), (rect.left + 34, rect.y + 60), (rect.right - 34, rect.y + 60)])
        # Speed streak wind lines
        for dx_s in (-32, 0, 32):
            pygame.draw.line(surface, (220, 215, 205, 140), (x + dx_s, y - 60), (x + dx_s, y - 10), 2)

    def _draw_assassin_projectile(self, surface: pygame.Surface, x: float, y: float):
        """Draws a whistling poison dart with a crimson trail."""
        # Crimson vapor trail
        pygame.draw.line(surface, (225, 45, 68), (x + 85, y), (x, y), 3)
        # Heavy stiletto dart with brass counterbalance
        pygame.draw.line(surface, (230, 225, 220), (x - 18, y), (x + 12, y), 4)
        pygame.draw.polygon(surface, (188, 42, 60), [(x - 24, y), (x - 16, y - 5), (x - 16, y + 5)])
        # Glowing venom aura
        glow = pygame.Surface((28, 28), pygame.SRCALPHA)
        pygame.draw.circle(glow, (215, 52, 85, 110), (14, 14), 12)
        surface.blit(glow, (int(x - 14), int(y - 14)))

    def _draw_lightning_arcs(self, surface: pygame.Surface, x: float, y: float):
        """Draws crackling galvanic lightning arcing into the player."""
        pts = [(x + random.randint(-180, 180), y - 260)]
        curr_x, curr_y = pts[0]
        while curr_y < y:
            curr_x += random.uniform(-35, 35)
            curr_y += random.uniform(25, 55)
            pts.append((curr_x, curr_y))
        pts.append((x, y))

        for i in range(len(pts) - 1):
            pygame.draw.line(surface, (95, 235, 255), pts[i], pts[i + 1], 4)
            pygame.draw.line(surface, (255, 255, 255), pts[i], pts[i + 1], 2)

    def _draw_fallen_character_fx(self, surface: pygame.Surface, x: float, y: float, t: float):
        """Renders the collapsed player character on the cobblestones."""
        # Blood / oil / dust pool expanding slowly
        pool_w = min(76, int(18 + (t * 22)))
        pool_h = pool_w // 2
        p_surf = pygame.Surface((pool_w * 2, pool_h * 2), pygame.SRCALPHA)
        col = (135, 22, 32, 180) if self.death_type != "GALVANIC_ARC" else (24, 28, 36, 210)
        pygame.draw.ellipse(p_surf, col, (0, 0, pool_w * 2, pool_h * 2))
        surface.blit(p_surf, (int(x - pool_w), int(y - pool_h // 2 + 10)))

        # Collapsed body silhouette
        body_surf = pygame.Surface((60, 34), pygame.SRCALPHA)
        pygame.draw.ellipse(body_surf, (38, 44, 58), (4, 8, 48, 20))
        pygame.draw.circle(body_surf, (225, 195, 175), (14, 16), 8)
        surface.blit(body_surf, (int(x - 30), int(y - 8)))

    def _draw_vignette(self, surface: pygame.Surface, alpha: int):
        vig = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        # Dark border vignette
        color = (12, 10, 16, alpha)
        pygame.draw.rect(vig, color, (0, 0, SCREEN_WIDTH, SCREEN_HEIGHT), 140)
        pygame.draw.rect(vig, (4, 4, 6, min(255, alpha + 35)), (0, 0, SCREEN_WIDTH, SCREEN_HEIGHT), 65)
        surface.blit(vig, (0, 0))

    def _render_fate_banner(self, surface: pygame.Surface, sub_t: float):
        """Displays the ornate 1920s gothic title card announcing the death."""
        fade = min(1.0, sub_t / 0.4)
        alpha = int(250 * fade)

        card_w, card_h = 880, 210
        card_rect = pygame.Rect(
            (SCREEN_WIDTH - card_w) // 2,
            int(SCREEN_HEIGHT * 0.22),
            card_w,
            card_h,
        )

        card_surf = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
        pygame.draw.rect(card_surf, (16, 18, 26, alpha), (0, 0, card_w, card_h), border_radius=18)
        pygame.draw.rect(card_surf, (218, 172, 78, alpha), (0, 0, card_w, card_h), 3, border_radius=18)
        surface.blit(card_surf, card_rect.topleft)

        # Death title text
        titles = {
            "CARRIAGE_CRASH": "FATE CLAIMED ITS TOLL: CRUSHED BY STEAM-LORRY",
            "CAR_CRASH": "FATE CLAIMED ITS TOLL: RUNAWAY CARRIAGE IMPACT",
            "ASSASSINATION_POISON": "FATE CLAIMED ITS TOLL: LETHAL ACONITE POISONING",
            "FOOD_CHOKING": "FATE CLAIMED ITS TOLL: ASPHYXIATED ON TAINTED PIE",
            "GARGOYLE_COLLAPSE": "FATE CLAIMED ITS TOLL: CRUSHED BY NORMAN GARGOYLE",
            "GALVANIC_ARC": "FATE CLAIMED ITS TOLL: 10,000-VOLT GALVANIC DISCHARGE",
        }
        title_str = titles.get(self.death_type, "FATE CLAIMED ITS TOLL: PREDESTINED DEATH")

        t_surf = self.font_title.render(title_str, True, (238, 82, 82))
        surface.blit(t_surf, (card_rect.centerx - t_surf.get_width() // 2, card_rect.y + 26))

        sub_str = f"{self.player_name} succumbed on {self.day_name.upper()} (Day {self.day_num}/7)"
        s_surf = self.font_subtitle.render(sub_str, True, (245, 240, 228))
        surface.blit(s_surf, (card_rect.centerx - s_surf.get_width() // 2, card_rect.y + 80))

        desc_str = "Destiny refused to be broken this day... But the Sole-Knower's memory endures."
        d_surf = self.font_body.render(desc_str, True, (205, 195, 180))
        surface.blit(d_surf, (card_rect.centerx - d_surf.get_width() // 2, card_rect.y + 124))

        prompt_str = "« TEMPORAL FABRIC FRACTURING — PREPARING TO REWIND »"
        p_surf = self.font_body.render(prompt_str, True, (105, 218, 235))
        surface.blit(p_surf, (card_rect.centerx - p_surf.get_width() // 2, card_rect.y + 162))

    def _render_temporal_rewind(self, surface: pygame.Surface, rew_t: float):
        """Displays the whirling clockwork temporal rewind vortex back to Monday morning."""
        # Spinning clock hands
        center_x = SCREEN_WIDTH // 2
        center_y = SCREEN_HEIGHT // 2

        # Rewind vortex flash
        vortex_alpha = min(255, int(rew_t * 180))
        vort_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        vort_surf.fill((10, 14, 22, min(230, vortex_alpha)))
        surface.blit(vort_surf, (0, 0))

        # Antique Clock Dial
        clock_rad = 120
        pygame.draw.circle(surface, (28, 26, 32), (center_x, center_y), clock_rad)
        pygame.draw.circle(surface, (218, 172, 78), (center_x, center_y), clock_rad, 4)
        pygame.draw.circle(surface, (142, 108, 48), (center_x, center_y), clock_rad + 8, 2)

        # 12 Roman numeral hour dots
        for hr in range(12):
            ang = hr * (math.tau / 12)
            hx = center_x + math.sin(ang) * (clock_rad - 18)
            hy = center_y - math.cos(ang) * (clock_rad - 18)
            pygame.draw.circle(surface, (242, 198, 82), (int(hx), int(hy)), 3)

        # Rapidly spinning clock hands counter-clockwise!
        spin_ang = -rew_t * 24.0  # Fast counter-clockwise whirl
        # Hour hand
        hx = center_x + math.sin(spin_ang * 0.25) * (clock_rad * 0.55)
        hy = center_y - math.cos(spin_ang * 0.25) * (clock_rad * 0.55)
        pygame.draw.line(surface, (245, 240, 228), (center_x, center_y), (int(hx), int(hy)), 5)

        # Minute hand
        mx = center_x + math.sin(spin_ang * 1.5) * (clock_rad * 0.82)
        my = center_y - math.cos(spin_ang * 1.5) * (clock_rad * 0.82)
        pygame.draw.line(surface, (218, 172, 78), (center_x, center_y), (int(mx), int(my)), 3)

        # Center brass rivet
        pygame.draw.circle(surface, (248, 208, 92), (center_x, center_y), 6)

        # Rewinding calendar text
        days = ["Sunday", "Saturday", "Friday", "Thursday", "Wednesday", "Tuesday", "Monday"]
        day_idx = min(6, int((rew_t / 1.4) * 6))
        display_day = days[day_idx]

        cal_str = f"REWINDING TIME: {display_day.upper()}"
        cal_col = (92, 222, 142) if display_day == "Monday" else (238, 188, 72)
        c_surf = self.font_subtitle.render(cal_str, True, cal_col)
        surface.blit(c_surf, (center_x - c_surf.get_width() // 2, center_y + clock_rad + 28))

        mem_str = f"Inscribing Loop #{self.loop_id} Death Memory into Sole-Knower Journal..."
        m_surf = self.font_body.render(mem_str, True, (245, 240, 228))
        surface.blit(m_surf, (center_x - m_surf.get_width() // 2, center_y + clock_rad + 65))

