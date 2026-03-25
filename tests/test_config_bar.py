"""Tests for ConfigBar component."""
import pytest
import sys

pytest.importorskip("PyQt6.QtWidgets")


@pytest.fixture(autouse=True)
def reset_singleton():
    from src.ui.theme.theme_engine import ThemeEngine
    ThemeEngine._instance = None
    yield
    ThemeEngine._instance = None


@pytest.fixture
def qapp():
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


def test_config_bar_creates(qapp):
    from src.ui.components.config_bar import ConfigBar
    bar = ConfigBar()
    assert bar is not None


def test_config_bar_add_field(qapp):
    from PyQt6.QtWidgets import QLineEdit
    from src.ui.components.config_bar import ConfigBar
    bar = ConfigBar()
    bar.add_field("Label", QLineEdit())
    # Should not crash
