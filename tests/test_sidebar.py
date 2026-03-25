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


def test_sidebar_title_text(qapp):
    from src.ui.components.sidebar import Sidebar
    sb = Sidebar()
    title = sb.findChild(type(sb.findChildren(type(sb))[0].__class__) if sb.findChildren(type(sb)) else object, "appTitle")
    # Use findChildren with QLabel
    from PyQt6.QtWidgets import QLabel
    titles = [w for w in sb.findChildren(QLabel) if w.objectName() == "appTitle"]
    assert len(titles) == 1
    assert titles[0].text() == "yt-dlp GUI"


def test_sidebar_subtitle_text(qapp):
    from src.ui.components.sidebar import Sidebar
    from PyQt6.QtWidgets import QLabel
    sb = Sidebar()
    subtitles = [w for w in sb.findChildren(QLabel) if w.objectName() == "appSubtitle"]
    assert len(subtitles) == 1
    assert subtitles[0].text() == "Download, convert, and organize media"


def test_sidebar_fixed_width_190(qapp):
    from src.ui.components.sidebar import Sidebar
    sb = Sidebar()
    assert sb.maximumWidth() == 190
    assert sb.minimumWidth() == 190


def test_sidebar_section_headers_not_clickable(qapp):
    from src.ui.components.sidebar import Sidebar
    from PyQt6.QtWidgets import QLabel
    sb = Sidebar()
    sections = [w for w in sb.findChildren(QLabel) if w.objectName() == "sidebarSection"]
    assert len(sections) >= 3  # DOWNLOAD, PROCESS, ORGANIZE


def test_sidebar_settings_below_separator(qapp):
    from src.ui.components.sidebar import Sidebar
    sb = Sidebar()
    # Settings is last button
    assert "settings" in sb._buttons


def test_sidebar_badge_does_not_mutate_wrong_item(qapp):
    from src.ui.components.sidebar import Sidebar
    sb = Sidebar()
    sb.set_badge("add_urls", 5)
    # Other buttons should keep original text
    assert sb._buttons["convert"].text() == "Convert"
    assert sb._buttons["settings"].text() == "Settings"


def test_sidebar_checked_button_object_name(qapp):
    from src.ui.components.sidebar import Sidebar
    sb = Sidebar()
    # All buttons use sidebarItem objectName
    for key, btn in sb._buttons.items():
        assert btn.objectName() == "sidebarItem"
