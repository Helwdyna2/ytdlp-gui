"""Tests for Sidebar component."""
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


def test_sidebar_creates(qapp):
    from src.ui.components.sidebar import Sidebar
    sb = Sidebar()
    assert sb is not None


def test_sidebar_has_nav_items(qapp):
    from src.ui.components.sidebar import Sidebar
    sb = Sidebar()
    assert sb.item_count() >= 9


def test_sidebar_emits_tool_selected(qapp):
    from src.ui.components.sidebar import Sidebar
    sb = Sidebar()
    received = []
    sb.tool_selected.connect(lambda key: received.append(key))
    sb.select_tool("convert")
    assert received == ["convert"]


def test_sidebar_set_badge(qapp):
    from src.ui.components.sidebar import Sidebar
    sb = Sidebar()
    sb.set_badge("add_urls", 3)
    # Should not crash; badge is visual
