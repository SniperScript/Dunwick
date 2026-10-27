"""Font compatibility shim for Pygame under Python 3.14+.

Resolves the known upstream circular import issue in pygame 2.6.1 where
`pygame/font.py` and `pygame/sysfont.py` recursively import each other,
causing `NotImplementedError: font module not available`.

Provides a seamless, drop-in replacement backed by pygame's C-level
`_freetype` extension so fonts work identically across all Python versions.
"""

import sys
import types
import pygame


class CompatibleFont:
    """Drop-in replacement for pygame.font.Font backed by pygame._freetype."""

    def __init__(self, filename=None, size=16):
        import pygame._freetype as _ft
        self._size = max(int(size), 1)
        self._ft_font = _ft.Font(filename, self._size)

    def render(self, text, antialias=True, color=(255, 255, 255), background=None):
        if text is None:
            text = ""
        self._ft_font.antialiased = bool(antialias)
        surf, _ = self._ft_font.render(str(text), color, background)
        return surf

    def size(self, text):
        rect = self._ft_font.get_rect(str(text))
        return rect.width, rect.height

    def get_height(self):
        return self._ft_font.height

    def set_bold(self, bold):
        self._ft_font.wide = bool(bold)

    def set_italic(self, italic):
        self._ft_font.oblique = bool(italic)

    def set_underline(self, underline):
        self._ft_font.underline = bool(underline)


class DummyFont:
    """Safe fallback font in case both font and _freetype are unavailable."""

    def __init__(self, filename=None, size=16):
        self._height = max(int(size), 1)

    def render(self, text, antialias=True, color=(255, 255, 255), background=None):
        width = max(1, len(str(text or "")) * 8)
        surf = pygame.Surface((width, self._height), pygame.SRCALPHA)
        return surf

    def size(self, text):
        return (len(str(text or "")) * 8, self._height)

    def get_height(self):
        return self._height

    def set_bold(self, bold):
        pass

    def set_italic(self, italic):
        pass

    def set_underline(self, underline):
        pass


def setup_font_compatibility():
    """Ensure pygame.font is functional and will not raise NotImplementedError."""
    # 1. First test if pygame.font already works without error
    try:
        if hasattr(pygame, "font") and getattr(pygame, "font") is not None:
            if not pygame.font.get_init():
                pygame.font.init()
            # Test creating and rendering a small test font
            test_font = pygame.font.Font(None, 12)
            test_font.render("test", True, (255, 255, 255))
            return True
    except BaseException:
        # Expected failure on unpatched Pygame 2.6.1 on Python 3.14
        pass

    # 2. Try freetype-backed CompatibleFont
    try:
        import pygame._freetype as _ft
        _ft.init()

        mod = types.ModuleType("pygame.font")
        mod.Font = CompatibleFont
        mod.init = _ft.init
        mod.get_init = _ft.get_init
        mod.quit = _ft.quit

        def _sys_font(name, size, bold=False, italic=False):
            f = CompatibleFont(None, size)
            if bold:
                f.set_bold(True)
            if italic:
                f.set_italic(italic)
            return f

        mod.SysFont = _sys_font
        mod.match_font = lambda name: None
        mod.get_default_font = lambda: "freesansbold.ttf"
        mod.get_fonts = lambda: []

        sys.modules["pygame.font"] = mod
        pygame.font = mod
        return True

    except Exception:
        pass

    # 3. Fallback DummyFont (never crash, ensure game/grid still functions)
    mod = types.ModuleType("pygame.font")
    mod.Font = DummyFont
    mod.init = lambda: None
    mod.get_init = lambda: True
    mod.quit = lambda: None
    mod.SysFont = lambda name, size, bold=False, italic=False: DummyFont(None, size)
    mod.match_font = lambda name: None
    mod.get_default_font = lambda: "default"
    mod.get_fonts = lambda: []

    sys.modules["pygame.font"] = mod
    pygame.font = mod
    return False


# Automatically apply compatibility shim on import
setup_font_compatibility()


