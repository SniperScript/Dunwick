"""
2.5D Defined Pixel-Art Character Animation & Portrait Engine (skeletal_engine.py)
Inspired by:
- Terraria / Starbound / Octopath Traveler / Eastward (Defined 2.5D sprites with crisp 2px dark
  outlines, 3/4 depth shading, layered clothing, and character role props)
- GemRB & Flare RPG (Multi-directional facing & pronounced 8-phase walk/idle/talk animation)

Features:
1. Larger, well-defined 2.5D characters (~64px tall) with 4-way/3/4 directional facing.
2. Pronounced, unmistakable animations:
   - High-step knee-bend walk cycle with heel strike, swinging arms, coat/apron sway, and hair bounce
   - Continuous idle breathing, eye blinking, and role-prop idle motion
   - Animated talking mouth & gesture bounce during dialogue
3. High-resolution AI Portrait loader + 2.5D Portrait renderer for the Figma-styled UI & Dialogue Box.
"""

import math
import os
import random
import pygame

_PORTRAIT_IMG_CACHE: dict[str, pygame.Surface] = {}
_ASSETS_PORTRAIT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "portraits")


def _shade(col: tuple[int, int, int], factor: float) -> tuple[int, int, int]:
    return (
        max(0, min(255, int(col[0] * factor))),
        max(0, min(255, int(col[1] * factor))),
        max(0, min(255, int(col[2] * factor))),
    )


class ParticleSystem2D:
    def __init__(self):
        self.particles = []

    def emit_step(self, x: float, y: float):
        if len(self.particles) < 160:
            self.particles.append(
                {
                    "x": x + random.uniform(-6, 6),
                    "y": y + random.uniform(-2, 3),
                    "vx": random.uniform(-16, 16),
                    "vy": random.uniform(-22, -6),
                    "life": 0.42,
                    "max_life": 0.42,
                    "size": random.uniform(3.5, 6.0),
                    "color": (218, 206, 184),
                }
            )

    def emit_burst(self, x: float, y: float, color: tuple, count: int = 16, speed: float = 95.0):
        for _ in range(count):
            ang = random.uniform(0, math.tau)
            spd = random.uniform(25.0, speed)
            self.particles.append(
                {
                    "x": x,
                    "y": y,
                    "vx": math.cos(ang) * spd,
                    "vy": math.sin(ang) * spd,
                    "life": random.uniform(0.35, 0.7),
                    "max_life": 0.7,
                    "size": random.uniform(3.5, 6.5),
                    "color": color,
                }
            )

    def update_and_draw(self, surface: pygame.Surface, cam_x: float, cam_y: float, dt: float):
        alive = []
        for p in self.particles:
            p["life"] -= dt
            if p["life"] > 0:
                p["x"] += p["vx"] * dt
                p["y"] += p["vy"] * dt
                ratio = max(0.1, p["life"] / p["max_life"])
                r = max(2, int(p["size"] * ratio))
                sx, sy = int(p["x"] - cam_x), int(p["y"] - cam_y)
                pygame.draw.circle(surface, p["color"], (sx, sy), r)
                pygame.draw.circle(surface, (32, 28, 24), (sx, sy), r, 1)
                alive.append(p)
        self.particles = alive


class SkeletalRig2D:
    """
    2.5D Defined Pixel-Art Character Rig (~64px tall) with:
    - 4-Directional 3/4 Perspective (LEFT, RIGHT, UP, DOWN)
    - Multi-jointed 2-bone legs (thigh + shin + 3D boot) & 2-bone arms (upper arm + forearm + prop)
    - Secondary hair/coat/scarf bounce, eye blinking, breathing, and talking animations
    """

    def __init__(self, spec: dict):
        self.spec = spec
        self.char_id = spec.get("id", "")
        self.shirt = spec.get("shirt", (70, 140, 230))
        self.pants = spec.get("pants", (45, 55, 78))
        self.hair = spec.get("hair", (65, 45, 32))
        self.skin = spec.get("skin", (245, 212, 186))
        self.accessory = spec.get("accessory", "none")
        self.scale = spec.get("scale", 1.0) * 1.18  # Larger, more defined 2.5D presence!

        self.walk_phase = random.uniform(0.0, math.tau)
        self.idle_phase = random.uniform(0.0, math.tau)
        self.facing_x = 1.0
        self.facing_dir = "DOWN"  # "LEFT", "RIGHT", "UP", "DOWN"
        self.speed_ratio = 0.0
        self.is_speaking = False
        self.talk_timer = 0.0

    def update(self, vx: float, vy: float, dt: float, is_speaking: bool = False):
        spd = math.hypot(vx, vy)
        target_ratio = min(1.0, spd / 155.0)
        self.speed_ratio += (target_ratio - self.speed_ratio) * min(1.0, dt * 14.0)
        self.is_speaking = is_speaking

        if abs(vx) > 8.0 or abs(vy) > 8.0:
            if abs(vx) >= abs(vy) * 0.75:
                self.facing_x = 1.0 if vx > 0 else -1.0
                self.facing_dir = "RIGHT" if vx > 0 else "LEFT"
            else:
                self.facing_dir = "UP" if vy < 0 else "DOWN"

        if self.speed_ratio > 0.05:
            # Fast, responsive 8-step walk cycle frequency
            self.walk_phase = (self.walk_phase + dt * (8.5 + 6.5 * self.speed_ratio)) % math.tau
        else:
            self.idle_phase = (self.idle_phase + dt * 3.4) % math.tau

        if is_speaking:
            self.talk_timer = (self.talk_timer + dt * 15.0) % math.tau

    def _draw_capsule_limb(
        self,
        surface: pygame.Surface,
        p1: tuple[int, int],
        p2: tuple[int, int],
        radius: int,
        fill_col: tuple[int, int, int],
        outline_col: tuple[int, int, int] = (24, 20, 18),
    ):
        """Draws a 2.5D shaded limb segment with dark crisp outline and top highlight."""
        pygame.draw.line(surface, outline_col, p1, p2, radius * 2 + 4)
        pygame.draw.circle(surface, outline_col, p1, radius + 2)
        pygame.draw.circle(surface, outline_col, p2, radius + 2)

        pygame.draw.line(surface, fill_col, p1, p2, radius * 2)
        pygame.draw.circle(surface, fill_col, p1, radius)
        pygame.draw.circle(surface, fill_col, p2, radius)

    def _draw_boot(self, surface: pygame.Surface, fx: int, fy: int, dir_x: int, sc: float):
        """Draws a 3D-shaded leather RPG boot with sole and toe cap."""
        bw = max(9, int(11 * sc))
        bh = max(6, int(7 * sc))
        bx = fx - bw // 2 + int(dir_x * 3 * sc)
        by = fy - bh // 2
        boot_rect = pygame.Rect(bx, by, bw, bh)
        pygame.draw.rect(surface, (22, 18, 16), boot_rect.inflate(4, 4), border_radius=4)
        pygame.draw.rect(surface, (68, 44, 30), boot_rect, border_radius=3)
        pygame.draw.line(surface, (112, 76, 52), (boot_rect.left + 2, boot_rect.top + 1), (boot_rect.right - 2, boot_rect.top + 1), 2)

    def _draw_held_prop(self, surface: pygame.Surface, hx: int, hy: int, dir_x: int, sc: float):
        """Draws a character-specific 2.5D role item in their front hand so characters feel alive!"""
        cid = self.char_id
        if cid == "arthur":
            # Glowing Architect Blueprint Tablet
            r = pygame.Rect(hx - 4, hy - 6, 12, 15)
            pygame.draw.rect(surface, (24, 28, 36), r.inflate(2, 2), border_radius=3)
            pygame.draw.rect(surface, (75, 205, 255), r, border_radius=2)
        elif cid == "elena":
            # Reporter's Press Notebook
            r = pygame.Rect(hx - 4, hy - 6, 11, 14)
            pygame.draw.rect(surface, (32, 24, 20), r.inflate(2, 2), border_radius=2)
            pygame.draw.rect(surface, (245, 232, 195), r, border_radius=2)
        elif cid == "maya" or cid == "clarke":
            # Science Frequency Scanner / Glowing Flask
            pygame.draw.circle(surface, (24, 32, 36), (hx + dir_x * 3, hy), 7)
            pygame.draw.circle(surface, (80, 245, 205), (hx + dir_x * 3, hy), 5)
        elif cid in ("sal", "mia"):
            # Silver Cafe Tray & Espresso Cup
            pygame.draw.ellipse(surface, (195, 202, 215), (hx - 7, hy - 3, 16, 6))
            pygame.draw.rect(surface, (248, 245, 238), (hx - 3, hy - 9, 7, 7), border_radius=2)
        elif cid in ("miller", "rosa", "hank"):
            # Brass Lantern / Security Baton
            pygame.draw.circle(surface, (255, 220, 95), (hx + dir_x * 3, hy + 2), 5)
            pygame.draw.circle(surface, (36, 30, 22), (hx + dir_x * 3, hy + 2), 5, 2)
        elif cid in ("sam", "raj", "zack"):
            # Hardware Parcel / Steel Wrench
            r = pygame.Rect(hx - 5, hy - 5, 12, 10)
            pygame.draw.rect(surface, (185, 132, 72), r, border_radius=2)
            pygame.draw.rect(surface, (42, 30, 18), r, 2, border_radius=2)

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
        sx = int(wx - cam_x)
        sy = int(wy - cam_y)
        if sx < -90 or sx > surface.get_width() + 90 or sy < -110 or sy > surface.get_height() + 90:
            return

        sc = self.scale
        outline = (22, 18, 16)
        dir_x = int(self.facing_x)

        # 1. 2.5D Ground Shadow & Player Ring
        sh_w = int(34 * sc)
        sh_h = int(14 * sc)
        pygame.draw.ellipse(surface, (26, 38, 28), (sx - sh_w // 2, sy - sh_h // 2 + 2, sh_w, sh_h))

        if is_player:
            pulse = int(math.sin(pygame.time.get_ticks() * 0.008) * 2)
            ring_rect = pygame.Rect(sx - sh_w // 2 - 5 - pulse, sy - sh_h // 2 - 2 - pulse, sh_w + 10 + pulse * 2, sh_h + 6 + pulse * 2)
            pygame.draw.ellipse(surface, (85, 235, 255), ring_rect, 3)

        if has_memory_anchor:
            anc_rect = pygame.Rect(sx - sh_w // 2 - 3, sy - sh_h // 2 - 1, sh_w + 6, sh_h + 4)
            pygame.draw.ellipse(surface, (80, 245, 155), anc_rect, 2)

        # 2. Compute Pronounced 8-Phase Walk & Idle Kinematics!
        w_sin = math.sin(self.walk_phase)
        w_cos = math.cos(self.walk_phase)
        i_sin = math.sin(self.idle_phase)
        sr = self.speed_ratio

        # Vertical bounce on every step (abs(cos) gives 2 bounces per stride cycle!)
        walk_bounce = abs(w_cos) * 6.5 * sr
        idle_breath = i_sin * 2.2 * (1.0 - sr)
        talk_bounce = abs(math.sin(self.talk_timer)) * 2.5 if self.is_speaking else 0.0
        body_y_off = int(-walk_bounce + idle_breath - talk_bounce)

        # Leg swing & knee lift (pronounced ±13px stride so walking looks super lively!)
        stride_x = int(w_sin * 13.0 * sr * sc)
        front_lift = int(max(0.0, -w_cos) * 8.5 * sr * sc)
        back_lift = int(max(0.0, w_cos) * 8.5 * sr * sc)

        # Hip & Shoulder anchors
        hip_y = sy - int(18 * sc) + body_y_off
        torso_h = int(21 * sc)
        torso_w = int(20 * sc)
        shoulder_y = hip_y - torso_h + int(3 * sc)

        # 3. Back Arm (behind torso)
        arm_swing = int(w_sin * 13.0 * sr * sc)
        back_sh = (sx - dir_x * int(5 * sc), shoulder_y + 2)
        back_hand = (sx - dir_x * int(6 * sc) - arm_swing, shoulder_y + int(14 * sc) - abs(arm_swing) // 3)
        self._draw_capsule_limb(surface, back_sh, back_hand, max(3, int(3.8 * sc)), _shade(self.shirt, 0.74), outline)
        pygame.draw.circle(surface, _shade(self.skin, 0.85), back_hand, max(3, int(3.2 * sc)))

        # 4. Back Leg & Boot (with knee joint!)
        back_hip = (sx - dir_x * int(4 * sc), hip_y)
        back_foot = (sx - dir_x * int(4 * sc) - stride_x, sy - 2 - back_lift)
        back_knee = (
            (back_hip[0] + back_foot[0]) // 2 + dir_x * int(3 * sc * sr),
            (back_hip[1] + back_foot[1]) // 2 - int(2 * sc),
        )
        self._draw_capsule_limb(surface, back_hip, back_knee, max(3, int(4.2 * sc)), _shade(self.pants, 0.72), outline)
        self._draw_capsule_limb(surface, back_knee, back_foot, max(3, int(3.8 * sc)), _shade(self.pants, 0.68), outline)
        self._draw_boot(surface, back_foot[0], back_foot[1], dir_x, sc)

        # 5. Front Leg & Boot (with knee joint!)
        front_hip = (sx + dir_x * int(4 * sc), hip_y)
        front_foot = (sx + dir_x * int(4 * sc) + stride_x, sy - 2 - front_lift)
        front_knee = (
            (front_hip[0] + front_foot[0]) // 2 + dir_x * int(4 * sc * sr),
            (front_hip[1] + front_foot[1]) // 2 - int(2 * sc),
        )
        self._draw_capsule_limb(surface, front_hip, front_knee, max(4, int(4.4 * sc)), self.pants, outline)
        self._draw_capsule_limb(surface, front_knee, front_foot, max(3, int(4.0 * sc)), _shade(self.pants, 0.92), outline)
        self._draw_boot(surface, front_foot[0], front_foot[1], dir_x, sc)

        # 6. 2.5D Layered Torso, Jacket/Vest, Belt & Accessory
        torso_rect = pygame.Rect(sx - torso_w // 2, hip_y - torso_h, torso_w, torso_h + 3)
        pygame.draw.rect(surface, outline, torso_rect.inflate(4, 4), border_radius=7)
        # Shadowed side of torso + lit side of torso for 3D cylindrical volume
        pygame.draw.rect(surface, _shade(self.shirt, 0.82), torso_rect, border_radius=6)
        lit_w = int(torso_w * 0.68)
        lit_x = torso_rect.left + (torso_w - lit_w if dir_x > 0 else 0)
        pygame.draw.rect(surface, self.shirt, (lit_x, torso_rect.top, lit_w, torso_rect.height - 2), border_radius=5)

        # Belt & Buckle
        belt_y = torso_rect.bottom - 5
        pygame.draw.line(surface, (42, 32, 24), (torso_rect.left + 2, belt_y), (torso_rect.right - 2, belt_y), 3)
        pygame.draw.rect(surface, (235, 195, 75), (sx + dir_x * 2 - 2, belt_y - 2, 5, 4))

        # Role Accessories on Torso
        if self.accessory == "apron":
            ap_sway = int(w_sin * 2 * sr)
            ap_rect = pygame.Rect(sx - int(7 * sc) + ap_sway, torso_rect.top + 5, int(14 * sc), torso_h - 3)
            pygame.draw.rect(surface, (246, 244, 238), ap_rect, border_radius=3)
            pygame.draw.rect(surface, outline, ap_rect, 1, border_radius=3)
        elif self.accessory == "glasses_tie":
            pygame.draw.line(
                surface,
                (215, 58, 62),
                (sx + dir_x * 3, torso_rect.top + 3),
                (sx + dir_x * 3, torso_rect.bottom - 5),
                3,
            )
        elif self.accessory == "scarf":
            scarf_rect = pygame.Rect(torso_rect.left - 1, torso_rect.top - 1, torso_w + 2, 7)
            pygame.draw.rect(surface, (245, 228, 185), scarf_rect, border_radius=3)
            pygame.draw.rect(surface, outline, scarf_rect, 1, border_radius=3)

        # 7. Head, Expressive Face, Hair Bounce & Headgear
        head_r = int(11.5 * sc)
        head_x = sx + dir_x * int(2 * sc * sr)
        head_y = torso_rect.top - head_r + int(3 * sc)

        # Back hair bun/flow
        hair_bounce = int(walk_bounce * 0.45)
        pygame.draw.circle(surface, outline, (head_x, head_y), head_r + 2)
        pygame.draw.circle(surface, self.skin, (head_x, head_y), head_r)
        # Warm cheek blush
        pygame.draw.circle(surface, _shade(self.skin, 0.92), (head_x + dir_x * int(3 * sc), head_y + 2), max(2, int(2.5 * sc)))

        # Hair Crown & Sidelocks
        hair_rect = pygame.Rect(head_x - head_r - 1, head_y - head_r - 3 - hair_bounce, head_r * 2 + 2, int(head_r * 1.15))
        pygame.draw.ellipse(surface, outline, hair_rect.inflate(2, 2))
        pygame.draw.ellipse(surface, self.hair, hair_rect)
        pygame.draw.arc(
            surface,
            _shade(self.hair, 1.3),
            hair_rect.inflate(-4, -3),
            0.3,
            2.8,
            2,
        )

        # Eyes (with natural blinking) & Mouth (animated when speaking)
        if self.facing_dir != "UP":
            blink = (pygame.time.get_ticks() + hash(self.char_id) * 197) % 3600 < 130
            eye_x1 = head_x + dir_x * int(2 * sc)
            eye_x2 = head_x + dir_x * int(7 * sc)
            eye_y = head_y - int(1 * sc)
            if blink:
                pygame.draw.line(surface, outline, (eye_x1 - 2, eye_y), (eye_x1 + 2, eye_y), 2)
                pygame.draw.line(surface, outline, (eye_x2 - 2, eye_y), (eye_x2 + 2, eye_y), 2)
            else:
                for ex in (eye_x1, eye_x2):
                    pygame.draw.circle(surface, (250, 250, 250), (ex, eye_y), max(2, int(2.6 * sc)))
                    pygame.draw.circle(surface, (24, 28, 38), (ex + dir_x, eye_y), max(1, int(1.6 * sc)))

            if self.accessory == "glasses_tie":
                pygame.draw.circle(surface, (42, 48, 58), (eye_x1, eye_y), int(3.8 * sc), 1)
                pygame.draw.circle(surface, (42, 48, 58), (eye_x2, eye_y), int(3.8 * sc), 1)

            # Mouth
            mouth_x = head_x + dir_x * int(4.5 * sc)
            mouth_y = head_y + int(4.5 * sc)
            if self.is_speaking and int(self.talk_timer * 2) % 2 == 0:
                pygame.draw.circle(surface, (175, 58, 62), (mouth_x, mouth_y), max(2, int(2.5 * sc)))
            else:
                pygame.draw.line(surface, (142, 78, 68), (mouth_x - 2, mouth_y), (mouth_x + 2, mouth_y), 2)

        # Headgear (Caps, Police Hats, Headphones)
        if self.accessory == "cap":
            cap_r = pygame.Rect(head_x - head_r, head_y - head_r - 4 - hair_bounce, head_r * 2, int(8 * sc))
            pygame.draw.rect(surface, (225, 68, 62), cap_r, border_radius=4)
            pygame.draw.rect(surface, outline, cap_r, 1, border_radius=4)
            visor_x = head_x if dir_x > 0 else head_x - head_r - 5
            pygame.draw.rect(surface, (185, 48, 44), (visor_x, head_y - head_r + 1 - hair_bounce, head_r + 5, 4), border_radius=2)
        elif self.accessory == "cop_hat":
            hat_r = pygame.Rect(head_x - head_r - 2, head_y - head_r - 6 - hair_bounce, head_r * 2 + 4, int(9 * sc))
            pygame.draw.rect(surface, (36, 58, 108), hat_r, border_radius=3)
            pygame.draw.rect(surface, outline, hat_r, 2, border_radius=3)
            pygame.draw.circle(surface, (255, 215, 75), (head_x + dir_x * 2, hat_r.centery), 3)
        elif self.accessory == "headphones":
            pygame.draw.arc(
                surface,
                (75, 225, 210),
                (head_x - head_r - 2, head_y - head_r - 3, head_r * 2 + 4, head_r * 2),
                0.2,
                2.94,
                3,
            )
            pygame.draw.circle(surface, (55, 215, 195), (head_x - dir_x * 3, head_y + 1), int(4.2 * sc))
            pygame.draw.circle(surface, outline, (head_x - dir_x * 3, head_y + 1), int(4.2 * sc), 1)

        # 8. Front Arm, Hand & Character Role Prop (in front of torso!)
        front_sh = (sx + dir_x * int(4 * sc), shoulder_y + 2)
        talk_gesture = int(abs(math.sin(self.talk_timer)) * 6 * sc) if self.is_speaking else 0
        front_hand = (
            sx + dir_x * int(6 * sc) + arm_swing,
            shoulder_y + int(14 * sc) - abs(arm_swing) // 3 - talk_gesture,
        )
        self._draw_capsule_limb(surface, front_sh, front_hand, max(3, int(4.0 * sc)), self.shirt, outline)
        pygame.draw.circle(surface, self.skin, front_hand, max(3, int(3.4 * sc)))
        pygame.draw.circle(surface, outline, front_hand, max(3, int(3.4 * sc)), 1)
        self._draw_held_prop(surface, front_hand[0], front_hand[1], dir_x, sc)


def draw_character_portrait(surface: pygame.Surface, rect: pygame.Rect, spec: dict, anim_phase: float = 0.0):
    """
    Renders a Character Portrait inside `rect`:
    - First checks if a high-resolution Generative AI portrait PNG/JPG exists in `assets/portraits/{id}.png`!
    - If found, renders the AI portrait with a sleek Figma-style rounded frame and live speaking aura.
    - Otherwise, renders a rich 2.5D timber-background character bust portrait with animated talking mouth.
    """
    cid = spec.get("id", "")
    cache_key = f"{cid}_{rect.width}x{rect.height}"

    if cache_key not in _PORTRAIT_IMG_CACHE:
        p_path = os.path.join(_ASSETS_PORTRAIT_DIR, f"{cid}.png")
        if os.path.exists(p_path):
            try:
                raw = pygame.image.load(p_path).convert_alpha()
                inner_w, inner_h = rect.width - 8, rect.height - 8
                scaled = pygame.transform.smoothscale(raw, (inner_w, inner_h))
                # Apply rounded corners mask
                masked = pygame.Surface((inner_w, inner_h), pygame.SRCALPHA)
                pygame.draw.rect(masked, (255, 255, 255, 255), (0, 0, inner_w, inner_h), border_radius=10)
                masked.blit(scaled, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
                _PORTRAIT_IMG_CACHE[cache_key] = masked
            except Exception:
                _PORTRAIT_IMG_CACHE[cache_key] = None
        else:
            _PORTRAIT_IMG_CACHE[cache_key] = None

    ai_img = _PORTRAIT_IMG_CACHE.get(cache_key)
    if ai_img is not None:
        # Outer dark frame + gold/cyan accent border
        pygame.draw.rect(surface, (22, 26, 36), rect, border_radius=12)
        surface.blit(ai_img, (rect.x + 4, rect.y + 4))
        border_col = (85, 235, 175) if anim_phase > 0 else (232, 192, 95)
        pygame.draw.rect(surface, border_col, rect, 3, border_radius=12)
        return

    # Fallback 2.5D Defined Pixel-Art Bust Portrait with Cozy Timber Interior Background
    pygame.draw.rect(surface, (42, 34, 28), rect, border_radius=12)
    inner = rect.inflate(-8, -8)
    pygame.draw.rect(surface, (68, 52, 40), inner, border_radius=9)
    # Warm sunlit window panes in background
    pygame.draw.rect(surface, (112, 86, 62), (inner.left + 8, inner.top + 8, inner.width - 16, 26), border_radius=4)

    cx = rect.centerx
    cy = rect.centery + 10
    shirt = spec.get("shirt", (70, 140, 230))
    hair = spec.get("hair", (65, 45, 32))
    skin = spec.get("skin", (245, 212, 186))
    acc = spec.get("accessory", "none")

    # Shoulders & Collar
    sh_rect = pygame.Rect(cx - 42, cy + 12, 84, 44)
    pygame.draw.rect(surface, (20, 18, 16), sh_rect.inflate(4, 4), border_radius=16)
    pygame.draw.rect(surface, shirt, sh_rect, border_radius=15)
    pygame.draw.polygon(surface, (245, 245, 245), [(cx - 14, cy + 12), (cx + 14, cy + 12), (cx, cy + 30)])

    if acc == "glasses_tie":
        pygame.draw.line(surface, (220, 55, 60), (cx, cy + 20), (cx, cy + 50), 6)
    elif acc == "scarf":
        pygame.draw.rect(surface, (245, 228, 185), (cx - 28, cy + 8, 56, 14), border_radius=5)

    # Neck & Head
    pygame.draw.rect(surface, skin, (cx - 10, cy - 4, 20, 20), border_radius=4)
    head_y = cy - 18
    pygame.draw.circle(surface, (20, 18, 16), (cx, head_y), 30)
    pygame.draw.circle(surface, skin, (cx, head_y), 28)

    # Hair
    hair_top = pygame.Rect(cx - 30, head_y - 32, 60, 28)
    pygame.draw.ellipse(surface, hair, hair_top)
    pygame.draw.rect(surface, hair, (cx - 30, head_y - 18, 11, 24), border_radius=4)
    pygame.draw.rect(surface, hair, (cx + 19, head_y - 18, 11, 24), border_radius=4)

    # Eyes
    for ex in (cx - 10, cx + 10):
        pygame.draw.circle(surface, (250, 250, 250), (ex, head_y - 3), 5)
        pygame.draw.circle(surface, (25, 30, 42), (ex + 1, head_y - 3), 3)
        pygame.draw.line(surface, hair, (ex - 5, head_y - 10), (ex + 5, head_y - 10), 2)

    if acc == "glasses_tie":
        pygame.draw.circle(surface, (38, 44, 54), (cx - 10, head_y - 3), 8, 2)
        pygame.draw.circle(surface, (38, 44, 54), (cx + 10, head_y - 3), 8, 2)
        pygame.draw.line(surface, (38, 44, 54), (cx - 2, head_y - 3), (cx + 2, head_y - 3), 2)

    # Mouth (animates when speaking)
    talk_open = anim_phase > 0.0 and int(anim_phase * 14.0) % 2 == 0
    if talk_open:
        pygame.draw.ellipse(surface, (185, 65, 70), (cx - 6, head_y + 9, 12, 8))
    else:
        pygame.draw.arc(surface, (150, 82, 72), (cx - 7, head_y + 6, 14, 8), 3.4, 6.0, 2)

    if acc == "cap":
        pygame.draw.rect(surface, (225, 68, 62), (cx - 28, head_y - 34, 56, 16), border_radius=6)
    elif acc == "cop_hat":
        pygame.draw.rect(surface, (36, 58, 108), (cx - 30, head_y - 36, 60, 18), border_radius=4)
        pygame.draw.circle(surface, (255, 215, 75), (cx, head_y - 27), 4)

    pygame.draw.rect(surface, (232, 192, 95), rect, 3, border_radius=12)
