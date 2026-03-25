"""Tests for SplitLayout component."""
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


def test_split_layout_creates(qapp):
    from src.ui.components.split_layout import SplitLayout
    sl = SplitLayout()
    assert sl.left_panel is not None
    assert sl.right_panel is not None


def test_split_layout_right_width(qapp):
    from src.ui.components.split_layout import SplitLayout
    sl = SplitLayout(right_width=260)
    assert sl.right_panel.maximumWidth() == 260
