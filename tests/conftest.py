"""Shared test fixtures for yt-dlp GUI."""
import sys

import pytest

pytest.importorskip("PyQt6.QtWidgets")


@pytest.fixture(scope="session")
def qapp():
    """Create or reuse a QApplication instance for the test session."""
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(sys.argv)
    yield app


@pytest.fixture(autouse=True)
def reset_theme_engine():
    """Reset ThemeEngine singleton between tests."""
    from src.ui.theme.theme_engine import ThemeEngine

    ThemeEngine._instance = None
    yield
    ThemeEngine._instance = None
