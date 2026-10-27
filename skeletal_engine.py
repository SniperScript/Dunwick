"""
HD-2D & 3D-Pre-Rendered 8-Directional Character Animation Engine (skeletal_engine.py)
Tailored for CHRONICLES OF DUNWICK: DEFYING FATE (1924) — Octopath Traveler HD-2D Edition:
1. Uses 8-directional (N, NE, E, SE, S, SW, W, NW) 3D pre-rendered human character models from
   Kenney `isometric-miniature-dungeon/Characters/Male` shaded with custom 1924 British Steampunk
   attire palettes, golden rim lighting, and crisp dark-sepia HD-2D silhouette outlines.
2. Integrates `space-lab-76` mask-based sprite tinting (`pygame.mask.from_surface`), spark bursts,
   and expanding translucent Aether energy wave rings during terminal scans and premonitions.
3. High-resolution AI Portrait loader + ornate dark-brass Octopath portrait framing.
"""

import math
import os
import random
import pygame

_PORTRAIT_IMG_CACHE: dict[str, pygame.Surface] = {}
_CHAR_SHEET_CACHE: dict[str, list[list[pygame.Surface]]] = {}
_ISOMETRIC_4DIR_CACHE: dict[str, list[pygame.Surface]] = {}
_ISOMETRIC_WALK_CACHE: dict[str, list[list[pygame.Surface]]] = {}
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_ASSETS_PORTRAIT_DIR = os.path.join(_BASE_DIR, "assets", "portraits")
_ASSETS_CHAR_SHEETS_DIR = os.path.join(_BASE_DIR, "assets", "hd2d_sprites", "char_sheets")
_ISOMETRIC_SPRITES_MD_DIR = os.path.join(_BASE_DIR, "isometric sprites md", "isometric sprites md")

ISOMETRIC_MD_MAP = {
    "arthur": {
        "folder": "Lord_Arthur",
        "sheet": "steampunk_businessman_4dir_sheet.png",
        "portrait": "businessman_bottom_left.png",
    },
    "elena": {
        "folder": "Lady_Elena",
        "sheet": "steampunk_housewife_4dir_sheet.png",
        "portrait": "housewife_bottom_left.png",
    },
    "maya": {
        "folder": "Maya_Daughter",
        "sheet": "steampunk_student_daughter_4dir_sheet.png",
        "portrait": "student_daughter_bottom_left.png",
    },
    "leo": {
        "folder": "Leo_Son",
        "sheet": "steampunk_student_son_4dir_sheet.png",
        "portrait": "student_son_bottom_left.png",
    },
    "miller": {
        "folder": "Inspector_Miller",
        "sheet": "steampunk_inspector_4dir_sheet.png",
        "portrait": "inspector_bottom_left.png",
    },
    "rosa": {
        "folder": "Constable_Rosa",
        "sheet": "steampunk_constable_4dir_sheet.png",
        "portrait": "constable_bottom_left.png",
    },
    "clarke": {
        "folder": "Professor_Clark",
        "sheet": "steampunk_professor_4dir_sheet.png",
        "portrait": "professor_bottom_left.png",
    },
    "joya": {
        "folder": "Sister_Joya",
        "sheet": "steampunk_church_sister_4dir_sheet.png",
        "portrait": "church_sister_bottom_left.png",
    },
    "chloe": {
        "folder": "Maya_Friend_Chloe",
        "sheet": "steampunk_student_friend_4dir_sheet.png",
        "portrait": "student_friend_bottom_left.png",
    },
    "lin": {
        "folder": "Apothecary_Rin",
        "sheet": "steampunk_apothecary_4dir_sheet.png",
        "portrait": "apothecary_bottom_left.png",
    },
    "raj": {
        "folder": "Chief_Stoker_Raj",
        "sheet": "steampunk_chief_stoker_4dir_sheet.png",
        "portrait": "chief_stoker_bottom_left.png",
    },
}

NPC_SPRITE_FALLBACK = {
    "sal": "arthur",      # Proprietor Sal
    "mia": "chloe",       # Parlourmaid Mia
    "sam": "raj",         # Master Engineer Sam
    "toby": "leo",        # Toby
    "dan": "leo",         # Dan
    "martha": "joya",     # Baker Martha
    "jenkins": "rosa",    # Constable Jenkins
    "vance": "clarke",    # Director Vance
    "higgins": "chloe",   # Higgins
    "zack": "raj",        # Zack
    "pam": "elena",       # Pamela
    "mayor": "arthur",    # Mayor
}

CELL_W = 64
CELL_H = 82
NUM_DIRS = 8
NUM_COLS = 7


def _load_isometric_walk_cycles(char_id: str, scale: float = 1.0) -> list[list[pygame.Surface]] | None:
    """
    Generates and caches full 8-frame walk animation cycles for all 4 isometric directions
    (0: SE, 1: SW, 2: NE, 3: NW) using character sprite assets from 'isometric sprites md'.
    Incorporates natural leg scissoring, foot lift arcs, torso tilt, and dynamic bobbing.
    """
    mapped_id = char_id if char_id in ISOMETRIC_MD_MAP else NPC_SPRITE_FALLBACK.get(char_id, "arthur")
    cache_key = f"{mapped_id}_{round(scale, 2)}"
    if cache_key in _ISOMETRIC_WALK_CACHE:
        return _ISOMETRIC_WALK_CACHE[cache_key]

    info = ISOMETRIC_MD_MAP.get(mapped_id, ISOMETRIC_MD_MAP["arthur"])
    sheet_p = os.path.join(_ISOMETRIC_SPRITES_MD_DIR, info["folder"], info["sheet"])
    if not os.path.exists(sheet_p):
        return None

    try:
        sheet = pygame.image.load(sheet_p).convert_alpha()
        sw, sh = sheet.get_size()
        col_w = sw // 4
        all_cycles: list[list[pygame.Surface]] = []

        margin_x = 16
        margin_y = 10
        overlap = 6

        for d in range(4):
            sub = sheet.subsurface(pygame.Rect(d * col_w, 0, col_w, sh))
            mask = pygame.mask.from_surface(sub)
            rects = mask.get_bounding_rects()
            if not rects:
                continue
            br = rects[0]
            for r in rects[1:]:
                br.union_ip(r)
            cropped = sub.subsurface(br)
            aspect = br.width / max(1, br.height)
            target_h = max(36, int(84 * scale))
            target_w = max(16, int(target_h * aspect))
            scaled = pygame.transform.smoothscale(cropped, (target_w, target_h))

            w, h = scaled.get_size()
            split_y = int(h * 0.58)
            split_x = int(w * 0.50)

            torso_raw = scaled.subsurface(pygame.Rect(0, 0, w, min(h, split_y + overlap))).copy()
            leg_l_raw = scaled.subsurface(pygame.Rect(0, split_y - 2, split_x, h - (split_y - 2))).copy()
            leg_r_raw = scaled.subsurface(pygame.Rect(split_x, split_y - 2, w - split_x, h - (split_y - 2))).copy()

            frame_w = w + margin_x * 2
            frame_h = h + margin_y * 2

            # Direction coefficients for isometric stride
            if d == 0:  # Bottom-Right (SE)
                sx_mult, sy_mult = 0.8, 0.4
                draw_back_leg_first = True
                tilt_sign = 1.0
            elif d == 1:  # Bottom-Left (SW)
                sx_mult, sy_mult = -0.8, 0.4
                draw_back_leg_first = False
                tilt_sign = -1.0
            elif d == 2:  # Top-Right (NE)
                sx_mult, sy_mult = 0.8, -0.4
                draw_back_leg_first = True
                tilt_sign = 1.0
            else:  # Top-Left (NW)
                sx_mult, sy_mult = -0.8, -0.4
                draw_back_leg_first = False
                tilt_sign = -1.0

            dir_frames: list[pygame.Surface] = []
            for f in range(8):
                surf = pygame.Surface((frame_w, frame_h), pygame.SRCALPHA)
                cx = frame_w // 2
                cy = frame_h - margin_y

                if f == 0:
                    # Neutral standing contact frame
                    surf.blit(leg_l_raw, (cx - (w // 2), cy - (h - (split_y - 2))))
                    surf.blit(leg_r_raw, (cx - (w // 2) + split_x, cy - (h - (split_y - 2))))
                    surf.blit(torso_raw, (cx - (w // 2), cy - h))
                else:
                    # Active walk stride frame
                    phase = (f / 8.0) * math.tau
                    stride = math.sin(phase)
                    s_l = stride * 4.2
                    s_r = -stride * 4.2
                    lift_l = max(0.0, math.cos(phase)) * 3.2
                    lift_r = max(0.0, -math.cos(phase)) * 3.2
                    bob = int(math.sin(phase * 2.0) * 2.0)
                    tilt = math.sin(phase) * 2.2 * tilt_sign

                    pos_l_x = cx - (w // 2) + int(s_l * sx_mult)
                    pos_l_y = cy - (h - (split_y - 2)) + int(s_l * sy_mult) - int(lift_l)

                    pos_r_x = cx - (w // 2) + split_x + int(s_r * sx_mult)
                    pos_r_y = cy - (h - (split_y - 2)) + int(s_r * sy_mult) - int(lift_r)

                    if draw_back_leg_first:
                        surf.blit(leg_l_raw, (pos_l_x, pos_l_y))
                        surf.blit(leg_r_raw, (pos_r_x, pos_r_y))
                    else:
                        surf.blit(leg_r_raw, (pos_r_x, pos_r_y))
                        surf.blit(leg_l_raw, (pos_l_x, pos_l_y))

                    t_rot = pygame.transform.rotate(torso_raw, tilt)
                    torso_top_y = cy - h + bob
                    t_rect = t_rot.get_rect(center=(cx, torso_top_y + (split_y + overlap) // 2))
                    surf.blit(t_rot, t_rect.topleft)

                dir_frames.append(surf)

            all_cycles.append(dir_frames)

        if len(all_cycles) == 4:
            _ISOMETRIC_WALK_CACHE[cache_key] = all_cycles
            return all_cycles
    except Exception:
        pass
    return None


def _load_isometric_4dir_frames(char_id: str, scale: float = 1.0) -> list[pygame.Surface] | None:
    """Loads and caches the 4 neutral directional isometric frames from 'isometric sprites md'."""
    cycles = _load_isometric_walk_cycles(char_id, scale)
    if cycles and len(cycles) == 4:
        return [cycles[0][0], cycles[1][0], cycles[2][0], cycles[3][0]]
    return None


def _shade(col: tuple[int, int, int], factor: float) -> tuple[int, int, int]:
    return (
        max(0, min(255, int(col[0] * factor))),
        max(0, min(255, int(col[1] * factor))),
        max(0, min(255, int(col[2] * factor))),
    )


def _load_char_sheet_grid(char_id: str) -> list[list[pygame.Surface]] | None:
    if char_id in _CHAR_SHEET_CACHE:
        return _CHAR_SHEET_CACHE[char_id]

    sheet_path = os.path.join(_ASSETS_CHAR_SHEETS_DIR, f"{char_id}.png")
    if not os.path.exists(sheet_path):
        # Fallback to arthur.png if a custom ID is requested
        sheet_path = os.path.join(_ASSETS_CHAR_SHEETS_DIR, "arthur.png")
    if os.path.exists(sheet_path):
        try:
            sheet = pygame.image.load(sheet_path).convert_alpha()
            grid: list[list[pygame.Surface]] = []
            for d in range(NUM_DIRS):
                row_frames: list[pygame.Surface] = []
                for c in range(NUM_COLS):
                    sub = pygame.Surface((CELL_W, CELL_H), pygame.SRCALPHA)
                    sub.blit(sheet, (0, 0), pygame.Rect(c * CELL_W, d * CELL_H, CELL_W, CELL_H))
                    row_frames.append(sub)
                grid.append(row_frames)
            _CHAR_SHEET_CACHE[char_id] = grid
            return grid
        except Exception:
            _CHAR_SHEET_CACHE[char_id] = None
            return None
    return None


class ParticleSystem2D:
    """
    HD-2D Atmospheric Particle & Energy-Wave System (incorporating `space-lab-76` spark & wave effects).
    """

    def __init__(self):
        self.particles: list[dict] = []
        self.energy_waves: list[dict] = []

    def emit_step(self, x: float, y: float):
        if len(self.particles) < 220:
            self.particles.append(
                {
                    "x": x + random.uniform(-6, 6),
                    "y": y + random.uniform(-2, 3),
                    "vx": random.uniform(-16, 16),
                    "vy": random.uniform(-22, -6),
                    "life": 0.42,
                    "max_life": 0.42,
                    "size": random.uniform(2.5, 4.8),
                    "color": (168, 156, 138),
                    "glow": False,
                }
            )

    def emit_steam(self, x: float, y: float):
        if len(self.particles) < 220:
            self.particles.append(
                {
                    "x": x + random.uniform(-5, 5),
                    "y": y,
                    "vx": random.uniform(-14, 14),
                    "vy": random.uniform(-42, -18),
                    "life": 0.65,
                    "max_life": 0.65,
                    "size": random.uniform(4.2, 7.8),
                    "color": (222, 218, 210),
                    "glow": False,
                }
            )

    def emit_burst(self, x: float, y: float, color: tuple, count: int = 18, speed: float = 105.0):
        """Emits glowing HD-2D sparks + a `space-lab-76` expanding translucent energy wave ring."""
        for _ in range(count):
            ang = random.uniform(0, math.tau)
            spd = random.uniform(28.0, speed)
            self.particles.append(
                {
                    "x": x,
                    "y": y,
                    "vx": math.cos(ang) * spd,
                    "vy": math.sin(ang) * spd,
                    "life": random.uniform(0.38, 0.78),
                    "max_life": 0.78,
                    "size": random.uniform(3.2, 6.2),
                    "color": color,
                    "glow": True,
                }
            )
        if len(self.energy_waves) < 12:
            self.energy_waves.append(
                {
                    "x": x,
                    "y": y,
                    "radius": 8.0,
                    "max_radius": 92.0,
                    "alpha": 195.0,
                    "color": color[:3],
                }
            )

    def update_and_draw(self, surface: pygame.Surface, cam_x: float, cam_y: float, dt: float):
        # 1. Draw `space-lab-76` expanding translucent energy wave rings
        alive_waves = []
        for w in self.energy_waves:
            w["radius"] += dt * 135.0
            w["alpha"] -= dt * 260.0
            if w["alpha"] > 8.0 and w["radius"] < w["max_radius"]:
                sx, sy = int(w["x"] - cam_x), int(w["y"] - cam_y)
                rad = int(w["radius"])
                wave_surf = pygame.Surface((rad * 2 + 6, rad * 2 + 6), pygame.SRCALPHA)
                col_rgba = (*w["color"], max(0, min(255, int(w["alpha"]))))
                pygame.draw.ellipse(
                    wave_surf,
                    col_rgba,
                    (3, rad // 2 + 3, rad * 2, max(8, rad)),
                    3,
                )
                surface.blit(wave_surf, (sx - rad - 3, sy - rad - 3))
                alive_waves.append(w)
        self.energy_waves = alive_waves

        # 2. Draw particles & glowing embers
        alive = []
        for p in self.particles:
            p["life"] -= dt
            if p["life"] > 0:
                p["x"] += p["vx"] * dt
                p["y"] += p["vy"] * dt
                ratio = max(0.1, p["life"] / p["max_life"])
                r = max(2, int(p["size"] * ratio))
                sx, sy = int(p["x"] - cam_x), int(p["y"] - cam_y)
                if p.get("glow"):
                    glow_s = pygame.Surface((r * 4, r * 4), pygame.SRCALPHA)
                    pygame.draw.circle(glow_s, (*p["color"][:3], int(95 * ratio)), (r * 2, r * 2), r * 2)
                    surface.blit(glow_s, (sx - r * 2, sy - r * 2))
                pygame.draw.circle(surface, p["color"], (sx, sy), r)
                pygame.draw.circle(surface, (20, 16, 14), (sx, sy), r, 1)
                alive.append(p)
        self.particles = alive


class SkeletalRig2D:
    """
    8-Directional 3D-Pre-Rendered HD-2D Character Rig tailored to 1924 Steampunk Britain.
    """

    def __init__(self, spec: dict):
        self.spec = spec
        self.char_id = spec.get("id", "")
        self.shirt = spec.get("shirt", (70, 140, 230))
        self.pants = spec.get("pants", (45, 55, 78))
        self.hair = spec.get("hair", (65, 45, 32))
        self.skin = spec.get("skin", (245, 212, 186))
        self.accessory = spec.get("accessory", "none")
        self.scale = spec.get("scale", 1.0)

        self.walk_phase = random.uniform(0.0, math.tau)
        self.idle_phase = random.uniform(0.0, math.tau)
        self.facing_x = 1.0
        self.facing_dir = "DOWN"
        # 8-direction index matching Kenney Male_0..7:
        # 0: NE, 1: E, 2: SE, 3: S (Down), 4: SW, 5: W, 6: NW, 7: N (Up)
        self.dir_idx = 3
        self.speed_ratio = 0.0
        self.is_speaking = False
        self.talk_timer = 0.0

    def update(self, vx: float, vy: float, dt: float, is_speaking: bool = False):
        spd = math.hypot(vx, vy)
        target_ratio = min(1.0, spd / 155.0)
        self.speed_ratio += (target_ratio - self.speed_ratio) * min(1.0, dt * 14.0)
        self.is_speaking = is_speaking

        if spd > 8.0:
            if abs(vx) > 4.0:
                self.facing_x = 1.0 if vx > 0 else -1.0
            # Compute 8-way direction from (vx, vy) where +x is East, +y is South
            ang = math.degrees(math.atan2(vy, vx))  # -180..180 (0=E, 90=S, -90=N, 180/-180=W)
            if -67.5 <= ang < -22.5:
                self.dir_idx = 0  # NE
                self.facing_dir = "UP"
            elif -22.5 <= ang < 22.5:
                self.dir_idx = 1  # E
                self.facing_dir = "RIGHT"
            elif 22.5 <= ang < 67.5:
                self.dir_idx = 2  # SE
                self.facing_dir = "RIGHT"
            elif 67.5 <= ang < 112.5:
                self.dir_idx = 3  # S
                self.facing_dir = "DOWN"
            elif 112.5 <= ang < 157.5:
                self.dir_idx = 4  # SW
                self.facing_dir = "LEFT"
            elif ang >= 157.5 or ang < -157.5:
                self.dir_idx = 5  # W
                self.facing_dir = "LEFT"
            elif -157.5 <= ang < -112.5:
                self.dir_idx = 6  # NW
                self.facing_dir = "UP"
            else:
                self.dir_idx = 7  # N
                self.facing_dir = "UP"

        if self.speed_ratio > 0.06:
            self.walk_phase = (self.walk_phase + dt * (8.5 + 6.5 * self.speed_ratio)) % math.tau
        else:
            self.idle_phase = (self.idle_phase + dt * 3.2) % math.tau

        if is_speaking:
            self.talk_timer = (self.talk_timer + dt * 14.0) % math.tau

    def _draw_steampunk_prop_aura(self, surface: pygame.Surface, sx: int, sy: int, dir_x: int):
        """Draws glowing 1924 British Steampunk role equipment (Bullseye Lantern, Alchemical Phial, Chronometer)."""
        cid = self.char_id
        hx = sx + dir_x * 14
        hy = sy - 34
        if cid in ("miller", "rosa", "hank"):
            # Scotland Yard Brass Bullseye Lantern + Warm Additive Halo
            glow = pygame.Surface((36, 36), pygame.SRCALPHA)
            pygame.draw.circle(glow, (255, 208, 92, 68), (18, 18), 16)
            surface.blit(glow, (hx - 18, hy - 18))
            pygame.draw.circle(surface, (255, 228, 120), (hx, hy), 4)
            pygame.draw.circle(surface, (36, 28, 18), (hx, hy), 5, 1)
        elif cid in ("maya", "clarke", "lin"):
            # Glowing Galvanic / Alchemical Phial
            glow = pygame.Surface((30, 30), pygame.SRCALPHA)
            pygame.draw.circle(glow, (78, 242, 198, 65), (15, 15), 13)
            surface.blit(glow, (hx - 15, hy - 15))
            pygame.draw.circle(surface, (112, 255, 218), (hx, hy), 3)
            pygame.draw.circle(surface, (24, 38, 36), (hx, hy), 4, 1)
        elif cid == "arthur":
            # Brass Pocket-Chronometer Glint
            pygame.draw.circle(surface, (242, 198, 82), (hx, hy), 4)
            pygame.draw.circle(surface, (42, 30, 18), (hx, hy), 4, 1)

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
        is_protected_loved_one: bool = False,
    ):
        sx = int(wx - cam_x)
        sy = int(wy - cam_y)
        if sx < -90 or sx > surface.get_width() + 90 or sy < -110 or sy > surface.get_height() + 90:
            return

        sc = self.scale
        dir_x = int(self.facing_x)
        ticks = pygame.time.get_ticks()

        # 1. Soft Multi-Layered HD-2D Ambient Occlusion Ground Shadow
        sh_w = int(38 * sc)
        sh_h = int(16 * sc)
        sh_surf = pygame.Surface((sh_w + 8, sh_h + 8), pygame.SRCALPHA)
        pygame.draw.ellipse(sh_surf, (10, 12, 16, 135), (4, 4, sh_w, sh_h))
        pygame.draw.ellipse(sh_surf, (6, 8, 12, 190), (8, 6, sh_w - 8, sh_h - 4))
        surface.blit(sh_surf, (sx - sh_w // 2 - 4, sy - sh_h // 2 - 2))

        # 2. Ornate HD-2D Status Rings (Player Chronometer Ring, Loved-One Thread of Fate, Memory Anchor)
        if is_player:
            pulse = int(math.sin(ticks * 0.007) * 2)
            ring_rect = pygame.Rect(
                sx - sh_w // 2 - 6 - pulse,
                sy - sh_h // 2 - 3 - pulse,
                sh_w + 12 + pulse * 2,
                sh_h + 8 + pulse * 2,
            )
            pygame.draw.ellipse(surface, (242, 198, 82), ring_rect, 2)
            pygame.draw.ellipse(surface, (138, 98, 32), ring_rect.inflate(4, 2), 1)

        if is_protected_loved_one:
            pulse = int(math.cos(ticks * 0.009) * 3)
            love_rect = pygame.Rect(
                sx - sh_w // 2 - 8 - pulse,
                sy - sh_h // 2 - 4 - pulse,
                sh_w + 16 + pulse * 2,
                sh_h + 10 + pulse * 2,
            )
            pygame.draw.ellipse(surface, (98, 228, 255), love_rect, 2)

        if has_memory_anchor:
            anc_rect = pygame.Rect(sx - sh_w // 2 - 3, sy - sh_h // 2 - 1, sh_w + 6, sh_h + 4)
            pygame.draw.ellipse(surface, (92, 238, 155), anc_rect, 2)

        # 3. 2.5D Isometric Character Rendering using 'isometric sprites md'
        iso_cycles = _load_isometric_walk_cycles(self.char_id, self.scale)
        if iso_cycles is not None:
            # 8-direction mapping to 4 isometric angles:
            # Frame 0: Bottom-Right (SE)
            # Frame 1: Bottom-Left (SW)
            # Frame 2: Top-Right (NE)
            # Frame 3: Top-Left (NW)
            if self.dir_idx in (0, 7) and self.facing_x > 0:
                frame_idx = 2  # NE
            elif self.dir_idx in (6, 7) and self.facing_x <= 0:
                frame_idx = 3  # NW
            elif self.dir_idx in (1, 2, 3) and self.facing_x > 0:
                frame_idx = 0  # SE
            else:
                frame_idx = 1  # SW

            dir_frames = iso_cycles[frame_idx]

            if self.speed_ratio > 0.08:
                # Active animated walk cycle
                walk_idx = int((self.walk_phase / math.tau) * 8.0) % 8
                frame_surf = dir_frames[walk_idx]
                bob_y = 0
                sway_x = 0
            else:
                # Idle standing pose with gentle breathing
                frame_surf = dir_frames[0]
                bob_y = int(math.sin(self.idle_phase) * 1.4)
                sway_x = 0
                if self.is_speaking:
                    bob_y -= int(abs(math.sin(self.talk_timer)) * 2.0)

            margin_y = 10
            tw, th = frame_surf.get_size()

            # Anchor feet reliably at ground shadow center (sx, sy)
            dest_x = sx - tw // 2 + sway_x
            dest_y = sy - th + margin_y + bob_y
            surface.blit(frame_surf, (dest_x, dest_y))

            # Silhouette Aura when speaking or anchored in memory
            if (is_protected_loved_one or has_memory_anchor) and hasattr(pygame, "mask"):
                try:
                    mask = pygame.mask.from_surface(frame_surf)
                    tint_col = (95, 225, 255, 38) if is_protected_loved_one else (92, 238, 155, 32)
                    tint_surf = mask.to_surface(setcolor=tint_col, unsetcolor=(0, 0, 0, 0))
                    surface.blit(tint_surf, (dest_x, dest_y))
                except Exception:
                    pass

            self._draw_steampunk_prop_aura(surface, sx, sy, dir_x)
            return

        # Fallback to Kenney grid if isometric sheet is not found
        grid = _load_char_sheet_grid(self.char_id)
        if grid is not None:
            if self.speed_ratio > 0.08:
                run_idx = 1 + (int((self.walk_phase / math.tau) * 5.0) % 5)
                frame_surf = grid[self.dir_idx][run_idx]
                bob_y = 0
            else:
                frame_surf = grid[self.dir_idx][0]
                bob_y = int(math.sin(self.idle_phase) * 1.2)
                if self.is_speaking:
                    bob_y -= int(abs(math.sin(self.talk_timer)) * 2.0)

            if abs(sc - 1.0) > 0.04:
                tw = max(32, int(CELL_W * sc))
                th = max(42, int(CELL_H * sc))
                frame_surf = pygame.transform.smoothscale(frame_surf, (tw, th))
            else:
                tw, th = CELL_W, CELL_H

            dest_x = sx - tw // 2
            dest_y = sy - th + int(6 * sc) + bob_y
            surface.blit(frame_surf, (dest_x, dest_y))

            if (is_protected_loved_one or has_memory_anchor) and hasattr(pygame, "mask"):
                try:
                    mask = pygame.mask.from_surface(frame_surf)
                    tint_col = (95, 225, 255, 38) if is_protected_loved_one else (92, 238, 155, 32)
                    tint_surf = mask.to_surface(setcolor=tint_col, unsetcolor=(0, 0, 0, 0))
                    surface.blit(tint_surf, (dest_x, dest_y))
                except Exception:
                    pass

            self._draw_steampunk_prop_aura(surface, sx, sy, dir_x)
            return

        # Fallback if sprite sheets are unavailable
        pygame.draw.circle(surface, self.shirt, (sx, sy - 24), 12)
        pygame.draw.circle(surface, self.skin, (sx, sy - 42), 9)


def draw_character_portrait(surface: pygame.Surface, rect: pygame.Rect, spec: dict, anim_phase: float = 0.0):
    """
    Renders an authentic Character Portrait using the character's isometric design
    from 'isometric sprites md' (NO AI-generated portrait images), framed within
    an ornate dark-brass & mahogany Octopath HD-2D frame.
    """
    cid = spec.get("id", "")
    cache_key = f"iso_md_{cid}_{rect.width}x{rect.height}"

    if cache_key not in _PORTRAIT_IMG_CACHE:
        mapped_id = cid if cid in ISOMETRIC_MD_MAP else NPC_SPRITE_FALLBACK.get(cid, "arthur")
        info = ISOMETRIC_MD_MAP.get(mapped_id, ISOMETRIC_MD_MAP["arthur"])
        p_path = os.path.join(_ISOMETRIC_SPRITES_MD_DIR, info["folder"], info["portrait"])

        if os.path.exists(p_path):
            try:
                raw = pygame.image.load(p_path).convert_alpha()
                mask = pygame.mask.from_surface(raw)
                rects = mask.get_bounding_rects()
                full_rect = rects[0]
                for r in rects[1:]:
                    full_rect.union_ip(r)

                # Crop head & upper torso (top 46% of character height)
                crop_h = max(20, int(full_rect.height * 0.46))
                crop_w = max(20, full_rect.width)
                sub = raw.subsurface(pygame.Rect(full_rect.x, full_rect.y, crop_w, crop_h))

                inner_w, inner_h = rect.width - 8, rect.height - 8
                aspect = crop_w / max(1, crop_h)
                if inner_w / inner_h > aspect:
                    target_h = inner_h
                    target_w = int(inner_h * aspect)
                else:
                    target_w = inner_w
                    target_h = int(inner_w / aspect)

                scaled = pygame.transform.smoothscale(sub, (target_w, target_h))
                portrait_surf = pygame.Surface((inner_w, inner_h), pygame.SRCALPHA)
                # Subtle mahogany backdrop
                pygame.draw.rect(portrait_surf, (26, 22, 28), (0, 0, inner_w, inner_h), border_radius=8)
                portrait_surf.blit(scaled, ((inner_w - target_w) // 2, (inner_h - target_h) // 2))

                # Rounded corner mask
                masked = pygame.Surface((inner_w, inner_h), pygame.SRCALPHA)
                pygame.draw.rect(masked, (255, 255, 255, 255), (0, 0, inner_w, inner_h), border_radius=8)
                masked.blit(portrait_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)

                _PORTRAIT_IMG_CACHE[cache_key] = masked
            except Exception:
                _PORTRAIT_IMG_CACHE[cache_key] = None
        else:
            _PORTRAIT_IMG_CACHE[cache_key] = None

    # Ornate Dark-Brass & Obsidian Octopath Frame
    pygame.draw.rect(surface, (16, 14, 18), rect, border_radius=10)
    p_img = _PORTRAIT_IMG_CACHE.get(cache_key)
    if p_img is not None:
        surface.blit(p_img, (rect.x + 4, rect.y + 4))

    border_col = (108, 236, 178) if anim_phase > 0 else (218, 172, 78)
    pygame.draw.rect(surface, (62, 46, 24), rect, 4, border_radius=10)
    pygame.draw.rect(surface, border_col, rect, 2, border_radius=10)
    # Corner brass rivets
    for rx_c in (rect.left + 5, rect.right - 6):
        for ry_c in (rect.top + 5, rect.bottom - 6):
            pygame.draw.circle(surface, (238, 194, 88), (rx_c, ry_c), 2)
