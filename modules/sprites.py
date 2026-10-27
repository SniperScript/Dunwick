"""Isometric Sprite Library & Asset Loader for IsoEngine (Dunwick Integration)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional
import pygame


ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets" / "iso_sprites"

CATEGORIES = [
    "tiles",
    "walls",
    "houses",
    "props",
    "furniture",
    "quests",
    "vehicles",
]


class IsometricSpriteLibrary:
    """Loads, caches, and scales Dunwick 2:1 isometric tile and object sprites."""

    def __init__(self, assets_dir: Path = ASSETS_DIR) -> None:
        self.assets_dir = assets_dir
        self.manifest: dict[str, dict] = {}
        self.by_category: dict[str, list[str]] = {c: [] for c in CATEGORIES}
        self._surfaces: dict[str, pygame.Surface] = {}
        self._flat_tile_surfaces: dict[str, pygame.Surface] = {}
        self._scaled_cache: dict[tuple[str, int, int], pygame.Surface] = {}

        self.load_manifest()

    def load_manifest(self) -> None:
        """Load asset_manifest.json and index all isometric sprites by ID and category."""
        manifest_path = self.assets_dir / "asset_manifest.json"
        if not manifest_path.exists():
            return

        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for entry in data.get("sprites", []):
            spr_id = entry["id"]
            cat = entry.get("category", "props")
            self.manifest[spr_id] = entry
            if cat not in self.by_category:
                self.by_category[cat] = []
            self.by_category[cat].append(spr_id)

    def get_surface(self, sprite_id: str, flat_tile: bool = False) -> Optional[pygame.Surface]:
        """Lazy-load and return the original Pygame RGBA surface for a sprite_id."""
        if flat_tile and sprite_id in self._flat_tile_surfaces:
            return self._flat_tile_surfaces[sprite_id]
        if not flat_tile and sprite_id in self._surfaces:
            return self._surfaces[sprite_id]

        entry = self.manifest.get(sprite_id)
        if not entry:
            return None

        rel_key = "flat_file" if (flat_tile and "flat_file" in entry) else "file"
        img_path = self.assets_dir / entry[rel_key]
        if not img_path.exists():
            return None

        try:
            surf = pygame.image.load(str(img_path)).convert_alpha()
        except Exception:
            from PIL import Image
            pil_img = Image.open(img_path).convert("RGBA")
            surf = pygame.image.frombytes(pil_img.tobytes(), pil_img.size, "RGBA")

        if flat_tile:
            self._flat_tile_surfaces[sprite_id] = surf
        else:
            self._surfaces[sprite_id] = surf
        return surf

    def get_scaled(
        self,
        sprite_id: str,
        zoom: float,
        flat_tile: bool = False,
    ) -> Optional[pygame.Surface]:
        """Return a zoom-scaled Pygame surface with caching."""
        base = self.get_surface(sprite_id, flat_tile=flat_tile)
        if base is None:
            return None

        target_w = max(1, int(round(base.get_width() * zoom)))
        target_h = max(1, int(round(base.get_height() * zoom)))
        if target_w == base.get_width() and target_h == base.get_height():
            return base

        cache_key = (f"{sprite_id}_flat" if flat_tile else sprite_id, target_w, target_h)
        if cache_key not in self._scaled_cache:
            # Keep cache bounded
            if len(self._scaled_cache) > 1200:
                self._scaled_cache.clear()
            self._scaled_cache[cache_key] = pygame.transform.smoothscale(base, (target_w, target_h))

        return self._scaled_cache[cache_key]

    def get_label(self, sprite_id: str) -> str:
        """Return human-readable label for sprite_id."""
        entry = self.manifest.get(sprite_id)
        if entry and "label" in entry:
            return entry["label"]
        return sprite_id.replace("iso_", "").replace("_", " ").title()
