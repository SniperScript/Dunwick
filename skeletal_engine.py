"""
Expressive 2.5D RPG Character Renderer & Framed Dialogue Bust Portrait Engine.
- Clean, appealing full-bodied characters with smooth walking, idle breathing,
  blinking eyes, speaking mouths, and role outfits (Zero physics line glitches!).
- High-detail Bust Portrait renderer (`draw_character_portrait`) for the bottom RPG Dialogue Box.
"""

import math
import random
import pygame


class ParticleSystem2D:
    def __init__(self):
        self.particles = []

    def emit_burst(self, x: float, y: float, color: tuple, count: int = 12, speed: float = 90.0, life: float = 0.5):
        for _ in range(count):
            ang = random.uniform(0, math.pi * 2.0)
            spd = random.uniform(speed * 0.3, speed)
            self.particles.append(
                {
                    "x": x,
                    "y": y,
                    "vx": math.cos(ang) * spd,
                    "vy": math.sin(ang) * spd - 15.0,
                    "color": color,
                    "life": life,
                    "max_life": life,
                    "size": random.uniform(2.5, 4.5),
                }
            )

    def emit_step(self, x: float, y: float):
        self.particles.append(
            {
                "x": x + random.uniform(-4, 4),
                "y": y,
                "vx": random.uniform(-10, 10),
                "vy": random.uniform(-14, -4),
                "color": (200, 198, 190),
                "life": 0.25,
                "max_life": 0.25,
                "size": 3.0,
            }
        )

    def update_and_draw(self, surface: pygame.Surface, cam_x: float, cam_y: float, dt: float):
        alive = []
        for p in self.particles:
            p["life"] -= dt
            if p["life"] <= 0:
                continue
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            ratio = max(0.1, p["life"] / p["max_life"])
            rad = max(1, int(p["size"] * ratio))
            pygame.draw.circle(surface, p["color"], (int(p["x"] - cam_x), int(p["y"] - cam_y)), rad)
            alive.append(p)
        self.particles = alive


class SkeletalRig2D:
    """
    Appealing 2.5D RPG Character Sprite with articulated limbs, smooth stride cycle,
    blinking eyes, speaking mouth, and zero physics-line artifacts.
    """

    def __init__(self, spec: dict):
        self.spec = spec
        self.shirt_color = spec.get("shirt", (70, 140, 230))
        self.pants_color = spec.get("pants", (45, 55, 75))
        self.hair_color = spec.get("hair", (75, 52, 38))
        self.skin_color = spec.get("skin", (245, 212, 188))
        self.accessory = spec.get("accessory", "none")
        self.scale = spec.get("scale", 1.0)
        self.primary_color = self.shirt_color

        self.phase = random.uniform(0.0, 6.28)
        self.facing = 1.0
        self.is_moving = False
        self.is_speaking = False
        self.blink_timer = random.uniform(1.5, 4.0)
        self.blink_dur = 0.0

    def update(self, vx: float, vy: float, dt: float, is_speaking: bool = False):
        self.is_speaking = is_speaking
        speed = math.hypot(vx, vy)
        self.is_moving = speed > 8.0
        if abs(vx) > 4.0:
            self.facing = 1.0 if vx > 0 else -1.0

        if self.is_moving:
            self.phase += dt * (speed * 0.065)
        else:
            self.phase += dt * (4.0 if is_speaking else 2.2)

        self.blink_timer -= dt
        if self.blink_timer <= 0:
            self.blink_dur = 0.12
            self.blink_timer = random.uniform(2.2, 4.5)
        if self.blink_dur > 0:
            self.blink_dur = max(0.0, self.blink_dur - dt)

    def draw(
        self,
        surface: pygame.Surface,
        wx: float,
        wy: float,
        cam_x: float,
        cam_y: float,
        is_player: bool = False,
        has_quest_marker: str = None,
        has_memory_anchor: bool = False,
    ):
        s = self.scale
        x = int(wx - cam_x)
        y = int(wy - cam_y)
        outline = (22, 24, 32)

        # Bounce & stride offsets
        if self.is_moving:
            bob = int(-abs(math.sin(self.phase * 2.0)) * 4.0 * s)
            leg_swing = math.sin(self.phase) * 7.5 * s
            arm_swing = math.sin(self.phase) * 8.5 * s
        else:
            bob = int(math.sin(self.phase) * 1.2 * s)
            leg_swing = 0.0
            arm_swing = math.sin(self.phase * 2.0) * (3.5 if self.is_speaking else 1.0) * s

        # 1. Ground Shadow & Player / Deja-Vu Aura Ring
        pygame.draw.ellipse(surface, (28, 36, 30), pygame.Rect(x - int(15 * s), y - 5, int(30 * s), 10))
        if is_player:
            pygame.draw.ellipse(surface, (75, 225, 255), pygame.Rect(x - 22, y - 8, 44, 16), 3)
        if has_memory_anchor:
            pygame.draw.ellipse(surface, (80, 245, 155), pygame.Rect(x - 24, y - 9, 48, 18), 2)

        # 2. Legs & Shoes
        l_foot_x = int(x - 5 * s + leg_swing)
        r_foot_x = int(x + 5 * s - leg_swing)
        l_foot_y = int(y - 2 - max(0, math.cos(self.phase) * 3.5 * s if self.is_moving else 0))
        r_foot_y = int(y - 2 - max(0, -math.cos(self.phase) * 3.5 * s if self.is_moving else 0))
        hip_y = int(y - 14 * s + bob)

        pygame.draw.line(surface, outline, (int(x - 4 * s), hip_y), (l_foot_x, l_foot_y), max(5, int(7 * s)))
        pygame.draw.line(surface, self.pants_color, (int(x - 4 * s), hip_y), (l_foot_x, l_foot_y), max(3, int(5 * s)))

        pygame.draw.line(surface, outline, (int(x + 4 * s), hip_y), (r_foot_x, r_foot_y), max(5, int(7 * s)))
        pygame.draw.line(surface, self.pants_color, (int(x + 4 * s), hip_y), (r_foot_x, r_foot_y), max(3, int(5 * s)))

        # Shoes
        pygame.draw.circle(surface, (35, 38, 48), (l_foot_x, l_foot_y), max(3, int(4 * s)))
        pygame.draw.circle(surface, (35, 38, 48), (r_foot_x, r_foot_y), max(3, int(4 * s)))

        # 3. Back Arm
        torso_top_y = int(y - 30 * s + bob)
        sh_y = torso_top_y + int(4 * s)
        b_hand_x = int(x - 9 * s - arm_swing * 0.7)
        b_hand_y = int(sh_y + 11 * s)
        pygame.draw.line(surface, outline, (int(x - 7 * s), sh_y), (b_hand_x, b_hand_y), max(5, int(6 * s)))
        pygame.draw.line(surface, self.shirt_color, (int(x - 7 * s), sh_y), (b_hand_x, b_hand_y), max(3, int(4 * s)))
        pygame.draw.circle(surface, self.skin_color, (b_hand_x, b_hand_y), max(2, int(3.2 * s)))

        # 4. Rounded Torso / Jacket
        torso_w = int(18 * s)
        torso_h = int(18 * s)
        torso_rect = pygame.Rect(x - torso_w // 2, torso_top_y, torso_w, torso_h)
        pygame.draw.rect(surface, self.shirt_color, torso_rect, border_radius=max(4, int(6 * s)))
        pygame.draw.rect(surface, outline, torso_rect, 2, border_radius=max(4, int(6 * s)))

        # Accessory details on torso
        if self.accessory == "glasses_tie":
            pygame.draw.line(surface, (220, 55, 65), (x + int(self.facing * 2), torso_top_y + 2), (x + int(self.facing * 2), torso_top_y + int(12 * s)), 3)
        elif self.accessory == "apron":
            ap_rect = pygame.Rect(x - int(6 * s), torso_top_y + int(4 * s), int(12 * s), int(13 * s))
            pygame.draw.rect(surface, (245, 245, 250), ap_rect, border_radius=3)
        elif self.accessory == "scarf":
            sc_rect = pygame.Rect(x - int(9 * s), torso_top_y - 1, int(18 * s), int(5 * s))
            pygame.draw.rect(surface, (255, 205, 85), sc_rect, border_radius=3)

        # 5. Front Arm
        f_hand_x = int(x + 9 * s + arm_swing)
        f_hand_y = int(sh_y + 11 * s - (3 if self.is_speaking else 0))
        pygame.draw.line(surface, outline, (int(x + 7 * s), sh_y), (f_hand_x, f_hand_y), max(5, int(6 * s)))
        pygame.draw.line(surface, self.shirt_color, (int(x + 7 * s), sh_y), (f_hand_x, f_hand_y), max(3, int(4 * s)))
        pygame.draw.circle(surface, self.skin_color, (f_hand_x, f_hand_y), max(2, int(3.2 * s)))

        # 6. Expressive Head, Hair, Eyes & Mouth
        head_r = max(8, int(11.5 * s))
        hx = x
        hy = int(torso_top_y - head_r + 3 * s)

        pygame.draw.circle(surface, self.skin_color, (hx, hy), head_r)
        pygame.draw.circle(surface, outline, (hx, hy), head_r, 2)

        # Hair & Hats
        hair_rect = pygame.Rect(hx - head_r - 1, hy - head_r - 2, head_r * 2 + 2, int(head_r * 1.25))
        pygame.draw.arc(surface, self.hair_color, hair_rect, 0.0, math.pi, max(4, int(6 * s)))

        if self.accessory == "cap":
            pygame.draw.arc(surface, (235, 75, 65), hair_rect, 0.0, math.pi, max(5, int(6 * s)))
            pygame.draw.line(
                surface,
                (235, 75, 65),
                (hx, hy - int(4 * s)),
                (hx + int(self.facing * (head_r + 5)), hy - int(3 * s)),
                3,
            )
        elif self.accessory == "cop_hat":
            pygame.draw.ellipse(surface, (30, 52, 105), pygame.Rect(hx - head_r, hy - head_r - 4, head_r * 2, int(9 * s)))
            pygame.draw.circle(surface, (255, 215, 65), (hx + int(self.facing * 3), hy - head_r), 3)

        # Eyes (Two expressive eyes facing direction of movement!)
        ex_base = hx + int(self.facing * 2.5 * s)
        ey = hy - int(1 * s)
        for offset in (-3.5 * s, 3.5 * s):
            ex = int(ex_base + offset)
            if self.blink_dur > 0:
                pygame.draw.line(surface, outline, (ex - 2, ey), (ex + 2, ey), 2)
            else:
                pygame.draw.circle(surface, (255, 255, 255), (ex, ey), 3)
                pygame.draw.circle(surface, (25, 30, 42), (ex + int(self.facing), ey), 2)

        # Glasses if applicable
        if self.accessory == "glasses_tie":
            pygame.draw.rect(surface, (45, 52, 68), pygame.Rect(ex_base - int(6 * s), ey - 3, int(5 * s), 5), 1)
            pygame.draw.rect(surface, (45, 52, 68), pygame.Rect(ex_base + int(1 * s), ey - 3, int(5 * s), 5), 1)

        # Mouth
        mx = ex_base
        my = hy + int(4.5 * s)
        if self.is_speaking:
            mh = 2 + int(abs(math.sin(self.phase * 4.0)) * 3)
            pygame.draw.ellipse(surface, (185, 65, 75), pygame.Rect(mx - 2, my - 1, 5, mh))
        else:
            pygame.draw.arc(surface, (150, 85, 80), pygame.Rect(mx - 3, my - 2, 6, 4), math.pi, math.pi * 2, 2)

        # 7. Floating Quest Marker (`!` or `?`) above Head if this NPC is the current story target!
        if has_quest_marker:
            qy = int(hy - head_r - 18 + math.sin(self.phase * 3.0) * 3)
            q_col = (255, 215, 65) if has_quest_marker == "!" else (85, 225, 255)
            pygame.draw.circle(surface, (20, 24, 34), (hx, qy), 11)
            pygame.draw.circle(surface, q_col, (hx, qy), 11, 2)
            # Draw vector '!' inside circle (no missing font glyphs!)
            pygame.draw.line(surface, q_col, (hx, qy - 5), (hx, qy + 1), 3)
            pygame.draw.circle(surface, q_col, (hx, qy + 5), 2)


def draw_character_portrait(surface: pygame.Surface, rect: pygame.Rect, spec: dict, anim_phase: float = 0.0):
    """
    Draws a large, expressive framed Bust Portrait (`120x120`) inside the bottom RPG Dialogue Box
    just like Stardew Valley / Persona / Undertale!
    """
    # Portrait Background & Frame
    pygame.draw.rect(surface, (34, 42, 62), rect, border_radius=10)
    pygame.draw.rect(surface, spec.get("shirt", (85, 165, 245)), rect.inflate(-6, -6), 2, border_radius=8)
    pygame.draw.rect(surface, (235, 195, 95), rect, 3, border_radius=10)

    cx = rect.centerx
    cy = rect.centery + 8
    skin = spec.get("skin", (245, 212, 188))
    hair = spec.get("hair", (75, 52, 38))
    shirt = spec.get("shirt", (70, 140, 230))
    acc = spec.get("accessory", "none")
    outline = (22, 24, 32)

    # 1. Shoulders & Collar inside Portrait
    sh_rect = pygame.Rect(cx - 38, cy + 16, 76, 34)
    pygame.draw.rect(surface, shirt, sh_rect, border_top_left_radius=18, border_top_right_radius=18)
    pygame.draw.rect(surface, outline, sh_rect, 2, border_top_left_radius=18, border_top_right_radius=18)

    if acc == "glasses_tie":
        pygame.draw.polygon(surface, (225, 55, 65), [(cx - 5, cy + 18), (cx + 5, cy + 18), (cx + 3, cy + 46), (cx - 3, cy + 46)])
    elif acc == "scarf":
        pygame.draw.rect(surface, (255, 205, 85), pygame.Rect(cx - 28, cy + 12, 56, 12), border_radius=5)
    elif acc == "apron":
        pygame.draw.rect(surface, (245, 245, 250), pygame.Rect(cx - 20, cy + 20, 40, 28), border_radius=4)

    # 2. Neck & Head
    pygame.draw.rect(surface, skin, pygame.Rect(cx - 10, cy + 4, 20, 18))
    head_r = 28
    hy = cy - 10
    pygame.draw.circle(surface, skin, (cx, hy), head_r)
    pygame.draw.circle(surface, outline, (cx, hy), head_r, 2)

    # 3. Hair & Hat
    hair_rect = pygame.Rect(cx - head_r - 3, hy - head_r - 5, head_r * 2 + 6, 36)
    pygame.draw.arc(surface, hair, hair_rect, 0.0, math.pi, 12)
    if acc == "cap":
        pygame.draw.arc(surface, (235, 75, 65), hair_rect, 0.0, math.pi, 12)
        pygame.draw.line(surface, (235, 75, 65), (cx - 10, hy - 14), (cx + 34, hy - 12), 5)
    elif acc == "cop_hat":
        pygame.draw.ellipse(surface, (30, 52, 105), pygame.Rect(cx - 30, hy - 36, 60, 18))
        pygame.draw.circle(surface, (255, 215, 65), (cx, hy - 28), 5)

    # 4. Expressive Eyes, Eyebrows & Animated Speaking Mouth
    for ox in (-10, 10):
        ex = cx + ox
        ey = hy - 2
        pygame.draw.circle(surface, (255, 255, 255), (ex, ey), 6)
        pygame.draw.circle(surface, (25, 32, 45), (ex + 1, ey), 3)
        pygame.draw.circle(surface, (255, 255, 255), (ex - 1, ey - 2), 1)
        pygame.draw.line(surface, hair, (ex - 5, ey - 8), (ex + 5, ey - 7), 2)

    if acc == "glasses_tie":
        pygame.draw.rect(surface, (40, 48, 65), pygame.Rect(cx - 18, hy - 8, 15, 12), 2, border_radius=2)
        pygame.draw.rect(surface, (40, 48, 65), pygame.Rect(cx + 3, hy - 8, 15, 12), 2, border_radius=2)
        pygame.draw.line(surface, (40, 48, 65), (cx - 3, hy - 2), (cx + 3, hy - 2), 2)

    # Speaking mouth
    mouth_h = 4 + int(abs(math.sin(anim_phase * 5.0)) * 6)
    pygame.draw.ellipse(surface, (185, 65, 75), pygame.Rect(cx - 6, hy + 10, 12, mouth_h))
