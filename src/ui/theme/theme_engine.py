"""Centralized theme engine for the Digital Obsidian design system."""

import logging
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QFontDatabase
from PyQt6.QtWidgets import QApplication

from .tokens import DARK_TOKENS, LIGHT_TOKENS, FONT_BODY, FONT_MONO, FONT_HEADLINE
from .qss_builder import build_qss

logger = logging.getLogger(__name__)

_FONTS_DIR = Path(__file__).parent / "fonts"


def _load_fonts() -> None:
    """Register bundled Manrope and Inter fonts with the Qt font database."""
    if not _FONTS_DIR.is_dir():
        logger.warning("Fonts directory not found: %s", _FONTS_DIR)
        return

    loaded = 0
    for font_file in sorted(_FONTS_DIR.iterdir()):
        if font_file.suffix.lower() in (".ttf", ".otf"):
            font_id = QFontDatabase.addApplicationFont(str(font_file))
            if font_id < 0:
                logger.warning("Failed to load font: %s", font_file.name)
            else:
                loaded += 1
    if loaded:
        logger.info("Loaded %d bundled fonts from %s", loaded, _FONTS_DIR)


class ThemeEngine(QObject):
    """Singleton theme engine that manages dark/light QSS themes.

    Usage:
        engine = ThemeEngine()
        engine.apply_theme(app)  # Apply current theme
        engine.toggle_theme()    # Switch between dark/light
        engine.apply_theme(app)  # Re-apply after switch

        # Get current token values:
        color = engine.get_color("primary")
    """

    theme_changed = pyqtSignal(str)  # Emits "dark" or "light"

    _instance: Optional["ThemeEngine"] = None
    _fonts_loaded: bool = False

    def __init__(self):
        super().__init__()
        self._current_theme = "dark"
        self._tokens = {"dark": DARK_TOKENS, "light": LIGHT_TOKENS}

    @classmethod
    def instance(cls) -> "ThemeEngine":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def current_theme(self) -> str:
        """Get the current theme name."""
        return self._current_theme

    def set_theme(self, theme: str) -> None:
        """Set the theme. Emits theme_changed if theme actually changes."""
        if theme not in ("dark", "light"):
            raise ValueError(f"Invalid theme: {theme}. Must be 'dark' or 'light'.")
        if theme != self._current_theme:
            self._current_theme = theme
            self.theme_changed.emit(theme)

    def toggle_theme(self) -> None:
        """Toggle between dark and light themes."""
        self.set_theme("light" if self._current_theme == "dark" else "dark")

    def apply_theme(self, app: QApplication) -> None:
        """Generate QSS from current theme tokens and apply to the application."""
        # Load bundled fonts once
        if not ThemeEngine._fonts_loaded:
            _load_fonts()
            ThemeEngine._fonts_loaded = True

        tokens = self._tokens[self._current_theme]
        qss = build_qss(tokens, FONT_BODY, FONT_MONO, font_headline=FONT_HEADLINE)
        app.setStyleSheet(qss)
        logger.info(f"Applied {self._current_theme} theme ({len(qss)} chars QSS)")

    def get_color(self, key: str) -> str:
        """Get a color token value for the current theme."""
        return self._tokens[self._current_theme][key]

    def get_tokens(self) -> dict:
        """Get the full token dictionary for the current theme."""
        return dict(self._tokens[self._current_theme])
