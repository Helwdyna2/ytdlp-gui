"""Centralized theme engine for the application."""

import logging
from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QApplication

from .tokens import DARK_TOKENS, LIGHT_TOKENS, FONT_BODY, FONT_MONO
from .qss_builder import build_qss

logger = logging.getLogger(__name__)


class ThemeEngine(QObject):
    """Singleton theme engine that manages dark/light QSS themes.

    Usage:
        engine = ThemeEngine()
        engine.apply_theme(app)  # Apply current theme
        engine.toggle_theme()    # Switch between dark/light
        engine.apply_theme(app)  # Re-apply after switch

        # Or set and apply in one step:
        engine.set_theme("light")
        engine.apply_theme(app)

        # Get current token values:
        color = engine.get_color("cyan")  # "#00d4ff" in dark mode
    """

    theme_changed = pyqtSignal(str)  # Emits "dark" or "light"

    _instance: Optional["ThemeEngine"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        super().__init__()
        self._initialized = True
        self._current_theme = "dark"
        self._tokens = {"dark": DARK_TOKENS, "light": LIGHT_TOKENS}

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
        tokens = self._tokens[self._current_theme]
        qss = build_qss(tokens, FONT_BODY, FONT_MONO)
        app.setStyleSheet(qss)
        logger.info(f"Applied {self._current_theme} theme ({len(qss)} chars QSS)")

    def get_color(self, key: str) -> str:
        """Get a color token value for the current theme."""
        return self._tokens[self._current_theme][key]

    def get_tokens(self) -> dict:
        """Get the full token dictionary for the current theme."""
        return dict(self._tokens[self._current_theme])
