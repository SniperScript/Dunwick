"""Dunwick -> IsoEngine Isometric Sprite & Tile Generator.

Audits all non-isometric assets from the Dunwick game (top-down tiles, flat front-facing
walls/columns/doors, flat 2D landmark houses, flat props, procedural 2D furniture/quest
stations, and flat side-view vehicles) and transforms/renders them into true 2:1
isometric tile and grid sprites for IsoEngine.
"""

from __future__ import annotations

import json
import math
import os
import random
import shutil
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter


# Source paths (checks local complete copy first, then Dunwick directory)
DUNWICK_SOURCES = [
    Path("/home/dareconduit/.gemini/antigravity/brain/14741d72-1e75-4460-a174-2bc89dc07419/scratch/dunwick_assets"),
    Path("/home/dareconduit/Documents/Coding Stuff/Dunwick/assets/hd2d_sprites"),
]

OUTPUT_ROOT = Path("/home/dareconduit/Documents/IsoEngine/assets/iso_sprites")

# Standard IsoEngine tile dimensions (2:1 isometric diamond)
TILE_W = 64
TILE_H = 32
BLOCK_H = 16  # Elevation / block thickness in pixels


def get_source_dir() -> Path:
    """Locate the Dunwick hd2d_sprites directory."""
    for p in DUNWICK_SOURCES:
        if p.exists():
            return p
    raise FileNotFoundError("Could not find Dunwick hd2d_sprites directory.")


def load_src_image(src_root: Path, rel_path: str) -> Image.Image:
    """Load an RGBA PIL image from the Dunwick asset folder and clean low-alpha noise."""
    basename = Path(rel_path).name
    candidates = [
        src_root / rel_path,
        src_root / "props" / basename,
        src_root / "tiles" / basename,
    ]
    for root in DUNWICK_SOURCES:
        candidates.append(root / rel_path)
        candidates.append(root / "props" / basename)
        candidates.append(root / "tiles" / basename)

    for full_path in candidates:
        if full_path.exists():
            return Image.open(full_path).convert("RGBA")
    # Fallback solid texture if missing
    img = Image.new("RGBA", (64, 64), (110, 100, 90, 255))
    return img


def tight_crop_opaque(img: Image.Image, alpha_threshold: int = 45) -> Image.Image:
    """Crop an RGBA image tightly around pixels with alpha > alpha_threshold.

    Also strips faint background matte/shadow rectangles present in some Kenney sprites.
    """
    rgba = img.convert("RGBA")
    w, h = rgba.size
    px = rgba.load()

    # Check if corners have a uniform matte color (like a grey background card)
    corner_samples = [px[0, 0], px[w - 1, 0], px[0, h - 1], px[w - 1, h - 1]]
    bg_color = None
    if all(c[3] > 200 for c in corner_samples):
        c0 = corner_samples[0]
        if all(abs(c[0] - c0[0]) < 12 and abs(c[1] - c0[1]) < 12 and abs(c[2] - c0[2]) < 12 for c in corner_samples):
            bg_color = c0[:3]

    cleaned = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    dst = cleaned.load()
    min_x, min_y, max_x, max_y = w, h, -1, -1

    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a <= alpha_threshold:
                continue
            if bg_color is not None:
                if abs(r - bg_color[0]) < 14 and abs(g - bg_color[1]) < 14 and abs(b - bg_color[2]) < 14:
                    continue
            dst[x, y] = (r, g, b, a)
            if x < min_x:
                min_x = x
            if y < min_y:
                min_y = y
            if x > max_x:
                max_x = x
            if y > max_y:
                max_y = y

    if max_x >= min_x and max_y >= min_y:
        return cleaned.crop((min_x, min_y, max_x + 1, max_y + 1))
    return rgba



# ==============================================================================
# 1. MATHEMATICAL ISOMETRIC PROJECTION HELPERS
# ==============================================================================

def project_top_diamond(
    texture: Image.Image,
    tile_w: int = TILE_W,
    tile_h: int = TILE_H,
    brightness: float = 1.0,
    border_color: Optional[tuple[int, int, int, int]] = (28, 25, 22, 160),
) -> Image.Image:
    """Project a square top-down texture onto a 2:1 isometric diamond surface."""
    tex = texture.convert("RGBA").resize((tile_w, tile_w), Image.Resampling.BICUBIC)
    if brightness != 1.0:
        rgb = ImageEnhance.Brightness(tex.convert("RGB")).enhance(brightness)
        tex = Image.merge("RGBA", (*rgb.split(), tex.split()[3]))

    out = Image.new("RGBA", (tile_w, tile_h), (0, 0, 0, 0))
    src_px = tex.load()
    dst_px = out.load()

    half_w = tile_w / 2.0
    half_h = tile_h / 2.0

    for sy in range(tile_h):
        for sx in range(tile_w):
            dx = (sx - half_w) / half_w
            dy = (sy - half_h) / half_h
            # Diamond bounds check: |dx| + |dy| <= 1.0
            if abs(dx) + abs(dy) <= 1.0:
                # Inverse isometric mapping to UV in [0, 1]
                u = (dx + dy + 1.0) * 0.5
                v = (dy - dx + 1.0) * 0.5
                tx = min(tile_w - 1, max(0, int(u * (tile_w - 1))))
                ty = min(tile_w - 1, max(0, int(v * (tile_w - 1))))
                r, g, b, a = src_px[tx, ty]
                if a > 0:
                    # Subtle directional lighting across diamond (brighter N/NW, slightly deeper S/SE)
                    shade = 1.04 - 0.08 * (sy / tile_h)
                    dst_px[sx, sy] = (
                        min(255, max(0, int(r * shade))),
                        min(255, max(0, int(g * shade))),
                        min(255, max(0, int(b * shade))),
                        a,
                    )

    if border_color:
        draw = ImageDraw.Draw(out)
        pts = [
            (tile_w // 2, 0),
            (tile_w - 1, tile_h // 2),
            (tile_w // 2, tile_h - 1),
            (0, tile_h // 2),
        ]
        draw.polygon(pts, outline=border_color)

    return out


def make_iso_block(
    top_tex: Image.Image,
    side_tex: Optional[Image.Image] = None,
    tile_w: int = TILE_W,
    tile_h: int = TILE_H,
    block_h: int = BLOCK_H,
    left_shade: float = 0.72,
    right_shade: float = 0.54,
    bevel_color: tuple[int, int, int, int] = (230, 215, 190, 75),
) -> Image.Image:
    """Create a 3D isometric tile block (64 x 48) with top diamond and shaded left/right faces."""
    if side_tex is None:
        side_tex = top_tex

    total_h = tile_h + block_h
    out = Image.new("RGBA", (tile_w, total_h), (0, 0, 0, 0))

    # 1. Top diamond
    top_diamond = project_top_diamond(top_tex, tile_w=tile_w, tile_h=tile_h, border_color=None)
    out.alpha_composite(top_diamond, (0, 0))

    # 2. Left and Right vertical isometric skirts
    half_w = tile_w // 2
    half_h = tile_h // 2
    s_tex = side_tex.convert("RGBA").resize((half_w, max(block_h, 16)), Image.Resampling.BICUBIC)
    s_px = s_tex.load()
    dst_px = out.load()

    for x in range(half_w):
        # Left face: x goes 0 -> half_w - 1, top edge goes half_h -> tile_h - 1
        y_top_l = half_h + int((x / half_w) * half_h)
        for dy in range(block_h):
            y = y_top_l + dy
            if 0 <= y < total_h:
                ty = min(s_tex.height - 1, int((dy / max(1, block_h)) * (s_tex.height - 1)))
                r, g, b, a = s_px[x, ty]
                if a > 10:
                    dst_px[x, y] = (
                        int(r * left_shade),
                        int(g * left_shade),
                        int(b * left_shade),
                        255,
                    )

        # Right face: x_r goes half_w -> tile_w - 1, top edge goes tile_h - 1 -> half_h
        x_r = half_w + x
        y_top_r = (tile_h - 1) - int((x / half_w) * half_h)
        for dy in range(block_h):
            y = y_top_r + dy
            if 0 <= y < total_h:
                ty = min(s_tex.height - 1, int((dy / max(1, block_h)) * (s_tex.height - 1)))
                r, g, b, a = s_px[x, ty]
                if a > 10:
                    dst_px[x_r, y] = (
                        int(r * right_shade),
                        int(g * right_shade),
                        int(b * right_shade),
                        255,
                    )

    # 3. Crisp isometric edges & highlight bevels
    draw = ImageDraw.Draw(out)
    top_pt = (half_w, 0)
    right_pt = (tile_w - 1, half_h)
    bottom_pt = (half_w, tile_h - 1)
    left_pt = (0, half_h)
    bot_left = (0, half_h + block_h - 1)
    bot_mid = (half_w, tile_h + block_h - 1)
    bot_right = (tile_w - 1, half_h + block_h - 1)

    outline_dark = (22, 20, 18, 190)
    draw.line([top_pt, right_pt, bottom_pt, left_pt, top_pt], fill=(32, 28, 24, 150), width=1)
    draw.line([left_pt, bot_left, bot_mid, bot_right, right_pt], fill=outline_dark, width=1)
    draw.line([bottom_pt, bot_mid], fill=outline_dark, width=1)
    # Front bevel highlight
    draw.line([left_pt, bottom_pt, right_pt], fill=bevel_color, width=1)

    return out


def shear_wall_face(
    tex: Image.Image,
    width: int,
    height: int,
    direction: str = "SW",
    shade: float = 0.9,
) -> Image.Image:
    """Shear a flat rectangular wall/facade texture onto an isometric vertical plane.

    direction='SW': slopes down-right (+2:1 isometric X axis, facing SW viewer)
    direction='SE': slopes up-right (-2:1 isometric Y axis, facing SE viewer)
    """
    src = tex.convert("RGBA").resize((width, height), Image.Resampling.BICUBIC)
    drop = width // 2
    out = Image.new("RGBA", (width, height + drop), (0, 0, 0, 0))
    src_px = src.load()
    dst_px = out.load()

    for x in range(width):
        y_offset = (x // 2) if direction == "SW" else ((width - 1 - x) // 2)
        for y in range(height):
            r, g, b, a = src_px[x, y]
            if a > 15:
                dst_px[x, y + y_offset] = (
                    min(255, int(r * shade)),
                    min(255, int(g * shade)),
                    min(255, int(b * shade)),
                    a,
                )
    return out


# ==============================================================================
# 2. PROCEDURAL DUNWICK TEXTURES (FOR PROCEDURAL NON-ISO TILES IN DUNWICK)
# ==============================================================================

def build_procedural_top_textures(src_root: Path) -> dict[str, Image.Image]:
    """Build top-down source textures for Dunwick's procedural tiles before iso projection."""
    rng = random.Random(1924)
    textures: dict[str, Image.Image] = {}

    # 1. Severn Moorland Grass (rich moss & clover greensward)
    moor = Image.new("RGBA", (64, 64), (58, 82, 52, 255))
    draw = ImageDraw.Draw(moor)
    for _ in range(220):
        gx, gy = rng.randint(0, 63), rng.randint(0, 63)
        c = rng.choice([(46, 68, 42, 255), (68, 94, 58, 255), (76, 102, 64, 255), (52, 74, 46, 255)])
        draw.line([(gx, gy), (gx, max(0, gy - rng.randint(2, 4)))], fill=c, width=1)
    for _ in range(18):
        fx, fy = rng.randint(4, 59), rng.randint(4, 59)
        draw.ellipse((fx - 1, fy - 1, fx + 1, fy + 1), fill=(195, 180, 120, 220))
    textures["moor_grass"] = moor

    # 2. High Street Cobblestone + Recessed Brass & Iron Steam-Tramway Rails
    cobble_src = load_src_image(src_root, "tiles/stone_tile.png").resize((64, 64), Image.Resampling.BICUBIC)
    # Darken slightly to match Dunwick's T_ROAD basalt cobblestone
    cobble_rgb = ImageEnhance.Brightness(cobble_src.convert("RGB")).enhance(0.78)
    cobble = Image.merge("RGBA", (*cobble_rgb.split(), cobble_src.split()[3]))
    textures["cobblestone"] = cobble

    # Tram rail along X axis (NE-SW) and Y axis (NW-SE)
    tram_x = cobble.copy()
    d_tx = ImageDraw.Draw(tram_x)
    # Oak sleepers
    for sx in range(4, 64, 10):
        d_tx.rectangle([sx, 14, sx + 4, 50], fill=(62, 45, 32, 255), outline=(38, 28, 20, 255))
    # Iron rail grooves + polished brass/steel rails
    d_tx.rectangle([0, 19, 63, 24], fill=(28, 30, 35, 255))
    d_tx.rectangle([0, 20, 63, 22], fill=(185, 165, 115, 255))
    d_tx.rectangle([0, 40, 63, 45], fill=(28, 30, 35, 255))
    d_tx.rectangle([0, 41, 63, 43], fill=(185, 165, 115, 255))
    textures["tram_rail_x"] = tram_x
    textures["tram_rail_y"] = tram_x.rotate(90, expand=False)

    # 3. Crosswalk (Step-stone slabs across basalt cobblestone with brass studs)
    cross = cobble.copy()
    step_slab = tight_crop_opaque(load_src_image(src_root, "tiles/step_stone.png")).resize((64, 64), Image.Resampling.BICUBIC)
    d_cr = ImageDraw.Draw(cross)
    for y_band in (8, 26, 44):
        strip = step_slab.crop((0, y_band, 64, y_band + 12))
        cross.paste(strip, (0, y_band))
        d_cr.rectangle([0, y_band, 63, y_band + 12], outline=(40, 38, 35, 220))
        # Brass road studs
        for sx in (6, 57):
            d_cr.ellipse([sx - 2, y_band + 4, sx + 2, y_band + 8], fill=(215, 175, 85, 255))
    textures["crosswalk"] = cross

    # 4. Door Threshold (Limestone step + woven crimson & gold welcome mat)
    thresh = load_src_image(src_root, "tiles/stone_slab.png").resize((64, 64), Image.Resampling.BICUBIC)
    d_th = ImageDraw.Draw(thresh)
    d_th.rectangle([10, 14, 54, 50], fill=(138, 38, 42, 255), outline=(212, 172, 78, 255), width=2)
    d_th.rectangle([14, 18, 50, 46], outline=(185, 140, 60, 255), width=1)
    textures["door_threshold"] = thresh

    # 5. St. Dunstan's Fencing Yard Court (T_GYM)
    gym = load_src_image(src_root, "tiles/stone_inset.png").resize((64, 64), Image.Resampling.BICUBIC)
    d_gym = ImageDraw.Draw(gym)
    d_gym.rectangle([3, 3, 60, 60], outline=(215, 190, 125, 220), width=2)
    d_gym.line([(32, 3), (32, 60)], fill=(215, 190, 125, 200), width=2)
    d_gym.ellipse([20, 20, 44, 44], outline=(195, 75, 65, 210), width=2)
    textures["gym_court"] = gym

    # 6. Severn Canal / Fountain Water
    water = Image.new("RGBA", (64, 64), (36, 78, 98, 255))
    d_wa = ImageDraw.Draw(water)
    for wy in range(4, 60, 8):
        for wx in range(4, 56, 14):
            d_wa.arc([wx, wy, wx + 12, wy + 6], start=0, end=180, fill=(95, 158, 185, 200), width=1)
    d_wa.rectangle([0, 0, 63, 63], outline=(68, 95, 112, 255), width=2)
    textures["water"] = water

    return textures


# ==============================================================================
# 3. GENERATE ISOMETRIC GROUND, ROAD, SIDEWALK & FLOOR TILES
# ==============================================================================

def generate_iso_tiles(src_root: Path, out_dir: Path) -> list[dict]:
    """Convert all Dunwick top-down tiles and procedural ground types into isometric tiles & blocks."""
    tiles_dir = out_dir / "tiles"
    tiles_dir.mkdir(parents=True, exist_ok=True)
    proc_tex = build_procedural_top_textures(src_root)

    # Copy existing iso_cube_grass and iso_cube_rocky for completeness
    manifest = []
    for existing in ("iso_cube_grass.png", "iso_cube_rocky.png"):
        src_p = src_root / "tiles" / existing
        if src_p.exists():
            shutil.copy2(src_p, tiles_dir / existing)
            manifest.append({
                "id": existing.replace(".png", ""),
                "category": "tiles",
                "file": f"tiles/{existing}",
                "source": f"tiles/{existing} (existing isometric cube)",
                "footprint": [1, 1],
            })

    tile_specs = [
        # (id, source_or_proc, label, brightness, left_shade, right_shade)
        ("iso_dirt_ground", "tiles/dirt_ground.png", "Moorland Dirt Ground", 1.0, 0.72, 0.54),
        ("iso_dirt_tiles", "tiles/dirt_tiles.png", "Dirt Stepping Stones", 1.0, 0.72, 0.54),
        ("iso_moor_grass", "proc:moor_grass", "Severn Moorland Greensward", 1.0, 0.75, 0.58),
        ("iso_cobblestone", "proc:cobblestone", "High Street Basalt Cobblestone", 1.0, 0.70, 0.52),
        ("iso_tram_rail_ne", "proc:tram_rail_x", "Steam-Tramway Rail (NE-SW)", 1.0, 0.70, 0.52),
        ("iso_tram_rail_nw", "proc:tram_rail_y", "Steam-Tramway Rail (NW-SE)", 1.0, 0.70, 0.52),
        ("iso_crosswalk", "proc:crosswalk", "High Street Flagstone Crosswalk", 1.0, 0.74, 0.56),
        ("iso_sidewalk", "tiles/stone_slab.png", "Sandstone Flagstone Sidewalk", 1.04, 0.76, 0.58),
        ("iso_stone_inset", "tiles/stone_inset.png", "Chancery Stone Inset Floor", 1.0, 0.74, 0.56),
        ("iso_stone_tile", "tiles/stone_tile.png", "Ashlar Dressed Stone Floor", 1.0, 0.74, 0.56),
        ("iso_stone_uneven", "tiles/stone_uneven.png", "Ancient Uneven Cobble", 1.0, 0.72, 0.54),
        ("iso_step_stone", "tiles/step_stone.png", "Dressed Limestone Slab", 1.02, 0.75, 0.56),
        ("iso_wood_planks", "tiles/wood_planks.png", "Tudor Polished Oak Planks", 1.0, 0.74, 0.55),
        ("iso_carpet_main", "tiles/carpet_main.png", "Ashford Crimson & Gold Runner", 1.05, 0.75, 0.58),
        ("iso_carpet_small", "tiles/carpet_small.png", "Parlour Woven Rug", 1.05, 0.75, 0.58),
        ("iso_door_threshold", "proc:door_threshold", "Threshold & Welcome Mat", 1.0, 0.76, 0.58),
        ("iso_gym_court", "proc:gym_court", "St. Dunstan's Fencing Court", 1.0, 0.75, 0.58),
        ("iso_water", "proc:water", "Severn Canal & Basin Water", 1.0, 0.80, 0.65),
    ]

    for tile_id, src_ref, label, bright, l_sh, r_sh in tile_specs:
        if src_ref.startswith("proc:"):
            tex = proc_tex[src_ref.split(":", 1)[1]]
        else:
            tex = tight_crop_opaque(load_src_image(src_root, src_ref))

        # 1. Flat 64x32 isometric diamond tile
        flat_img = project_top_diamond(tex, TILE_W, TILE_H, brightness=bright)
        flat_name = f"{tile_id}_flat.png"
        flat_img.save(tiles_dir / flat_name)

        # 2. 3D 64x48 isometric block tile (for elevated terrain or thick grid mode)
        side_tex = load_src_image(src_root, "tiles/stone_slab.png") if "carpet" in tile_id else tex
        block_img = make_iso_block(
            tex,
            side_tex=side_tex,
            tile_w=TILE_W,
            tile_h=TILE_H,
            block_h=BLOCK_H,
            left_shade=l_sh,
            right_shade=r_sh,
        )
        block_name = f"{tile_id}.png"
        block_img.save(tiles_dir / block_name)

        manifest.append({
            "id": tile_id,
            "label": label,
            "category": "tiles",
            "file": f"tiles/{block_name}",
            "flat_file": f"tiles/{flat_name}",
            "source": src_ref,
            "footprint": [1, 1],
        })

    return manifest


# ==============================================================================
# 4. GENERATE ISOMETRIC WALLS, COLUMNS, DOORS, STAIRS & FENCES
# ==============================================================================

def make_iso_wall_segment(
    wall_tex: Image.Image,
    orientation: str = "SW",
    wall_h: int = 56,
    thickness: int = 8,
) -> Image.Image:
    """Project a flat Dunwick wall sprite onto a 3D isometric wall segment with stone cap & depth."""
    canvas_w = TILE_W
    canvas_h = wall_h + TILE_H
    out = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))

    # Extract opaque region of source wall texture
    cropped = tight_crop_opaque(wall_tex)

    # Fill any transparent gaps (unless archway or open door) with warm stone mortar backing
    solid_wall = Image.new("RGBA", cropped.size, (96, 88, 76, 255))
    solid_wall.alpha_composite(cropped)
    cropped_wall = cropped if cropped.getbbox() else solid_wall

    half_w = TILE_W // 2  # 32 px wide along one isometric edge
    if orientation == "SW":
        # Runs along +X axis (top-left to bottom-right of tile)
        main_face = shear_wall_face(cropped, half_w, wall_h, direction="SW", shade=0.96)
        edge_face = shear_wall_face(cropped, thickness, wall_h, direction="SE", shade=0.62)
        out.alpha_composite(main_face, (12, 8))
        out.alpha_composite(edge_face, (12 + half_w, 8 + half_w // 2 - thickness // 2))
        # Top coping stone strip
        draw = ImageDraw.Draw(out)
        top_poly = [
            (12, 8),
            (12 + thickness, 8 - thickness // 2),
            (12 + half_w + thickness, 8 + half_w // 2 - thickness // 2),
            (12 + half_w, 8 + half_w // 2),
        ]
        draw.polygon(top_poly, fill=(135, 126, 114, 255), outline=(55, 50, 44, 220))
    else:
        # Runs along +Y axis (top-right to bottom-left of tile, facing SE)
        main_face = shear_wall_face(cropped, half_w, wall_h, direction="SE", shade=0.78)
        edge_face = shear_wall_face(cropped, thickness, wall_h, direction="SW", shade=0.92)
        out.alpha_composite(edge_face, (20 - thickness, 8 + half_w // 2 - thickness // 2))
        out.alpha_composite(main_face, (20, 8))
        draw = ImageDraw.Draw(out)
        top_poly = [
            (20 - thickness, 8 + half_w // 2 - thickness // 2),
            (20, 8 + half_w // 2),
            (20 + half_w, 8),
            (20 + half_w - thickness, 8 - thickness // 2),
        ]
        draw.polygon(top_poly, fill=(135, 126, 114, 255), outline=(55, 50, 44, 220))

    return out


def make_iso_iron_fence(orientation: str = "SW") -> Image.Image:
    """Create a 3D isometric Victorian wrought-iron & brass-finial estate fence."""
    out = Image.new("RGBA", (TILE_W, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(out)

    # Stone plinth base along isometric axis
    pts_sw = [(10, 32), (46, 50)]
    pts_se = [(54, 32), (18, 50)]
    p0, p1 = pts_sw if orientation == "SW" else pts_se

    # Base curb
    draw.line([p0, p1], fill=(115, 110, 102, 255), width=5)
    draw.line([(p0[0], p0[1] - 2), (p1[0], p1[1] - 2)], fill=(155, 148, 138, 255), width=2)

    # Top & bottom horizontal wrought-iron rails
    draw.line([(p0[0], p0[1] - 24), (p1[0], p1[1] - 24)], fill=(32, 36, 42, 255), width=2)
    draw.line([(p0[0], p0[1] - 8), (p1[0], p1[1] - 8)], fill=(32, 36, 42, 255), width=2)

    # Vertical iron pickets + gold spear finials
    steps = 7
    for i in range(steps + 1):
        t = i / steps
        px = int(p0[0] + (p1[0] - p0[0]) * t)
        py = int(p0[1] + (p1[1] - p0[1]) * t)
        is_post = i in (0, steps)
        w = 3 if is_post else 1
        h = 30 if is_post else 27
        draw.line([(px, py - 3), (px, py - h)], fill=(26, 30, 36, 255), width=w)
        # Brass spearhead finial
        draw.polygon(
            [(px, py - h - 4), (px - 2, py - h), (px + 2, py - h)],
            fill=(218, 178, 78, 255),
        )

    return out


def generate_iso_walls(src_root: Path, out_dir: Path) -> list[dict]:
    """Convert all flat Kenney Angle wall/column/stair sprites into isometric architectural sprites."""
    walls_dir = out_dir / "walls"
    walls_dir.mkdir(parents=True, exist_ok=True)
    manifest = []

    wall_specs = [
        ("iso_wall_stone", "props/wall_stone.png", "Tudor Ashlar Stone Wall", 56),
        ("iso_wall_aged", "props/wall_aged.png", "Weathered Sanctuary Wall", 56),
        ("iso_wall_window", "props/wall_window.png", "Lancet Stained-Glass Window Wall", 56),
        ("iso_wall_round_win", "props/wall_round_win.png", "Rose Oculus Window Wall", 56),
        ("iso_wall_window_bars", "props/wall_window_bars.png", "Constabulary Barred Window Wall", 56),
        ("iso_wall_books", "props/wall_books.png", "Library Recessed Book-Wall", 56),
        ("iso_wall_archway", "props/wall_archway.png", "Gothic Stone Archway", 56),
        ("iso_wall_door_closed", "props/wall_door_closed.png", "Heavy Oak Portal (Closed)", 56),
        ("iso_wall_door_open", "props/wall_door_open.png", "Heavy Oak Portal (Open)", 56),
        ("iso_wall_half", "props/wall_half.png", "Low Stone Parapet Wall", 34),
    ]

    for base_id, rel_src, label, wh in wall_specs:
        tex = load_src_image(src_root, rel_src)
        for orient in ("sw", "se"):
            img = make_iso_wall_segment(tex, orientation=orient.upper(), wall_h=wh)
            fname = f"{base_id}_{orient}.png"
            img.save(walls_dir / fname)
            manifest.append({
                "id": f"{base_id}_{orient}",
                "label": f"{label} ({orient.upper()})",
                "category": "walls",
                "file": f"walls/{fname}",
                "source": rel_src,
                "footprint": [1, 1],
            })

    # Columns, Beams & Stairs converted to 3D isometric architectural pillars/stairs
    special_specs = [
        ("iso_column_stone", "props/column_stone.png", "Gothic Stone Pillar"),
        ("iso_column_wood", "props/column_wood.png", "Tudor Oak Timber Pillar"),
        ("iso_support_beams", "props/support_beams.png", "Timber Arch Bracing"),
        ("iso_stairs_aged", "props/stairs_aged.png", "Isometric Stone Staircase"),
        ("iso_stairs_spiral", "props/stairs_spiral.png", "Clocktower Spiral Staircase"),
    ]
    for sp_id, rel_src, label in special_specs:
        src_img = load_src_image(src_root, rel_src)
        crop = tight_crop_opaque(src_img)

        out = Image.new("RGBA", (TILE_W, 84), (0, 0, 0, 0))
        # Render isometric stone plinth under pillar/stairs
        stone_tex = load_src_image(src_root, "tiles/stone_slab.png")
        plinth = make_iso_block(stone_tex, tile_w=40, tile_h=20, block_h=8)
        out.alpha_composite(plinth, ((TILE_W - 40) // 2, 84 - 28))

        if "column" in sp_id:
            # Create two perpendicular sheared faces for a true 3D square isometric pillar
            left_f = shear_wall_face(crop, 14, 58, direction="SW", shade=0.98)
            right_f = shear_wall_face(crop, 14, 58, direction="SE", shade=0.72)
            out.alpha_composite(left_f, (18, 10))
            out.alpha_composite(right_f, (32, 10))
        elif "stairs_aged" in sp_id:
            # Stepped 3D isometric staircase rising from SW to NE
            draw = ImageDraw.Draw(out)
            for step in range(6):
                sx = 14 + step * 4
                sy = 58 - step * 7
                step_blk = make_iso_block(stone_tex, tile_w=28, tile_h=14, block_h=6)
                out.alpha_composite(step_blk, (sx, sy))
        else:
            scaled = crop.resize((42, 62), Image.Resampling.BICUBIC)
            out.alpha_composite(scaled, ((TILE_W - 42) // 2, 8))

        fname = f"{sp_id}.png"
        out.save(walls_dir / fname)
        manifest.append({
            "id": sp_id,
            "label": label,
            "category": "walls",
            "file": f"walls/{fname}",
            "source": rel_src,
            "footprint": [1, 1],
        })

    # Wrought-iron estate fences (SW and SE)
    for orient in ("sw", "se"):
        fence_img = make_iso_iron_fence(orientation=orient.upper())
        fname = f"iso_fence_iron_{orient}.png"
        fence_img.save(walls_dir / fname)
        manifest.append({
            "id": f"iso_fence_iron_{orient}",
            "label": f"Wrought-Iron Estate Fence ({orient.upper()})",
            "category": "walls",
            "file": f"walls/{fname}",
            "source": "procedural:wrought_iron_fence",
            "footprint": [1, 1],
        })

    return manifest


# ==============================================================================
# 5. GENERATE ISOMETRIC 3D LANDMARK HOUSES (6 DUNWICK BUILDINGS)
# ==============================================================================

def create_iso_landmark_house(
    front_facade: Image.Image,
    stone_tex: Image.Image,
    wood_tex: Image.Image,
    roof_color: tuple[int, int, int],
    trim_color: tuple[int, int, int],
    has_clocktower: bool = False,
    has_awning: bool = False,
    awning_colors: tuple[tuple[int, int, int], tuple[int, int, int]] = ((165, 42, 42), (235, 220, 190)),
) -> Image.Image:
    """Build a multi-tile 3D isometric building (256x240) from Dunwick's flat house sprite."""
    W, H = 256, 240
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(out)

    # Crop opaque bounds of original flat building
    facade = tight_crop_opaque(front_facade)

    # Extract rectangular masonry/timber wall body and back it with solid Tudor stone/plaster
    fw, fh = facade.size
    raw_wall = facade.crop((int(fw * 0.08), int(fh * 0.44), int(fw * 0.92), int(fh * 0.96)))
    wall_crop = stone_tex.convert("RGBA").resize(raw_wall.size, Image.Resampling.BICUBIC)
    wall_crop.alpha_composite(raw_wall)

    # Isometric footprint center near bottom
    cx, cy = 128, 212
    left_w = 88   # SW main facade width
    right_w = 76  # SE side wall width
    wall_h = 82

    # 1. Isometric Stone Foundation Plinth
    plinth_pts = [
        (cx - left_w, cy - left_w // 2 + 4),
        (cx, cy + 4),
        (cx + right_w, cy - right_w // 2 + 4),
        (cx + right_w - left_w, cy - (left_w + right_w) // 2 + 4),
    ]
    draw.polygon(plinth_pts, fill=(72, 68, 64, 255), outline=(35, 32, 30, 255))

    # 2. SW Front Facade (sheared from actual Dunwick house texture!)
    sw_wall = shear_wall_face(wall_crop, left_w, wall_h, direction="SW", shade=1.0)
    out.alpha_composite(sw_wall, (cx - left_w, cy - left_w // 2 - wall_h))

    # 3. SE Side Wall (sheared from wall_crop with deeper shadow for 3D volume)
    se_wall = shear_wall_face(wall_crop, right_w, wall_h, direction="SE", shade=0.72)
    out.alpha_composite(se_wall, (cx, cy - right_w // 2 - wall_h))

    # 4. Tudor Timber Corner Posts & Eaves Trim
    top_front = (cx, cy - wall_h)
    top_left = (cx - left_w, cy - left_w // 2 - wall_h)
    top_right = (cx + right_w, cy - right_w // 2 - wall_h)
    top_back = (cx + right_w - left_w, cy - (left_w + right_w) // 2 - wall_h)

    # Fill top ceiling plane under roof so there is never an internal gap
    draw.polygon([top_left, top_front, top_right, top_back], fill=(42, 36, 32, 255))

    draw.line([top_left, (cx - left_w, cy - left_w // 2)], fill=trim_color, width=3)
    draw.line([top_front, (cx, cy)], fill=trim_color, width=4)
    draw.line([top_right, (cx + right_w, cy - right_w // 2)], fill=trim_color, width=3)

    # 5. Pitched 3D Isometric Gabled Roof
    ridge_h = 46
    # Ridge runs parallel to SW face (along X axis)
    ridge_front = (cx + right_w // 2, cy - right_w // 4 - wall_h - ridge_h)
    ridge_back = (
        cx + right_w // 2 - left_w,
        cy - right_w // 4 - left_w // 2 - wall_h - ridge_h,
    )

    # Front-left roof slope (brightest)
    r_r, r_g, r_b = roof_color
    slope_sw = [top_left, top_front, ridge_front, ridge_back]
    draw.polygon(slope_sw, fill=(r_r, r_g, r_b, 255), outline=(28, 24, 22, 255))

    # Shingle tile courses on SW roof slope
    for s in range(1, 7):
        t = s / 7.0
        lx = int(top_left[0] + (ridge_back[0] - top_left[0]) * t)
        ly = int(top_left[1] + (ridge_back[1] - top_left[1]) * t)
        rx = int(top_front[0] + (ridge_front[0] - top_front[0]) * t)
        ry = int(top_front[1] + (ridge_front[1] - top_front[1]) * t)
        draw.line([(lx, ly), (rx, ry)], fill=(max(0, r_r - 24), max(0, r_g - 24), max(0, r_b - 24), 210), width=1)

    # SE Gable Triangle + Side Roof Slope
    gable_se = [top_front, top_right, ridge_front]
    draw.polygon(
        gable_se,
        fill=(int(r_r * 0.72), int(r_g * 0.72), int(r_b * 0.72), 255),
        outline=trim_color,
    )
    # Copper/brass ridge cresting
    draw.line([ridge_back, ridge_front], fill=(195, 162, 88, 255), width=3)
    draw.line([top_left, top_front, top_right], fill=trim_color, width=3)

    # 6. Brick & Copper Steampunk Chimneys
    for ch_offset in (0.25, 0.78):
        ch_x = int(ridge_back[0] + (ridge_front[0] - ridge_back[0]) * ch_offset)
        ch_y = int(ridge_back[1] + (ridge_front[1] - ridge_back[1]) * ch_offset)
        draw.rectangle([ch_x - 6, ch_y - 18, ch_x + 6, ch_y + 4], fill=(128, 64, 52, 255), outline=(45, 28, 24, 255))
        draw.rectangle([ch_x - 8, ch_y - 21, ch_x + 8, ch_y - 17], fill=(188, 145, 78, 255))

    # 7. Optional Market / Teahouse Striped Awning over SW Facade
    if has_awning:
        c1, c2 = awning_colors
        for i in range(8):
            ax0 = cx - left_w + 8 + i * 9
            ay0 = cy - left_w // 2 - 34 + (i * 9) // 2
            stripe_col = c1 if i % 2 == 0 else c2
            pts = [
                (ax0, ay0),
                (ax0 + 9, ay0 + 4),
                (ax0 + 3, ay0 + 14),
                (ax0 - 6, ay0 + 10),
            ]
            draw.polygon(pts, fill=(*stripe_col, 255), outline=(35, 28, 24, 180))

    # 8. Optional Borough Foundry Brass Clocktower & Copper Spire
    if has_clocktower:
        tx, ty = ridge_front[0] - 18, ridge_front[1] + 6
        tw, th = 28, 52
        # Left & right tower faces
        draw.polygon(
            [(tx - tw, ty - tw // 2), (tx, ty), (tx, ty - th), (tx - tw, ty - tw // 2 - th)],
            fill=(118, 108, 96, 255),
            outline=(45, 40, 35, 255),
        )
        draw.polygon(
            [(tx, ty), (tx + tw, ty - tw // 2), (tx + tw, ty - tw // 2 - th), (tx, ty - th)],
            fill=(86, 78, 70, 255),
            outline=(45, 40, 35, 255),
        )
        # Illuminated Brass Clock Dials on both isometric faces
        draw.ellipse([tx - tw + 6, ty - th + 6, tx - 6, ty - th + 24], fill=(245, 232, 188, 255), outline=(195, 150, 62, 255), width=2)
        draw.line([(tx - tw // 2, ty - th + 15), (tx - tw // 2, ty - th + 9)], fill=(25, 25, 30, 255), width=2)
        draw.ellipse([tx + 6, ty - th + 6, tx + tw - 6, ty - th + 24], fill=(215, 202, 162, 255), outline=(165, 125, 52, 255), width=2)
        # Verdigris Copper Spire
        spire_top = (tx, ty - th - 34)
        draw.polygon([(tx - tw, ty - tw // 2 - th), (tx, ty - th), spire_top], fill=(72, 138, 122, 255), outline=(35, 68, 60, 255))
        draw.polygon([(tx, ty - th), (tx + tw, ty - tw // 2 - th), spire_top], fill=(54, 108, 95, 255), outline=(35, 68, 60, 255))

    return out


def generate_iso_houses(src_root: Path, out_dir: Path) -> list[dict]:
    """Generate 3D isometric landmark buildings for all 6 Dunwick houses."""
    houses_dir = out_dir / "houses"
    houses_dir.mkdir(parents=True, exist_ok=True)
    stone_tex = load_src_image(src_root, "tiles/stone_tile.png")
    wood_tex = load_src_image(src_root, "tiles/wood_planks.png")

    house_specs = [
        (
            "iso_house_home",
            "houses/house_home.png",
            "Ashford-Mercer Tudor Manor",
            (118, 56, 48),
            (58, 40, 28),
            False,
            False,
            ((165, 42, 42), (235, 220, 190)),
        ),
        (
            "iso_house_cafe",
            "houses/house_cafe.png",
            "The Brass Kettle Teahouse",
            (72, 96, 84),
            (64, 44, 30),
            False,
            True,
            ((158, 44, 42), (240, 228, 198)),
        ),
        (
            "iso_house_office",
            "houses/house_office.png",
            "Borough Foundry & Clocktower",
            (64, 72, 84),
            (48, 52, 58),
            True,
            False,
            ((165, 42, 42), (235, 220, 190)),
        ),
        (
            "iso_house_school",
            "houses/house_school.png",
            "St. Dunstan's Polytechnic",
            (108, 62, 46),
            (68, 52, 38),
            False,
            False,
            ((165, 42, 42), (235, 220, 190)),
        ),
        (
            "iso_house_market",
            "houses/house_market.png",
            "Guildhall Bazaar & Apothecary",
            (124, 78, 44),
            (62, 42, 28),
            False,
            True,
            ((46, 112, 78), (238, 222, 185)),
        ),
        (
            "iso_house_park",
            "houses/house_park.png",
            "Severn Commons & Constabulary",
            (58, 76, 92),
            (48, 54, 64),
            False,
            False,
            ((165, 42, 42), (235, 220, 190)),
        ),
    ]

    manifest = []
    for h_id, rel_src, label, roof_col, trim_col, clock, awning, aw_cols in house_specs:
        facade = load_src_image(src_root, rel_src)
        iso_house = create_iso_landmark_house(
            facade,
            stone_tex,
            wood_tex,
            roof_color=roof_col,
            trim_color=trim_col,
            has_clocktower=clock,
            has_awning=awning,
            awning_colors=aw_cols,
        )
        fname = f"{h_id}.png"
        iso_house.save(houses_dir / fname)
        manifest.append({
            "id": h_id,
            "label": label,
            "category": "houses",
            "file": f"houses/{fname}",
            "source": rel_src,
            "footprint": [3, 3],
        })

    return manifest


# ==============================================================================
# 6. GENERATE ISOMETRIC PROPS, FURNITURE & QUEST STATIONS
# ==============================================================================

def draw_iso_box(
    draw: ImageDraw.ImageDraw,
    cx: int,
    cy: int,
    rx: int,
    ry: int,
    h: int,
    top_col: tuple[int, int, int],
    left_col: tuple[int, int, int],
    right_col: tuple[int, int, int],
    outline: tuple[int, int, int] = (28, 24, 20),
) -> None:
    """Draw a 3D isometric box centered at bottom-front corner (cx, cy) with half-spans rx, ry and height h."""
    # Bottom vertices
    b_front = (cx, cy)
    b_left = (cx - rx, cy - rx // 2)
    b_right = (cx + ry, cy - ry // 2)
    b_back = (cx - rx + ry, cy - (rx + ry) // 2)

    # Top vertices
    t_front = (b_front[0], b_front[1] - h)
    t_left = (b_left[0], b_left[1] - h)
    t_right = (b_right[0], b_right[1] - h)
    t_back = (b_back[0], b_back[1] - h)

    # Left face (SW)
    draw.polygon([t_left, t_front, b_front, b_left], fill=(*left_col, 255), outline=(*outline, 220))
    # Right face (SE)
    draw.polygon([t_front, t_right, b_right, b_front], fill=(*right_col, 255), outline=(*outline, 220))
    # Top face
    draw.polygon([t_back, t_right, t_front, t_left], fill=(*top_col, 255), outline=(*outline, 220))


def draw_iso_cylinder(
    draw: ImageDraw.ImageDraw,
    cx: int,
    cy: int,
    rx: int,
    ry: int,
    h: int,
    top_col: tuple[int, int, int],
    body_col: tuple[int, int, int],
    band_col: Optional[tuple[int, int, int]] = None,
) -> None:
    """Draw a 3D vertical cylinder in isometric view with optional iron/brass hoops."""
    # Body rectangle + bottom ellipse
    draw.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=(*body_col, 255), outline=(25, 22, 18, 230))
    draw.rectangle([cx - rx, cy - h, cx + rx, cy], fill=(*body_col, 255))
    draw.line([(cx - rx, cy - h), (cx - rx, cy)], fill=(25, 22, 18, 230), width=1)
    draw.line([(cx + rx, cy - h), (cx + rx, cy)], fill=(25, 22, 18, 230), width=1)

    if band_col:
        for bh in (int(h * 0.28), int(h * 0.72)):
            draw.arc([cx - rx, cy - bh - ry, cx + rx, cy - bh + ry], start=0, end=180, fill=(*band_col, 255), width=2)

    # Top ellipse
    draw.ellipse([cx - rx, cy - h - ry, cx + rx, cy - h + ry], fill=(*top_col, 255), outline=(25, 22, 18, 230))


def convert_flat_prop_to_iso_3d(
    src_img: Image.Image,
    prop_id: str,
    wood_tex: Image.Image,
    stone_tex: Image.Image,
) -> Image.Image:
    """Convert a non-isometric Kenney Angle prop into a 3D isometric prop on a diamond footprint."""
    out = Image.new("RGBA", (80, 88), (0, 0, 0, 0))
    draw = ImageDraw.Draw(out)

    # Subtle ambient contact shadow on the isometric ground diamond
    draw.ellipse([18, 54, 62, 76], fill=(12, 14, 18, 95))

    crop = tight_crop_opaque(src_img)

    if "bookcase" in prop_id or "display" in prop_id:
        # True 3D isometric cabinet/bookcase: sheared front face + 3D oak side & top
        front_w, front_h = 34, 48 if "half" not in prop_id else 30
        depth_w = 14
        front_sheared = shear_wall_face(crop, front_w, front_h, direction="SW", shade=0.98)
        side_sheared = shear_wall_face(wood_tex, depth_w, front_h, direction="SE", shade=0.65)
        bx, by = 18, 66 - front_h
        out.alpha_composite(front_sheared, (bx, by))
        out.alpha_composite(side_sheared, (bx + front_w, by + front_w // 2 - depth_w // 2))
        # Isometric oak top lid
        top_pts = [
            (bx, by),
            (bx + depth_w, by - depth_w // 2),
            (bx + front_w + depth_w, by + front_w // 2 - depth_w // 2),
            (bx + front_w, by + front_w // 2),
        ]
        draw.polygon(top_pts, fill=(116, 82, 54, 255), outline=(42, 28, 18, 230))

    elif "long_table" in prop_id or "table_short" in prop_id:
        # 3D isometric oak banquet/study table
        cx, cy = 40, 68
        rx = 26 if "long" in prop_id else 18
        ry = 14
        # 4 isometric legs
        for lx, ly in ((cx - rx + 3, cy - rx // 2 + 2), (cx - 2, cy - 1), (cx + ry - 3, cy - ry // 2 + 2)):
            draw.rectangle([lx - 2, ly - 14, lx + 2, ly], fill=(74, 48, 32, 255))
        draw_iso_box(draw, cx, cy - 12, rx, ry, 5, (132, 92, 58), (98, 66, 42), (76, 50, 32))
        if "books" in prop_id:
            draw_iso_box(draw, cx - 6, cy - 17, 7, 5, 4, (168, 48, 44), (225, 215, 190), (125, 34, 32))
            draw_iso_box(draw, cx + 4, cy - 19, 6, 5, 3, (46, 88, 128), (225, 215, 190), (34, 64, 96))

    elif "table_round" in prop_id:
        cx, cy = 40, 66
        # Central turned oak pedestal + round isometric tabletop
        draw.rectangle([cx - 4, cy - 16, cx + 4, cy], fill=(78, 52, 34, 255))
        draw.ellipse([cx - 12, cy - 6, cx + 12, cy + 6], fill=(64, 42, 28, 255))
        draw_iso_cylinder(draw, cx, cy - 14, 20, 10, 4, (142, 98, 62), (96, 64, 40))
        if "items" in prop_id:
            draw_iso_cylinder(draw, cx - 4, cy - 18, 4, 2, 6, (215, 175, 80), (175, 135, 55))

    elif "barrel" in prop_id:
        cx, cy = 40, 66
        if "group" in prop_id or "stacked" in prop_id:
            draw_iso_cylinder(draw, cx - 10, cy - 4, 9, 5, 18, (138, 96, 62), (108, 72, 44), (48, 52, 58))
            draw_iso_cylinder(draw, cx + 8, cy - 2, 9, 5, 18, (138, 96, 62), (102, 68, 42), (48, 52, 58))
            if "stacked" in prop_id:
                draw_iso_cylinder(draw, cx - 1, cy - 18, 9, 5, 16, (148, 104, 68), (114, 78, 48), (48, 52, 58))
        else:
            draw_iso_cylinder(draw, cx, cy, 11, 6, 22, (138, 96, 62), (108, 72, 44), (48, 52, 58))

    elif "crate" in prop_id:
        cx, cy = 40, 68
        if "group" in prop_id:
            draw_iso_box(draw, cx - 8, cy - 2, 12, 12, 14, (152, 112, 72), (124, 88, 54), (96, 68, 42))
            draw_iso_box(draw, cx + 10, cy, 10, 10, 12, (144, 104, 66), (118, 82, 50), (90, 62, 38))
        else:
            draw_iso_box(draw, cx, cy, 14, 14, 16, (152, 112, 72), (124, 88, 54), (96, 68, 42))

    elif "chest" in prop_id:
        cx, cy = 40, 66
        draw_iso_box(draw, cx, cy, 16, 11, 12, (185, 148, 68), (112, 72, 44), (84, 52, 32))
        if "open" in prop_id:
            # Gold & brass treasures gleaming inside
            draw.ellipse([cx - 8, cy - 16, cx + 8, cy - 9], fill=(242, 202, 78, 255))

    elif "tree" in prop_id:
        # Place the lush tree canopy atop a 3D isometric stone/turf planter base
        planter = make_iso_block(stone_tex, tile_w=44, tile_h=22, block_h=8)
        out.alpha_composite(planter, (18, 52))
        tree_s = crop.resize((64, 64), Image.Resampling.BICUBIC)
        out.alpha_composite(tree_s, (8, 4))

    else:
        # Generic 3D isometric pedestal + prop sprite
        ped = make_iso_block(wood_tex, tile_w=36, tile_h=18, block_h=6)
        out.alpha_composite(ped, (22, 54))
        w = min(52, max(24, crop.width))
        h = min(56, max(24, crop.height))
        scaled = crop.resize((w, h), Image.Resampling.BICUBIC)
        out.alpha_composite(scaled, ((80 - w) // 2, 62 - h))

    return out


def generate_procedural_quest_and_furniture_sprites(out_dir: Path) -> list[dict]:
    """Generate true 3D isometric sprites for all Dunwick procedural 2D furniture & quest stations."""
    furn_dir = out_dir / "furniture"
    quest_dir = out_dir / "quests"
    furn_dir.mkdir(parents=True, exist_ok=True)
    quest_dir.mkdir(parents=True, exist_ok=True)

    manifest = []

    # --- 1. Chesterfield Tufted Leather Parlour Sofa ---
    sofa = Image.new("RGBA", (80, 72), (0, 0, 0, 0))
    d = ImageDraw.Draw(sofa)
    d.ellipse([12, 42, 68, 66], fill=(12, 14, 18, 90))
    # Seat cushion (burgundy leather)
    draw_iso_box(d, 40, 58, 24, 14, 10, (128, 42, 46), (98, 30, 34), (76, 22, 26))
    # Backrest & rolled armrests
    draw_iso_box(d, 46, 52, 24, 5, 22, (142, 48, 52), (108, 34, 38), (84, 26, 30))
    draw_iso_box(d, 20, 48, 5, 14, 16, (136, 45, 48), (102, 32, 36), (80, 24, 28))
    draw_iso_box(d, 40, 58, 5, 14, 16, (136, 45, 48), (102, 32, 36), (80, 24, 28))
    sofa.save(furn_dir / "iso_chesterfield_sofa.png")
    manifest.append({
        "id": "iso_chesterfield_sofa",
        "label": "Chesterfield Tufted Parlour Sofa",
        "category": "furniture",
        "file": "furniture/iso_chesterfield_sofa.png",
        "source": "art_engine_25d:draw_sofa",
        "footprint": [2, 1],
    })

    # --- 2. Victorian Cast-Iron Coal Range & Copper Kettle ---
    stove = Image.new("RGBA", (80, 84), (0, 0, 0, 0))
    d = ImageDraw.Draw(stove)
    d.ellipse([16, 52, 64, 74], fill=(12, 14, 18, 95))
    draw_iso_box(d, 40, 66, 20, 16, 22, (46, 50, 58), (34, 38, 44), (26, 28, 34))
    # Glowing coal firebox grate on SW face
    d.polygon([(24, 50), (36, 56), (36, 62), (24, 56)], fill=(245, 125, 38, 255), outline=(185, 145, 65, 255))
    # Copper kettle & iron flue pipe
    draw_iso_cylinder(d, 34, 42, 6, 3, 8, (215, 138, 72), (182, 108, 52))
    draw_iso_cylinder(d, 48, 40, 5, 3, 28, (58, 62, 70), (38, 42, 48))
    stove.save(furn_dir / "iso_victorian_coal_range.png")
    manifest.append({
        "id": "iso_victorian_coal_range",
        "label": "Victorian Cast-Iron Coal Range",
        "category": "furniture",
        "file": "furniture/iso_victorian_coal_range.png",
        "source": "art_engine_25d:draw_kitchen_island",
        "footprint": [1, 1],
    })

    # --- 3. Victorian Brass Street Gaslamp ---
    lamp = Image.new("RGBA", (64, 96), (0, 0, 0, 0))
    d = ImageDraw.Draw(lamp)
    d.ellipse([18, 72, 46, 88], fill=(245, 205, 110, 55))
    draw_iso_cylinder(d, 32, 82, 7, 4, 10, (54, 58, 66), (36, 40, 46))
    d.line([(32, 74), (32, 26)], fill=(38, 42, 48, 255), width=3)
    d.line([(26, 32), (38, 32)], fill=(195, 158, 72, 255), width=2)
    # Warm glowing amber glass lantern
    d.ellipse([20, 10, 44, 32], fill=(255, 215, 115, 90))
    draw_iso_box(d, 32, 28, 6, 6, 12, (52, 56, 64), (255, 228, 145), (235, 192, 95))
    lamp.save(furn_dir / "iso_street_gaslamp.png")
    manifest.append({
        "id": "iso_street_gaslamp",
        "label": "Victorian Brass Street Gaslamp",
        "category": "furniture",
        "file": "furniture/iso_street_gaslamp.png",
        "source": "art_engine_25d:draw_street_lamp",
        "footprint": [1, 1],
    })

    # --- 4. Sculpted Topiary Estate Hedge ---
    hedge = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(hedge)
    draw_iso_box(d, 32, 56, 18, 18, 6, (124, 118, 108), (96, 90, 82), (76, 72, 66))
    draw_iso_box(d, 32, 50, 16, 16, 22, (62, 98, 54), (46, 76, 40), (34, 58, 30))
    hedge.save(furn_dir / "iso_topiary_hedge.png")
    manifest.append({
        "id": "iso_topiary_hedge",
        "label": "Sculpted Estate Topiary Hedge",
        "category": "furniture",
        "file": "furniture/iso_topiary_hedge.png",
        "source": "art_engine_25d:draw_hedge",
        "footprint": [1, 1],
    })

    # --- 5. Medieval Gargoyle Courtyard Fountain ---
    fount = Image.new("RGBA", (96, 96), (0, 0, 0, 0))
    d = ImageDraw.Draw(fount)
    draw_iso_cylinder(d, 48, 76, 34, 17, 10, (52, 112, 138), (118, 112, 104))
    draw_iso_cylinder(d, 48, 68, 10, 5, 24, (142, 136, 126), (104, 98, 90))
    draw_iso_cylinder(d, 48, 44, 18, 9, 6, (72, 148, 175), (124, 118, 108))
    # Cascading water arcs
    d.arc([32, 34, 64, 68], start=180, end=360, fill=(165, 225, 245, 210), width=2)
    fount.save(furn_dir / "iso_gargoyle_fountain.png")
    manifest.append({
        "id": "iso_gargoyle_fountain",
        "label": "Severn Gargoyle Courtyard Fountain",
        "category": "furniture",
        "file": "furniture/iso_gargoyle_fountain.png",
        "source": "art_engine_25d:draw_park_fountain",
        "footprint": [2, 2],
    })

    # --- 6. QUEST STATION: Copper Steam-Urn & Tea Bar (cafe_counter) ---
    cafe = Image.new("RGBA", (88, 88), (0, 0, 0, 0))
    d = ImageDraw.Draw(cafe)
    draw_iso_box(d, 44, 70, 26, 16, 20, (138, 92, 56), (98, 64, 38), (74, 48, 28))
    # Twin pressurized copper & brass espresso steam urns
    draw_iso_cylinder(d, 36, 48, 7, 4, 18, (225, 175, 85), (192, 112, 58), (235, 195, 95))
    draw_iso_cylinder(d, 52, 46, 6, 3, 15, (225, 175, 85), (192, 112, 58), (235, 195, 95))
    cafe.save(quest_dir / "iso_quest_cafe_counter.png")
    manifest.append({
        "id": "iso_quest_cafe_counter",
        "label": "Copper Steam-Urn & Tea Bar (Quest)",
        "category": "quests",
        "file": "quests/iso_quest_cafe_counter.png",
        "source": "art_engine_25d:draw_cafe_counter",
        "footprint": [2, 1],
    })

    # --- 7. QUEST STATION: Central Steam-Boiler & Clocktower Regulator (power_generator) ---
    boiler = Image.new("RGBA", (96, 104), (0, 0, 0, 0))
    d = ImageDraw.Draw(boiler)
    draw_iso_box(d, 48, 84, 28, 24, 8, (82, 78, 74), (62, 58, 54), (48, 44, 42))
    # Riveted copper boiler drum + brass flywheel & pressure gauge
    draw_iso_cylinder(d, 44, 74, 18, 9, 38, (205, 128, 68), (172, 98, 48), (225, 182, 82))
    # Glowing furnace viewport & steam gauge
    d.ellipse([36, 52, 50, 64], fill=(255, 155, 48, 255), outline=(215, 175, 75, 255), width=2)
    d.ellipse([54, 44, 68, 62], outline=(218, 178, 74, 255), width=3)
    boiler.save(quest_dir / "iso_quest_power_generator.png")
    manifest.append({
        "id": "iso_quest_power_generator",
        "label": "Central Steam-Boiler & Regulator (Quest)",
        "category": "quests",
        "file": "quests/iso_quest_power_generator.png",
        "source": "art_engine_25d:draw_power_generator",
        "footprint": [2, 2],
    })

    # --- 8. QUEST STATION: Galvanic & Alchemical Bench (school_lab_table) ---
    lab = Image.new("RGBA", (88, 88), (0, 0, 0, 0))
    d = ImageDraw.Draw(lab)
    draw_iso_box(d, 44, 70, 26, 16, 18, (64, 68, 74), (92, 62, 40), (70, 46, 28))
    # Glowing emerald & cyan alchemical retorts and brass Tesla coil
    draw_iso_cylinder(d, 34, 50, 5, 3, 12, (125, 245, 195), (65, 195, 145))
    draw_iso_cylinder(d, 46, 48, 4, 2, 16, (225, 185, 82), (175, 135, 55))
    draw_iso_cylinder(d, 56, 52, 5, 3, 10, (95, 195, 250), (55, 145, 215))
    lab.save(quest_dir / "iso_quest_school_lab_table.png")
    manifest.append({
        "id": "iso_quest_school_lab_table",
        "label": "Galvanic & Alchemical Bench (Quest)",
        "category": "quests",
        "file": "quests/iso_quest_school_lab_table.png",
        "source": "art_engine_25d:draw_school_lab",
        "footprint": [2, 1],
    })

    # --- 9. QUEST STATION: Apothecary & Tincture Counter (market_ledger) ---
    apoth = Image.new("RGBA", (88, 88), (0, 0, 0, 0))
    d = ImageDraw.Draw(apoth)
    draw_iso_box(d, 44, 70, 26, 16, 18, (118, 78, 48), (88, 56, 34), (68, 42, 26))
    # Brass balance scale + open merchant ledger + tincture jars
    draw_iso_box(d, 36, 51, 8, 6, 3, (240, 232, 205), (195, 182, 152), (145, 42, 38))
    d.line([(52, 50), (52, 36)], fill=(218, 178, 75, 255), width=2)
    d.line([(46, 38), (58, 38)], fill=(218, 178, 75, 255), width=2)
    apoth.save(quest_dir / "iso_quest_market_ledger.png")
    manifest.append({
        "id": "iso_quest_market_ledger",
        "label": "Apothecary & Merchant Ledger (Quest)",
        "category": "quests",
        "file": "quests/iso_quest_market_ledger.png",
        "source": "art_engine_25d:draw_market_stall",
        "footprint": [2, 1],
    })

    # --- 10. QUEST STATION: Scotland Yard Telegraph Desk (police_dispatch) ---
    police = Image.new("RGBA", (88, 88), (0, 0, 0, 0))
    d = ImageDraw.Draw(police)
    draw_iso_box(d, 44, 70, 24, 16, 18, (54, 78, 62), (86, 56, 36), (66, 42, 26))
    # Brass ticker-tape telegraph & blue constabulary lamp
    draw_iso_cylinder(d, 36, 50, 6, 3, 12, (85, 165, 245), (48, 105, 185))
    draw_iso_box(d, 50, 50, 7, 6, 8, (218, 178, 78), (175, 138, 54), (142, 108, 42))
    police.save(quest_dir / "iso_quest_police_dispatch.png")
    manifest.append({
        "id": "iso_quest_police_dispatch",
        "label": "Constabulary Telegraph Desk (Quest)",
        "category": "quests",
        "file": "quests/iso_quest_police_dispatch.png",
        "source": "art_engine_25d:draw_police_desk",
        "footprint": [2, 1],
    })

    # --- 11. QUEST STATION: Chancery Pneumatic & Drafting Desk (office_records) ---
    office = Image.new("RGBA", (88, 88), (0, 0, 0, 0))
    d = ImageDraw.Draw(office)
    draw_iso_box(d, 44, 70, 24, 16, 18, (128, 86, 52), (94, 62, 36), (72, 46, 28))
    # Brass pneumatic dispatch tube & blueprint scroll
    draw_iso_cylinder(d, 54, 48, 5, 3, 24, (218, 178, 78), (182, 142, 58))
    draw_iso_box(d, 38, 51, 9, 7, 2, (68, 118, 178), (52, 92, 142), (42, 74, 115))
    office.save(quest_dir / "iso_quest_office_records.png")
    manifest.append({
        "id": "iso_quest_office_records",
        "label": "Chancery Pneumatic & Drafting Desk (Quest)",
        "category": "quests",
        "file": "quests/iso_quest_office_records.png",
        "source": "art_engine_25d:draw_office_desk",
        "footprint": [2, 1],
    })

    # --- 12. QUEST STATION: Ashford Brass Orrery & Study Desk (study_notebook) ---
    study = Image.new("RGBA", (88, 88), (0, 0, 0, 0))
    d = ImageDraw.Draw(study)
    draw_iso_box(d, 44, 70, 24, 16, 18, (118, 44, 46), (88, 56, 36), (68, 42, 26))
    # Celestial brass armillary sphere / orrery + leather journal
    d.ellipse([38, 30, 58, 50], outline=(228, 188, 82, 255), width=2)
    d.ellipse([42, 34, 54, 46], outline=(198, 152, 62, 255), width=2)
    d.ellipse([46, 38, 50, 42], fill=(245, 208, 92, 255))
    study.save(quest_dir / "iso_quest_study_notebook.png")
    manifest.append({
        "id": "iso_quest_study_notebook",
        "label": "Ashford Brass Orrery & Study Desk (Quest)",
        "category": "quests",
        "file": "quests/iso_quest_study_notebook.png",
        "source": "art_engine_25d:draw_study_desk",
        "footprint": [2, 1],
    })

    return manifest


def generate_iso_props(src_root: Path, out_dir: Path) -> list[dict]:
    """Copy existing isometric props and convert all non-isometric props into 3D isometric props."""
    props_dir = out_dir / "props"
    props_dir.mkdir(parents=True, exist_ok=True)
    wood_tex = load_src_image(src_root, "tiles/wood_planks.png")
    stone_tex = load_src_image(src_root, "tiles/stone_slab.png")

    manifest = []

    # 1. Copy already-isometric Dunwick props (iso_* and lab_*)
    already_iso = [
        "iso_barrels.png",
        "iso_bookcase.png",
        "iso_crates.png",
        "iso_display.png",
        "iso_table_round.png",
        "lab_blue_comp.png",
        "lab_buttons.png",
        "lab_desk_pc.png",
        "lab_printer.png",
        "lab_red_comp.png",
        "lab_tan_comp.png",
        "lab_tape_hifi.png",
        "lab_tape_reel.png",
    ]
    for fname in already_iso:
        src_p = src_root / "props" / fname
        if src_p.exists():
            shutil.copy2(src_p, props_dir / fname)
            manifest.append({
                "id": fname.replace(".png", ""),
                "label": fname.replace(".png", "").replace("_", " ").title(),
                "category": "props",
                "file": f"props/{fname}",
                "source": f"props/{fname} (existing isometric)",
                "footprint": [1, 1],
            })

    # 2. Convert all non-isometric flat props into 3D isometric props
    flat_props = [
        "barrel_single.png",
        "barrels_group.png",
        "barrels_stacked.png",
        "book_stand.png",
        "bookcase_desk.png",
        "bookcase_glass.png",
        "bookcase_half.png",
        "bookcase_ladder.png",
        "bookcase_wide.png",
        "candle_double.png",
        "candle_single.png",
        "chair_single.png",
        "chest_closed.png",
        "chest_open.png",
        "crate_single.png",
        "crates_group.png",
        "display_books.png",
        "display_open.png",
        "display_sword.png",
        "long_table_books.png",
        "long_table_chairs.png",
        "long_table_plain.png",
        "paper_clutter.png",
        "table_round_chairs.png",
        "table_round_items.png",
        "table_short_chairs.png",
        "tree_hd2d.png",
        "wood_pile.png",
    ]

    for fname in flat_props:
        prop_id = f"iso_{fname.replace('.png', '')}"
        src_img = load_src_image(src_root, f"props/{fname}")
        iso_img = convert_flat_prop_to_iso_3d(src_img, prop_id, wood_tex, stone_tex)
        out_name = f"{prop_id}.png"
        iso_img.save(props_dir / out_name)
        manifest.append({
            "id": prop_id,
            "label": prop_id.replace("iso_", "").replace("_", " ").title(),
            "category": "props",
            "file": f"props/{out_name}",
            "source": f"props/{fname}",
            "footprint": [1, 1],
        })

    return manifest


# ==============================================================================
# 7. GENERATE ISOMETRIC 1924 STEAMPUNK VEHICLES (CARRIAGES & OMNI-TRAM)
# ==============================================================================

def create_iso_steampunk_vehicle(
    body_color: tuple[int, int, int],
    trim_color: tuple[int, int, int] = (218, 178, 78),
    is_tram: bool = False,
    direction: str = "SW",
) -> Image.Image:
    """Render a 3D isometric 1924 British Steampunk Steam-Carriage or Omni-Tram."""
    W, H = (128, 112) if is_tram else (96, 84)
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(out)

    cx, cy = W // 2, H - 18
    rx = (40 if is_tram else 26) if direction in ("SW", "NE") else (16 if is_tram else 14)
    ry = (16 if is_tram else 14) if direction in ("SW", "NE") else (40 if is_tram else 26)

    # Contact shadow
    draw.ellipse([cx - 36, cy - 20, cx + 36, cy + 8], fill=(12, 14, 18, 105))

    r, g, b = body_color
    top_c = (min(255, int(r * 1.15)), min(255, int(g * 1.15)), min(255, int(b * 1.15)))
    left_c = (r, g, b)
    right_c = (int(r * 0.72), int(g * 0.72), int(b * 0.72))

    # 1. Brass-spoked wheels along isometric chassis
    wheel_offsets = [(-rx + 6, -rx // 2 + 3), (-4, -2), (ry - 6, -ry // 2 + 3)]
    for wx_off, wy_off in wheel_offsets:
        wx, wy = cx + wx_off, cy + wy_off
        draw.ellipse([wx - 6, wy - 6, wx + 6, wy + 6], fill=(32, 34, 38, 255), outline=trim_color, width=2)

    # 2. Lower Coach Chassis
    chassis_h = 16 if is_tram else 12
    draw_iso_box(draw, cx, cy - 4, rx, ry, chassis_h, top_c, left_c, right_c)

    # 3. Upper Passenger Cabin with illuminatedclerestory windows
    cab_rx = int(rx * 0.76)
    cab_ry = int(ry * 0.76)
    cab_h = 18 if is_tram else 13
    draw_iso_box(
        draw,
        cx,
        cy - 4 - chassis_h,
        cab_rx,
        cab_ry,
        cab_h,
        (68, 52, 38),
        (235, 212, 142),
        (195, 172, 112),
    )

    # 4. Steampunk Copper Boiler Stack & Brass Headlamp
    draw_iso_cylinder(
        draw,
        cx - rx // 2,
        cy - 4 - chassis_h,
        4,
        2,
        18,
        trim_color,
        (184, 108, 52),
    )

    return out


def generate_iso_vehicles(src_root: Path, out_dir: Path) -> list[dict]:
    """Generate isometric directional sprites for all Dunwick vehicles."""
    veh_dir = out_dir / "vehicles"
    veh_dir.mkdir(parents=True, exist_ok=True)

    veh_specs = [
        ("iso_car_crimson", "vehicles/car_crimson.png", "Crimson Brass Steam-Carriage", (152, 38, 42), False),
        ("iso_car_emerald", "vehicles/car_emerald.png", "Emerald Brass Steam-Carriage", (38, 108, 68), False),
        ("iso_car_navy", "vehicles/car_navy.png", "Navy Brass Steam-Carriage", (42, 68, 124), False),
        ("iso_tram_amber", "vehicles/tram_amber.png", "Dunwick Amber Steam Omni-Tram", (196, 134, 44), True),
    ]

    manifest = []
    for v_id, rel_src, label, col, is_tram in veh_specs:
        for orient in ("sw", "se"):
            img = create_iso_steampunk_vehicle(col, is_tram=is_tram, direction=orient.upper())
            fname = f"{v_id}_{orient}.png"
            img.save(veh_dir / fname)
            manifest.append({
                "id": f"{v_id}_{orient}",
                "label": f"{label} ({orient.upper()})",
                "category": "vehicles",
                "file": f"vehicles/{fname}",
                "source": rel_src,
                "footprint": [2, 1] if orient == "sw" else [1, 2],
            })

    return manifest


# ==============================================================================
# 8. CONTACT SHEET GENERATOR FOR VISUAL VERIFICATION
# ==============================================================================

def build_contact_sheet(manifest: list[dict], out_dir: Path) -> Path:
    """Create a labeled visual contact sheet of generated isometric sprites."""
    cols = 8
    cell_w, cell_h = 110, 110
    rows = math.ceil(len(manifest) / cols)
    sheet = Image.new("RGBA", (cols * cell_w + 20, rows * cell_h + 20), (22, 25, 33, 255))
    draw = ImageDraw.Draw(sheet)

    for idx, item in enumerate(manifest):
        r = idx // cols
        c = idx % cols
        x0 = 10 + c * cell_w
        y0 = 10 + r * cell_h

        draw.rectangle([x0 + 2, y0 + 2, x0 + cell_w - 4, y0 + cell_h - 4], fill=(32, 37, 48, 255), outline=(58, 66, 84, 255))
        img_path = out_dir / item["file"]
        if img_path.exists():
            spr = Image.open(img_path).convert("RGBA")
            spr.thumbnail((76, 72), Image.Resampling.BICUBIC)
            sx = x0 + (cell_w - spr.width) // 2
            sy = y0 + 8 + (72 - spr.height) // 2
            sheet.alpha_composite(spr, (sx, sy))

        short_id = item["id"].replace("iso_", "")[:14]
        draw.text((x0 + 8, y0 + 86), short_id, fill=(210, 220, 235, 255))

    sheet_path = out_dir / "dunwick_iso_contact_sheet.png"
    sheet.save(sheet_path)
    return sheet_path


def generate_all() -> dict:
    """Run the full Dunwick -> IsoEngine isometric asset conversion pipeline."""
    src_root = get_source_dir()
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    manifest: list[dict] = []
    manifest.extend(generate_iso_tiles(src_root, OUTPUT_ROOT))
    manifest.extend(generate_iso_walls(src_root, OUTPUT_ROOT))
    manifest.extend(generate_iso_houses(src_root, OUTPUT_ROOT))
    manifest.extend(generate_iso_props(src_root, OUTPUT_ROOT))
    manifest.extend(generate_procedural_quest_and_furniture_sprites(OUTPUT_ROOT))
    manifest.extend(generate_iso_vehicles(src_root, OUTPUT_ROOT))

    sheet_path = build_contact_sheet(manifest, OUTPUT_ROOT)

    summary = {
        "total_sprites": len(manifest),
        "categories": {
            cat: sum(1 for m in manifest if m["category"] == cat)
            for cat in ("tiles", "walls", "houses", "props", "furniture", "quests", "vehicles")
        },
        "contact_sheet": str(sheet_path),
        "sprites": manifest,
    }

    manifest_path = OUTPUT_ROOT / "asset_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"Generated {len(manifest)} isometric Dunwick sprites in {OUTPUT_ROOT}")
    for cat, count in summary["categories"].items():
        print(f"  - {cat:10s}: {count} sprites")
    return summary


if __name__ == "__main__":
    generate_all()
